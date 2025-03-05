from flask import Flask, request, jsonify, send_file, send_from_directory
from datetime import datetime
import os
import csv
import rrdtool
import time
import subprocess
import sqlite3
from pathlib import Path
from rrd_utils import (
    get_rrd_path, init_rrd, update_rrd, 
    fetch_rrd_data, get_last_update, format_rrd_data_for_chart
)

app = Flask(__name__)
app.config['DATABASE'] = 'uptime.db'
app.config['TESTING'] = False

def get_db():
    db_path = app.config['DATABASE']
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return db

# Make get_db available as an app attribute for testing
app.get_db = get_db

def init_db():
    with get_db() as db:
        # Create hosts table
        db.execute('''
            CREATE TABLE IF NOT EXISTS hosts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aws_account_label TEXT,
                aws_account_id TEXT,
                aws_region TEXT,
                aws_instance_id TEXT,
                aws_instance_ip TEXT,
                aws_instance_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_check TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Create deleted_hosts table
        db.execute('''
            CREATE TABLE IF NOT EXISTS deleted_hosts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aws_account_label TEXT,
                aws_account_id TEXT,
                aws_region TEXT,
                aws_instance_id TEXT,
                aws_instance_ip TEXT,
                aws_instance_name TEXT,
                created_at TIMESTAMP,
                last_check TIMESTAMP,
                is_active INTEGER,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

# Create necessary directories
def setup_directories():
    """Create necessary directories for RRD and graph files."""
    base_dir = os.path.dirname(app.config['DATABASE']) if app.config['TESTING'] else '.'
    directories = [
        os.path.join(base_dir, 'rrd'),
        os.path.join(base_dir, 'static', 'graphs')
    ]
    for directory in directories:
        print(directory)
        Path(directory).mkdir(parents=True, exist_ok=True)
        # Ensure directory has proper permissions
        os.chmod(directory, 0o755)

def get_graph_path(host_id):
    """Get the correct graph file path based on testing configuration."""
    base_dir = os.path.dirname(app.config['DATABASE']) if app.config['TESTING'] else '.'
    return os.path.join(base_dir, 'static', 'graphs', f'host_{host_id}.png')

# Routes
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/deleted_hosts')
def deleted_hosts():
    return send_from_directory('static', 'deleted_hosts.html')

@app.route('/import', methods=['POST'])
def import_hosts():
    if 'csv_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['csv_file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'File must be a CSV'}), 400

    try:
        stream = file.stream.read().decode("UTF8")
        if not stream.strip():
            return jsonify({'error': 'No file selected'}), 400
            
        csv_data = csv.DictReader(stream.splitlines())
        
        # Check if the CSV has any rows
        if not any(csv_data):
            return jsonify({'error': 'No file selected'}), 400
            
        # Reset the file pointer and create a new reader
        file.seek(0)
        stream = file.stream.read().decode("UTF8")
        csv_data = csv.DictReader(stream.splitlines())
        
        with get_db() as db:
            for row in csv_data:
                db.execute('''
                    INSERT INTO hosts (
                        aws_account_label, aws_account_id, aws_region,
                        aws_instance_id, aws_instance_ip, aws_instance_name
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    row['AWS Account Label'],
                    row['AWS Account ID'],
                    row['AWS Region'],
                    row['AWS Instance ID'],
                    row['AWS Instance IP Address'],
                    row['AWS Instance Name']
                ))
            db.commit()
        
        return jsonify({'message': 'Hosts imported successfully'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/metrics/<int:host_id>')
def get_metrics(host_id):
    with get_db() as db:
        host = db.execute('SELECT * FROM hosts WHERE id = ?', (host_id,)).fetchone()
        if not host:
            return jsonify({'error': 'Host not found'}), 404
    
    rrd_file = get_rrd_path(host_id)
    
    if not os.path.exists(rrd_file):
        return jsonify({'error': 'No metrics available'}), 404
    
    # Get the last 24 hours of data
    rrd_data = fetch_rrd_data(rrd_file)
    if not rrd_data:
        return jsonify({'error': 'Failed to fetch RRD data'}), 500
    
    return jsonify({
        'host_id': host_id,
        'host_name': host['aws_instance_name'],
        'metrics': rrd_data
    })

@app.route('/graph/<int:host_id>')
def get_graph(host_id):
    with get_db() as db:
        host = db.execute('SELECT * FROM hosts WHERE id = ?', (host_id,)).fetchone()
        if not host:
            return jsonify({'error': 'Host not found'}), 404
    
    rrd_file = get_rrd_path(host_id)
    graph_file = get_graph_path(host_id)
    
    if not os.path.exists(rrd_file):
        return jsonify({'error': 'No metrics available'}), 404
    
    # Generate graph for the last 24 hours
    rrdtool.graph(
        graph_file,
        '--start', '-86400',
        '--end', 'now',
        '--title', f'Uptime Metrics for {host["aws_instance_name"]}',
        '--vertical-label', 'Percentage',
        f'DEF:uptime={rrd_file}:uptime:AVERAGE',
        'LINE1:uptime#00FF00:Uptime'
    )
    
    return send_file(graph_file, mimetype='image/png')

@app.route('/add_host', methods=['POST'])
def add_host():
    try:
        # Validate required fields
        required_fields = [
            'aws_account_label', 'aws_account_id', 'aws_region',
            'aws_instance_id', 'aws_instance_ip', 'aws_instance_name'
        ]
        
        for field in required_fields:
            if not request.form.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate AWS account ID format
        if not request.form['aws_account_id'].isdigit() or len(request.form['aws_account_id']) != 12:
            return jsonify({'error': 'AWS Account ID must be 12 digits'}), 400
        
        # Ensure directories exist
        setup_directories()
        
        with get_db() as db:
            cursor = db.execute('''
                INSERT INTO hosts (
                    aws_account_label, aws_account_id, aws_region,
                    aws_instance_id, aws_instance_ip, aws_instance_name,
                    created_at, last_check, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
            ''', (
                request.form['aws_account_label'],
                request.form['aws_account_id'],
                request.form['aws_region'],
                request.form['aws_instance_id'],
                request.form['aws_instance_ip'],
                request.form['aws_instance_name']
            ))
            host_id = cursor.lastrowid
            db.commit()
        
        # Initialize RRD database for the new host
        init_rrd(host_id, app.config)
        
        return jsonify({'message': 'Host added successfully'})
    
    except Exception as e:
        print(f"Error adding host: {str(e)}")  # Add logging for debugging
        return jsonify({'error': str(e)}), 500

def check_host(host):
    """Check a host's status and update metrics."""
    try:
        # Perform ICMP check
        result = subprocess.run(['ping', '-c', '1', host['aws_instance_ip']],
                              capture_output=True, text=True)
        success = result.returncode == 0
        
        # Update host status
        with get_db() as db:
            db.execute('''
                UPDATE hosts 
                SET last_check = CURRENT_TIMESTAMP, is_active = ?
                WHERE id = ?
            ''', (1 if success else 0, host['id']))
            db.commit()
        
        # Update RRD database
        rrd_file = get_rrd_path(host['id'])
        if os.path.exists(rrd_file):
            try:
                # Extract latency from ping output
                latency = 0
                if success and 'time=' in result.stdout:
                    latency_str = result.stdout.split('time=')[-1].split()[0]
                    latency = float(latency_str)
                
                update_rrd(rrd_file, int(time.time()), 100 if success else 0, latency)
            except Exception as e:
                print(f"Error updating RRD file: {str(e)}")
        
        return success
    except Exception as e:
        print(f"Error checking host {host['aws_instance_name']}: {str(e)}")
        with get_db() as db:
            db.execute('''
                UPDATE hosts 
                SET last_check = CURRENT_TIMESTAMP, is_active = 0
                WHERE id = ?
            ''', (host['id'],))
            db.commit()
        return False

@app.route('/check_host/<int:host_id>', methods=['POST'])
def check_host_route(host_id):
    """Route to check a specific host's status."""
    with get_db() as db:
        host = db.execute('SELECT * FROM hosts WHERE id = ?', (host_id,)).fetchone()
        if not host:
            return jsonify({'success': False, 'error': 'Host not found'}), 404
    
    success = check_host(host)
    return jsonify({
        'success': True,
        'is_active': 1 if success else 0
    })

@app.route('/delete_host/<int:host_id>', methods=['POST'])
def delete_host(host_id):
    """Delete a host and its associated RRD database."""
    with get_db() as db:
        # Get the host to delete
        host = db.execute('SELECT * FROM hosts WHERE id = ?', (host_id,)).fetchone()
        if not host:
            return jsonify({'success': False, 'error': 'Host not found'}), 404
        
        # Store host data in deleted_hosts table
        db.execute('''
            INSERT INTO deleted_hosts (
                aws_account_label, aws_account_id, aws_region,
                aws_instance_id, aws_instance_ip, aws_instance_name,
                created_at, last_check, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            host['aws_account_label'],
            host['aws_account_id'],
            host['aws_region'],
            host['aws_instance_id'],
            host['aws_instance_ip'],
            host['aws_instance_name'],
            host['created_at'],
            host['last_check'],
            host['is_active']
        ))
        
        # Delete RRD database if it exists
        rrd_file = get_rrd_path(host_id)
        if os.path.exists(rrd_file):
            os.remove(rrd_file)
        
        # Delete host from database
        db.execute('DELETE FROM hosts WHERE id = ?', (host_id,))
        db.commit()
        
        # Return the deleted host data in the response
        host_dict = dict(host)
        # Convert datetime objects to strings
        for key in ['created_at', 'last_check']:
            if host_dict[key] and not isinstance(host_dict[key], str):
                host_dict[key] = host_dict[key].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'success': True, 
            'deleted_host_data': host_dict
        })

