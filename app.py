from flask import Flask, request, jsonify, send_file, send_from_directory, redirect, url_for
import os
import sys
from pathlib import Path
import rrdtool

# Import modules
from db import get_db, init_db
from utils import setup_directories
from routes.static_routes import register_static_routes
from routes.host_routes import register_host_routes
from routes.api_routes import register_api_routes
from routes.daemon_routes import register_daemon_routes

app = Flask(__name__)
app.config['DATABASE'] = 'uptime.db'
app.config['TESTING'] = False
app.config['MONITOR_PATH'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'monitors')
app.config['RRD_DIR'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rrd')
app.config['MONITOR_LOG_PATH'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'monitors', 'icmp', 'icmp_monitor.log')

# Make get_db available as an app attribute for testing
app.get_db = get_db

# Register routes
register_static_routes(app)
register_host_routes(app)
register_api_routes(app)
register_daemon_routes(app)

def create_rrd(host_id):
    """Create RRD file for a host if it doesn't exist already."""
    rrd_path = os.path.join(app.config['RRD_PATH'], f"{host_id}.rrd")
    
    # Check if the RRD file already exists
    if os.path.exists(rrd_path):
        app.logger.info(f"RRD file for host {host_id} already exists, preserving historic data")
        return rrd_path
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(rrd_path), exist_ok=True)
    
    # Define RRD structure - 1 year of data
    # Step: 60 seconds (1 minute)
    # DS: uptime (gauge) and latency (gauge)
    # RRA: Average over 1 minute, 5 minutes, 30 minutes, and 1 day
    rrdtool.create(
        rrd_path,
        "--step", "60",
        "--start", "N-86400",  # Start 24 hours ago
        "DS:uptime:GAUGE:120:0:1",
        "DS:latency:GAUGE:120:0:10000",
        "RRA:AVERAGE:0.5:1:1440",     # 1 minute average for 24 hours
        "RRA:AVERAGE:0.5:5:2016",     # 5 minute average for 7 days
        "RRA:AVERAGE:0.5:30:1488",    # 30 minute average for 31 days
        "RRA:AVERAGE:0.5:1440:365"    # 1 day average for 1 year
    )
    
    app.logger.info(f"Created RRD file for host {host_id}")
    return rrd_path

if __name__ == '__main__':
    try:
        print("Initializing database...")
        init_db(app.config)
        print("Database initialized successfully.")
        
        print("Setting up directories...")
        setup_directories(app.config)
        print("Directories set up successfully.")
        
        # Initialize RRD databases for existing hosts
        print("Initializing RRD databases for existing hosts...")
        from rrd_utils import init_rrd
        with get_db(app.config) as db:
            hosts = db.execute('SELECT * FROM hosts').fetchall()
            for host in hosts:
                try:
                    print(f"Initializing RRD for host {host['id']} ({host['aws_instance_name']})...")
                    init_rrd(host['id'], app.config)
                    print(f"RRD initialized successfully for host {host['id']}.")
                except Exception as e:
                    print(f"Error initializing RRD for host {host['id']}: {str(e)}")
        
        print("Starting Flask application...")
        app.run(debug=True)
    except Exception as e:
        print(f"Error initializing application: {str(e)}")
        
        # If the error is related to database permissions, provide more helpful information
        if "readonly database" in str(e):
            print("\nThis error is likely due to permission issues with the database file.")
            print("Try the following steps to fix it:")
            print("1. Check the ownership of the database file and directory:")
            print("   $ ls -la uptime.db")
            print("   $ ls -la .")
            print("2. Change the ownership of the database file and directory:")
            print("   $ sudo chown $(whoami) uptime.db")
            print("   $ sudo chown $(whoami) .")
            print("3. Change the permissions of the database file and directory:")
            print("   $ chmod 644 uptime.db")
            print("   $ chmod 755 .")
            print("4. If the database file doesn't exist yet, check the permissions of the parent directory.")
        
        sys.exit(1) 