from flask import request, jsonify, redirect
import os
import time
import json
import pytz
from datetime import datetime
from db import get_db
from utils import read_last_n_lines
from rrd_utils import get_rrd_path, init_rrd, fetch_rrd_data, format_rrd_data_for_chart

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
    
    @app.route('/api/deleted_hosts')
    def get_deleted_hosts_data():
        """API endpoint to fetch all deleted hosts data in JSON format"""
        with get_db(app.config) as db:
            deleted_hosts = db.execute('SELECT * FROM deleted_hosts ORDER BY deleted_at DESC').fetchall()
            
        # Convert hosts to a list of dictionaries
        hosts_list = []
        for host in deleted_hosts:
            host_dict = dict(host)
            # Convert datetime objects to strings
            for key in ['created_at', 'last_check', 'deleted_at']:
                if host_dict[key] and not isinstance(host_dict[key], str):
                    host_dict[key] = host_dict[key].strftime('%Y-%m-%d %H:%M:%S')
            
            # Ensure all required fields are present
            required_fields = [
                'id', 'aws_account_label', 'aws_account_id', 'aws_region',
                'aws_instance_id', 'aws_instance_ip', 'aws_instance_name',
                'created_at', 'last_check', 'is_active', 'deleted_at'
            ]
            
            for field in required_fields:
                if field not in host_dict:
                    host_dict[field] = None
            
            hosts_list.append(host_dict)
            
        return jsonify(hosts_list)
    
    @app.route('/api/restore_host', methods=['POST'])
    def restore_host_api():
        """API endpoint to restore a deleted host"""
        data = request.json
        if not data or 'host_id' not in data:
            return jsonify({'success': False, 'error': 'Host ID is required'}), 400
        
        host_id = data['host_id']
        
        # Call the existing undo_delete function
        from routes.host_routes import register_host_routes
        # Get the undo_delete function from the app
        undo_delete = app.view_functions.get('undo_delete')
        if undo_delete:
            response = undo_delete(host_id)
            
            # If the response is a tuple, it means there was an error
            if isinstance(response, tuple):
                return response
            
            return response  # Return the JSON response from undo_delete
        else:
            return jsonify({'success': False, 'error': 'undo_delete function not found'}), 500
    
    @app.route('/api/permanently_delete_host', methods=['POST'])
    def permanently_delete_host():
        """API endpoint to permanently delete a host from deleted_hosts table"""
        data = request.json
        if not data or 'host_id' not in data:
            return jsonify({'success': False, 'error': 'Host ID is required'}), 400
        
        host_id = data['host_id']
        
        with get_db(app.config) as db:
            # Check if the host exists
            host = db.execute('SELECT * FROM deleted_hosts WHERE id = ?', (host_id,)).fetchone()
            if not host:
                return jsonify({'success': False, 'error': 'Host not found'}), 404
            
            # Delete the host from deleted_hosts table
            db.execute('DELETE FROM deleted_hosts WHERE id = ?', (host_id,))
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