@app.route('/undo_delete/<int:host_id>', methods=['POST'])
def undo_delete(host_id):
    """Restore the last deleted host."""
    with get_db() as db:
        # Get the deleted host
        deleted_host = db.execute('SELECT * FROM deleted_hosts WHERE id = ?', (host_id,)).fetchone()
        
        if not deleted_host:
            return jsonify({'success': False, 'error': 'No host to restore'}), 404
        
        try:
            # Insert the host back into the hosts table
            cursor = db.execute('''
                INSERT INTO hosts (
                    aws_account_label, aws_account_id, aws_region,
                    aws_instance_id, aws_instance_ip, aws_instance_name,
                    created_at, last_check, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                deleted_host['aws_account_label'],
                deleted_host['aws_account_id'],
                deleted_host['aws_region'],
                deleted_host['aws_instance_id'],
                deleted_host['aws_instance_ip'],
                deleted_host['aws_instance_name'],
                deleted_host['created_at'],
                deleted_host['last_check'],
                deleted_host['is_active']
            ))
            restored_id = cursor.lastrowid
            
            # Initialize RRD database for the restored host
            init_rrd(restored_id, app.config)
            
            # Remove the host from deleted_hosts
            db.execute('DELETE FROM deleted_hosts WHERE id = ?', (host_id,))
            db.commit()
            
            # Return the restored host ID
            return jsonify({
                'success': True,
                'restored_host_id': restored_id
            })
        except Exception as e:
            db.rollback()  # Rollback any changes if an error occurs
            print(f"Error restoring host: {str(e)}")  # Add logging for debugging
            return jsonify({
                'success': False, 
                'error': f"Failed to restore host: {str(e)}"
            }), 500

@app.route('/api/metrics/<int:host_id>')
def get_metrics_data(host_id):
    """API endpoint to fetch metric data for Chart.js"""
    rrd_file = get_rrd_path(host_id)
    if not os.path.exists(rrd_file):
        return jsonify({'error': 'RRD file not found'}), 404
    
    try:
        # Fetch data from RRD
        rrd_data = fetch_rrd_data(rrd_file)
        if not rrd_data:
            return jsonify({'error': 'Failed to fetch RRD data'}), 500
        
        # Format data for Chart.js
        chart_data = format_rrd_data_for_chart(rrd_data)
        if not chart_data:
            return jsonify({'error': 'No valid data points found'}), 500
        
        return jsonify(chart_data)
    except Exception as e:
        print(f"Error fetching metrics data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/hosts')
def get_hosts_data():
    """API endpoint to fetch all hosts data in JSON format"""
    with get_db() as db:
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
    with get_db() as db:
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
    response = undo_delete(host_id)
    
    # If the response is a tuple, it means there was an error
    if isinstance(response, tuple):
        return response
    
    return response  # Return the JSON response from undo_delete

@app.route('/api/permanently_delete_host', methods=['POST'])
def permanently_delete_host():
    """API endpoint to permanently delete a host from deleted_hosts table"""
    data = request.json
    if not data or 'host_id' not in data:
        return jsonify({'success': False, 'error': 'Host ID is required'}), 400
    
    host_id = data['host_id']
    
    with get_db() as db:
        # Check if the host exists
        host = db.execute('SELECT * FROM deleted_hosts WHERE id = ?', (host_id,)).fetchone()
        if not host:
            return jsonify({'success': False, 'error': 'Host not found'}), 404
        
        # Delete the host from deleted_hosts table
        db.execute('DELETE FROM deleted_hosts WHERE id = ?', (host_id,))
        db.commit()
        
        return jsonify({'success': True})

@app.route('/host/<int:host_id>')
def host_details(host_id):
    """Redirect to the main page with a query parameter to open the host details modal"""
    return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    init_db()
    setup_directories()
    # Initialize RRD databases for existing hosts
    with get_db() as db:
        hosts = db.execute('SELECT * FROM hosts').fetchall()
        for host in hosts:
            init_rrd(host['id'], app.config)
    
    app.run(debug=True) 