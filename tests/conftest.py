import pytest
import os
import tempfile
from app import app, get_db, init_db, init_rrd, setup_directories
import rrdtool
from datetime import datetime
import sqlite3
from rrd_utils import init_rrd, update_rrd, get_rrd_path
import time

@pytest.fixture
def app_with_db():
    """Create a test Flask app with a test database."""
    # Configure app for testing
    app.config['TESTING'] = True
    app.config['DATABASE'] = 'test_uptime.db'
    
    # Create test database and tables
    with app.app_context():
        init_db()
        setup_directories()  # Create RRD directory
    
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
    return '''AWS Account Label,AWS Account ID,AWS Region,AWS Instance ID,AWS Instance IP Address,AWS Instance Name
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
    
    # Generate test data points
    current_time = int(time.time())
    # Add data points for the last 24 hours (288 points at 5-minute intervals)
    for i in range(288):
        timestamp = current_time - (287 - i) * 300  # Start 24 hours ago
        uptime = 100.0  # 100% uptime
        latency = 10.0  # 10ms latency
        try:
            # Update the RRD file with the data point
            update_success = update_rrd(rrd_file, timestamp, uptime, latency)
            if not update_success:
                print(f"Failed to update RRD at timestamp {timestamp}")
        except Exception as e:
            print(f"Error updating RRD: {str(e)}")
    
    # Verify the RRD file has data
    try:
        last_update = rrdtool.lastupdate(rrd_file)
        print(f"RRD last update: {last_update}")
    except Exception as e:
        print(f"Error getting last update: {str(e)}")
    
    return rrd_file

@pytest.fixture
def sample_host(app_with_db):
    print(app_with_db)
    """Create a sample host for testing."""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with app_with_db.app_context():
        with app_with_db.get_db() as db:
            cursor = db.execute('''
                INSERT INTO hosts (
                    aws_account_label, aws_account_id, aws_region,
                    aws_instance_id, aws_instance_ip, aws_instance_name,
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
                'aws_account_label': 'Test Account',
                'aws_account_id': '123456789012',
                'aws_region': 'us-east-1',
                'aws_instance_id': 'i-1234567890abcdef0',
                'aws_instance_ip': '192.168.1.1',
                'aws_instance_name': 'test-instance',
                'is_active': 1,  # Add is_active to the returned dictionary
                'last_check': host['last_check'],  # Add last_check from the database
                'created_at': host['created_at']   # Add created_at from the database
            } 