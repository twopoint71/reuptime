from flask import Flask, request, jsonify, send_file, send_from_directory, redirect, url_for, render_template
import os
import sys
from pathlib import Path
import rrdtool
import logging
from logging.handlers import RotatingFileHandler

# Import modules
from db import get_db, init_db, reinit_db
from utils import setup_directories
from routes.static_routes import register_static_routes
from routes.host_routes import register_host_routes
from routes.api_routes import register_api_routes
from routes.daemon_routes import register_daemon_routes

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'generate-a-secure-key-here'),
    DATABASE=os.path.join(app.instance_path, 'reuptime.sqlite'),
    DEBUG=False,  # Set to False for production
)

# If you're using environment-specific config files, ensure production settings are used
app.config.from_pyfile('config.py', silent=True)

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

# CL commands
@app.cli.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db(app.config)
    print('Initialized the database.')

@app.cli.command('reinit-db')
def reinit_db_command():
    """Clear the existing data and create new tables."""
    reinit_db(app.config)
    print('Reinitialized the database.')

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

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

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
                    print(f"Initializing RRD for host {host['id']} ({host['host_name']})...")
                    init_rrd(host['id'], app.config)
                    print(f"RRD initialized successfully for host {host['id']}.")
                except Exception as e:
                    print(f"Error initializing RRD for host {host['id']}: {str(e)}")

        print("Starting Flask application...")
        if not app.debug:
            # Ensure log directory exists
            if not os.path.exists('logs'):
                os.mkdir('logs')

            # Set up file handler
            file_handler = RotatingFileHandler('logs/reuptime.log', maxBytes=10240, backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)

            # Apply handler to app logger
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)
            app.logger.info('ReUptime startup')

        app.run()
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
