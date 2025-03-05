import pytest
import os
import tempfile
from app import app
from db import get_db, init_db
from utils import setup_directories
from rrd_utils import init_rrd, update_rrd, get_rrd_path
import rrdtool
from datetime import datetime
import sqlite3
import time

@pytest.fixture
def app_with_db():
    """Create a test Flask app with a test database."""
    # Configure app for testing
    app.config['TESTING'] = True
    app.config['DATABASE'] = 'test_uptime.db'
    
    # Create test database and tables
    init_db(app.config)
    setup_directories(app.config)  # Create RRD directory
    
    yield app
    
    # Clean up after tests
    if os.path.exists('test_uptime.db'):
        os.remove('test_uptime.db')
    
    # Clean up RRD directory
    rrd_dir = os.path.join(os.path.dirname('test_uptime.db'), 'rrd')
    if os.path.exists(rrd_dir):
        for file in os.listdir(rrd_dir):
            os.remove(os.path.join(rrd_dir, file))
        os.rmdir(rrd_dir)

@pytest.fixture
def client(app_with_db):
    """Create a test client."""
    return app_with_db.test_client()

@pytest.fixture
def runner():
    return app.test_cli_runner()

@pytest.fixture
def sample_csv():
    """Create a sample CSV file content for testing."""
    return '''Account Label,Account Id,Region,Host Id,Host IP Address,Hostname
Test Account,123456789012,us-east-1,i-1234567890abcdef0,10.0.0.1,Test Instance'''

def populate_rrd_with_test_data(host_id, app_config):
    """Populate an RRD file with test data for testing."""
    rrd_file = get_rrd_path(host_id, app_config)
    
    # Ensure the RRD directory exists
    os.makedirs(os.path.dirname(rrd_file), exist_ok=True)
    
    # Ensure the RRD file exists
    if not os.path.exists(rrd_file):
        init_rrd(host_id, app_config)
    
    try:
        # Verify the RRD file is properly initialized
        rrdtool.info(rrd_file)
    except Exception as e:
        print(f"Error with RRD file, reinitializing: {str(e)}")
        # If there's an issue, recreate the file
        if os.path.exists(rrd_file):
            os.remove(rrd_file)
        init_rrd(host_id, app_config)
    
    # Get the current time
    current_time = int(time.time())
    
    # Check if the RRD file already has data
    try:
        last_update_info = rrdtool.lastupdate(rrd_file)
        print(f"RRD last update before adding test data: {last_update_info}")
        
        # If there's already data, use the last update time + 300 seconds as our base
        if last_update_info and 'date' in last_update_info:
            last_update_timestamp = int(last_update_info['date'].timestamp())
            
            # Check if the last update time is in the future
            if last_update_timestamp > current_time:
                print(f"Last update time is in the future: {last_update_timestamp} > {current_time}")
                # Use the last update time + 300 seconds as our base
                base_timestamp = last_update_timestamp + 300
                print(f"Using future last update timestamp + 300s as base: {base_timestamp}")
            else:
                # Use the last update time + 300 seconds as our base
                base_timestamp = last_update_timestamp + 300
                print(f"Using last update timestamp + 300s as base: {base_timestamp}")
        else:
            # Otherwise, use current time - 24 hours
            base_timestamp = current_time - 86400
            print(f"Using current time - 24h as base: {base_timestamp}")
    except Exception as e:
        print(f"Error getting last update, using current time - 24h: {str(e)}")
        base_timestamp = current_time - 86400
    
    # Calculate how many points we can add (up to 24 hours worth at 5-minute intervals)
    # If base_timestamp is in the future, we'll add fewer points
    end_timestamp = max(current_time + 3600, base_timestamp + 86400)  # Either 1 hour in the future or 24 hours after base
    num_points = min(288, (end_timestamp - base_timestamp) // 300)  # Max 288 points (24 hours at 5-minute intervals)
    
    print(f"Adding {num_points} data points from {base_timestamp} to {end_timestamp}")
    
    # Add data points
    for i in range(num_points):
        timestamp = base_timestamp + (i * 300)  # 5-minute intervals
        uptime = 100.0  # 100% uptime
        latency = 10.0  # 10ms latency
        try:
            # Update the RRD file with the data point
            update_success = update_rrd(rrd_file, timestamp, uptime, latency)
            if not update_success:
                print(f"Failed to update RRD at timestamp {timestamp}")
        except Exception as e:
            print(f"Error updating RRD file: {str(e)}")
    
    # Verify the RRD file has data
    try:
        last_update = rrdtool.lastupdate(rrd_file)
        print(f"RRD last update after adding test data: {last_update}")
    except Exception as e:
        print(f"Error getting last update: {str(e)}")
    
    return rrd_file

@pytest.fixture
def sample_host(app_with_db):
    print(app_with_db)
    """Create a sample host for testing."""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with get_db(app_with_db.config) as db:
        cursor = db.execute('''
            INSERT INTO hosts (
                account_label, account_id, region,
                host_id, host_ip_address, host_name,
                is_active, last_check, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (
            'Test Account',
            '123456789012',
            'us-east-1',
            'i-1234567890abcdef0',
            '192.168.1.1',
            'test-instance',
            1  # Set is_active to 1 (True)
        ))
        host_id = cursor.lastrowid
        db.commit()
        
        # Get the inserted host with all fields
        host = db.execute('SELECT * FROM hosts WHERE id = ?', (host_id,)).fetchone()
        
        # Initialize RRD database for the sample host and populate with test data
        init_rrd(host_id, app_with_db.config)
        populate_rrd_with_test_data(host_id, app_with_db.config)
        
        return {
            'id': host_id,
            'account_label': 'Test Account',
            'account_id': '123456789012',
            'region': 'us-east-1',
            'host_id': 'i-1234567890abcdef0',
            'host_ip_address': '192.168.1.1',
            'host_name': 'test-instance',
            'is_active': 1,  # Add is_active to the returned dictionary
            'last_check': host['last_check'],  # Add last_check from the database
            'created_at': host['created_at']   # Add created_at from the database
        } 