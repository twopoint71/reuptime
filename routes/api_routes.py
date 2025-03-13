from flask import request, jsonify, redirect
import os
import time
import json
import pytz
import rrdtool
from datetime import datetime, timedelta
from db import get_db
from utils import read_last_n_lines
from rrd_utils import get_rrd_path, init_rrd, fetch_rrd_data, format_rrd_data_for_chart, get_aggregate_rrd_path, init_aggregate_rrd

def register_api_routes(app):
    """Register API routes for the application."""
    
    @app.route('/metrics/<int:host_id>')
    def get_metrics(host_id):
        """Redirect to the API metrics endpoint for consistency."""
        # Get the query string parameters
        query_string = request.query_string.decode('utf-8')
        target_url = f"/api/metrics/{host_id}"
        
        # Append query string if it exists
        if query_string:
            target_url = f"{target_url}?{query_string}"
        
        return redirect(target_url, code=301)
    
    @app.route('/api/metrics/<int:host_id>')
    def get_metrics_data(host_id):
        """API endpoint to fetch metric data for Chart.js"""
        # Parse time range parameter
        time_range = request.args.get('range', '24h')
        
        # Calculate start time based on time range
        end_time = int(time.time())
        start_time = end_time
        
        # Parse time range format
        if time_range.endswith('m'):
            # Minutes
            minutes = int(time_range[:-1])
            start_time = end_time - (minutes * 60)
        elif time_range.endswith('h'):
            # Hours
            hours = int(time_range[:-1])
            start_time = end_time - (hours * 3600)
        elif time_range.endswith('d'):
            # Days
            days = int(time_range[:-1])
            start_time = end_time - (days * 86400)
        elif time_range.endswith('w'):
            # Weeks
            weeks = int(time_range[:-1])
            start_time = end_time - (weeks * 7 * 86400)
        elif time_range.endswith('mo'):
            # Months (approximate)
            months = int(time_range[:-2])
            start_time = end_time - (months * 30 * 86400)
        elif time_range.endswith('y'):
            # Years (approximate)
            years = int(time_range[:-1])
            start_time = end_time - (years * 365 * 86400)
        else:
            # Default to 24 hours
            start_time = end_time - 86400
        
        rrd_file = get_rrd_path(host_id, app.config)
        if not os.path.exists(rrd_file):
            print(f"RRD file not found: {rrd_file}")
            # Try to create the RRD file
            try:
                print(f"Attempting to create RRD file for host ID {host_id}")
                init_rrd(host_id, app.config)
                print(f"Successfully created RRD file for host ID {host_id}")
            except Exception as e:
                print(f"Failed to create RRD file for host ID {host_id}: {str(e)}")
                return jsonify({'error': f'RRD file not found and could not be created: {str(e)}'}), 500
        
        try:
            # Fetch data from RRD with time range
            rrd_data = fetch_rrd_data(rrd_file, start_time=start_time, end_time=end_time)
            
            # Format data for Chart.js
            chart_data = format_rrd_data_for_chart(rrd_data)
            
            return jsonify(chart_data)
        except Exception as e:
            print(f"Error fetching metrics data: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/hosts')
    def get_hosts_data():
        """API endpoint to fetch all hosts data in JSON format"""
        with get_db(app.config) as db:
            hosts = db.execute('SELECT * FROM hosts').fetchall()
            
        # Convert hosts to a list of dictionaries
        hosts_list = []
        for host in hosts:
            host_dict = dict(host)
            # Convert datetime objects to strings
            for key in ['created_at', 'last_check']:
                if host_dict[key] and not isinstance(host_dict[key], str):
                    host_dict[key] = host_dict[key].strftime('%Y-%m-%d %H:%M:%S')
            hosts_list.append(host_dict)
            
        return jsonify(hosts_list)
    
    @app.route('/api/unmonitored_hosts')
    def get_unmonitored_hosts_data():
        """API endpoint to fetch all unmonitored hosts data in JSON format"""
        with get_db(app.config) as db:
            unmonitored_hosts = db.execute('SELECT * FROM unmonitored_hosts ORDER BY unmonitored_at DESC').fetchall()
            
        # Convert hosts to a list of dictionaries
        hosts_list = []
        for host in unmonitored_hosts:
            host_dict = dict(host)
            # Convert datetime objects to strings
            for key in ['created_at', 'last_check', 'unmonitored_at']:
                if host_dict[key] and not isinstance(host_dict[key], str):
                    host_dict[key] = host_dict[key].strftime('%Y-%m-%d %H:%M:%S')
            
            # Ensure all required fields are present
            required_fields = [
                'id', 'account_label', 'account_id', 'region',
                'host_id', 'host_ip_address', 'host_name',
                'created_at', 'last_check', 'is_active', 'unmonitored_at'
            ]
            
            for field in required_fields:
                if field not in host_dict:
                    host_dict[field] = None
            
            hosts_list.append(host_dict)
            
        return jsonify(hosts_list)
    
    @app.route('/api/restore_host', methods=['POST'])
    def restore_host_api():
        """API endpoint to restore an unmonitored host"""
        data = request.json
        if not data or 'host_id' not in data:
            return jsonify({'success': False, 'error': 'Host ID is required'}), 400
        
        host_id = data['host_id']
        
        # Call the existing restore_host function
        from routes.host_routes import register_host_routes
        # Get the restore_host function from the app
        restore_host = app.view_functions.get('restore_host')
        if restore_host:
            response = restore_host(host_id)
            
            # If the response is a tuple, it means there was an error
            if isinstance(response, tuple):
                return response
            
            return response  # Return the JSON response from restore_host
        else:
            return jsonify({'success': False, 'error': 'restore_host function not found'}), 500
    
    @app.route('/api/permanently_delete_host', methods=['POST'])
    def permanently_delete_host():
        """API endpoint to permanently delete a host from unmonitored_hosts table"""
        data = request.json
        if not data or 'host_id' not in data:
            return jsonify({'success': False, 'error': 'Host ID is required'}), 400
        
        host_id = data['host_id']
        
        with get_db(app.config) as db:
            # Check if the host exists
            host = db.execute('SELECT * FROM unmonitored_hosts WHERE id = ?', (host_id,)).fetchone()
            if not host:
                return jsonify({'success': False, 'error': 'Host not found'}), 404
            
            # Delete the host from unmonitored_hosts table
            db.execute('DELETE FROM unmonitored_hosts WHERE id = ?', (host_id,))
            db.commit()
            
            return jsonify({'success': True})
    
    @app.route('/api/monitor_log')
    def get_monitor_log():
        """API endpoint to get the ICMP monitor log data."""
        try:
            # Get the number of lines to return (default to 50)
            lines = request.args.get('lines', default=50, type=int)
            
            # Check if the log file exists
            if not os.path.exists(app.config['MONITOR_LOG_PATH']):
                return jsonify({
                    'error': 'Log file not found',
                    'log_content': 'The ICMP monitor log file does not exist. Make sure the monitor daemon is running.'
                }), 404
            
            # Read the last N lines from the log file
            log_content = read_last_n_lines(app.config['MONITOR_LOG_PATH'], lines)
            
            return jsonify({
                'log_content': log_content
            })
        except Exception as e:
            return jsonify({
                'error': str(e),
                'log_content': f'Error reading log file: {str(e)}'
            }), 500
    
    @app.route('/api/system_info')
    def system_info():
        """Get system information."""
        try:
            # Get database path
            db_path = app.config['DATABASE']
            
            # Get host counts
            with get_db(app.config) as db:
                hosts_count = db.execute('SELECT COUNT(*) FROM hosts').fetchone()[0]
                deleted_hosts_count = db.execute('SELECT COUNT(*) FROM deleted_hosts').fetchone()[0]
            
            # Get server uptime (Linux only)
            server_uptime = "Unknown"
            try:
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.readline().split()[0])
                    uptime_days = int(uptime_seconds // 86400)
                    uptime_hours = int((uptime_seconds % 86400) // 3600)
                    uptime_minutes = int((uptime_seconds % 3600) // 60)
                    server_uptime = f"{uptime_days} days, {uptime_hours} hours, {uptime_minutes} minutes"
            except:
                # Fallback for non-Linux systems
                server_uptime = "Not available on this platform"
            
            return jsonify({
                'db_path': db_path,
                'hosts_count': hosts_count,
                'deleted_hosts_count': deleted_hosts_count,
                'server_uptime': server_uptime,
                'server_time': datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d %H:%M:%S %Z')
            })
        except Exception as e:
            return jsonify({
                'error': str(e)
            }), 500
    
    @app.route('/api/aggregate_uptime')
    def get_aggregate_uptime():
        """API endpoint to fetch aggregate uptime data from the dedicated RRD file"""
        # Parse time range parameter
        time_range = request.args.get('range', '24h')
        
        # Calculate start time based on time range
        end_time = int(time.time())
        start_time = end_time
        
        # Parse time range format
        if time_range.endswith('m'):
            # Minutes
            minutes = int(time_range[:-1])
            start_time = end_time - (minutes * 60)
        elif time_range.endswith('h'):
            # Hours
            hours = int(time_range[:-1])
            start_time = end_time - (hours * 3600)
        elif time_range.endswith('d'):
            # Days
            days = int(time_range[:-1])
            start_time = end_time - (days * 86400)
        elif time_range.endswith('w'):
            # Weeks
            weeks = int(time_range[:-1])
            start_time = end_time - (weeks * 7 * 86400)
        elif time_range.endswith('mo'):
            # Months (approximate)
            months = int(time_range[:-2])
            start_time = end_time - (months * 30 * 86400)
        elif time_range.endswith('y'):
            # Years (approximate)
            years = int(time_range[:-1])
            start_time = end_time - (years * 365 * 86400)
        else:
            # Default to 24 hours
            start_time = end_time - 86400
        
        try:
            # Get the path to the aggregate RRD file
            aggregate_rrd = get_aggregate_rrd_path(app.config)
            
            # Check if the aggregate RRD file exists
            if not os.path.exists(aggregate_rrd):
                print(f"Aggregate RRD file not found: {aggregate_rrd}")
                # Try to create the RRD file
                try:
                    print(f"Attempting to create aggregate RRD file")
                    aggregate_rrd = init_aggregate_rrd(app.config)
                    print(f"Successfully created aggregate RRD file")
                except Exception as e:
                    print(f"Failed to create aggregate RRD file: {str(e)}")
                    # Fall back to the old method of calculating from individual hosts
                    return calculate_aggregate_from_hosts(start_time, end_time)
            
            # Fetch data from the aggregate RRD file
            rrd_data = fetch_rrd_data(aggregate_rrd, start_time=start_time, end_time=end_time)
            
            if not rrd_data or len(rrd_data) < 3:
                print("Invalid RRD data structure from aggregate RRD")
                # Fall back to the old method
                return calculate_aggregate_from_hosts(start_time, end_time)
            
            # Process the RRD data
            time_info, ds_names, data = rrd_data
            
            # Filter out None values and their corresponding timestamps
            valid_indices = [i for i, val in enumerate(data) if val[2] is not None]  # Check uptime_percent
            
            if not valid_indices:
                print("No valid data points found in aggregate RRD")
                # Fall back to the old method
                return calculate_aggregate_from_hosts(start_time, end_time)
            
            valid_timestamps = [time_info[0] + (i * time_info[2]) for i in valid_indices]
            valid_data = [data[i] for i in valid_indices]
            
            # Format data for Chart.js
            formatted_timestamps = [datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') for ts in valid_timestamps]
            uptime_values = [float(val[2]) if val[2] is not None else None for val in valid_data]  # uptime_percent is at index 2
            
            # Get the most recent uptime percentage
            current_uptime = uptime_values[-1] if uptime_values else 100.0
            
            chart_data = {
                'labels': formatted_timestamps,
                'datasets': [{
                    'label': 'Aggregate Uptime (%)',
                    'data': uptime_values,
                    'borderColor': '#00FF00',
                    'fill': False
                }]
            }
            
            return jsonify({
                'current_uptime': f"{current_uptime:.2f}",
                'chart_data': chart_data
            })
        
        except Exception as e:
            print(f"Error fetching aggregate uptime data: {str(e)}")
            # Fall back to the old method in case of any error
            return calculate_aggregate_from_hosts(start_time, end_time)

    @app.route('/api/aggregate_uptime')
    def calculate_aggregate_from_hosts(start_time, end_time):
        """
        Calculate aggregate uptime from individual host RRD files.
        This is a fallback method in case the aggregate RRD file is not available.
        """
        try:
            # Get all hosts
            with get_db(app.config) as db:
                hosts = db.execute('SELECT * FROM hosts').fetchall()
            
            if not hosts:
                return jsonify({
                    'current_uptime': "100.00",
                    'chart_data': {
                        'labels': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                        'datasets': [{
                            'label': 'Aggregate Uptime (%)',
                            'data': [100],
                            'borderColor': '#00FF00',
                            'fill': False
                        }]
                    }
                })
            
            # Initialize data structure for aggregate uptime
            aggregate_data = {}
            
            # Collect uptime data from each host's RRD file
            for host in hosts:
                rrd_file = get_rrd_path(host['id'], app.config)
                if os.path.exists(rrd_file):
                    rrd_data = fetch_rrd_data(rrd_file, start_time=start_time, end_time=end_time)
                    if rrd_data:
                        time_info, ds_names, data = rrd_data
                        
                        # Process each data point
                        for i, point in enumerate(data):
                            if point[0] is not None:  # Check if uptime value exists
                                timestamp = time_info[0] + (i * time_info[2])
                                if timestamp not in aggregate_data:
                                    aggregate_data[timestamp] = {'total': 0, 'count': 0}
                                
                                aggregate_data[timestamp]['total'] += float(point[0])
                                aggregate_data[timestamp]['count'] += 1
            
            # Calculate averages for each timestamp
            timestamps = sorted(aggregate_data.keys())
            uptime_values = []
            formatted_timestamps = []
            
            for ts in timestamps:
                if aggregate_data[ts]['count'] > 0:
                    avg_uptime = aggregate_data[ts]['total'] / aggregate_data[ts]['count']
                    uptime_values.append(avg_uptime)
                    formatted_timestamps.append(datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'))
            
            # Calculate current uptime (average of the most recent data points)
            current_uptime = 100.0  # Default to 100% if no data
            if uptime_values:
                # Use the last data point
                current_uptime = uptime_values[-1]
            
            # Format data for Chart.js
            chart_data = {
                'labels': formatted_timestamps,
                'datasets': [{
                    'label': 'Aggregate Uptime (%)',
                    'data': uptime_values,
                    'borderColor': '#00FF00',
                    'fill': False
                }]
            }
            
            return jsonify({
                'current_uptime': f"{current_uptime:.2f}",
                'chart_data': chart_data
            })
        
        except Exception as e:
            print(f"Error calculating aggregate uptime from hosts: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/annual_uptime')
    def get_annual_uptime():
        """API endpoint to fetch the annual uptime percentage."""
        try:
            # get timestamps with 20 second alignment
            end_time = datetime.now()
            start_time = str(int((end_time - timedelta(days=365)).timestamp() / 20) * 20)
            end_time = str(int(end_time.timestamp() / 20) * 20)

            # Get the aggregate RRD file path
            aggregate_rrd = get_aggregate_rrd_path(app.config)
            
            if not os.path.exists(aggregate_rrd):
                return jsonify({
                    'error': 'Aggregate RRD file not found',
                    'annual_uptime': '100.00'  # Default value if no data
                }), 404

            rrd_data = rrdtool.fetch(aggregate_rrd, 'AVERAGE', '--start', start_time, '--end', end_time)
            
            if not rrd_data or len(rrd_data) < 3:
                return jsonify({
                    'error': 'Invalid RRD data structure',
                    'annual_uptime': '100.00'
                }), 500            
            
            # Process the RRD data
            time_info, ds_names, data = rrd_data
            
            # Filter out None values and get uptime percentages
            # 2 is HOST_UP column
            valid_data = [float(val[2]) for val in data if val[2] is not None]  # uptime_percent is at index 2
            
            if not valid_data:
                return jsonify({
                    'error': 'No valid data points found',
                    'annual_uptime': '100.00'
                }), 404
            
            # Calculate average uptime
            annual_uptime = sum(valid_data) / len(valid_data)
            
            return jsonify({
                'annual_uptime': f"{annual_uptime:.2f}",
                'data_points': len(valid_data)
            })
            
        except Exception as e:
            logger.error(f"Error calculating annual uptime: {str(e)}")
            return jsonify({
                'error': str(e),
                'annual_uptime': '100.00'
            }), 500 