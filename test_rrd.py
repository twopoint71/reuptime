import os
import sys
import time
from datetime import datetime
import rrdtool

def test_create_rrd():
    """Test creating an RRD file directly."""
    print("Testing RRD file creation...")
    
    # Create test directory if it doesn't exist
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_rrd')
    os.makedirs(test_dir, exist_ok=True)
    print(f"Created test directory: {test_dir}")
    
    # Set up RRD file path
    rrd_file = os.path.join(test_dir, 'test.rrd')
    print(f"RRD file path: {rrd_file}")
    
    # Remove existing file if it exists
    if os.path.exists(rrd_file):
        os.remove(rrd_file)
        print(f"Removed existing RRD file: {rrd_file}")
    
    # Set start time to 24 hours before current time
    start_time = int(time.time() - 87000)
    print(f"Start time: {start_time} ({datetime.fromtimestamp(start_time)})")
    
    try:
        print("Creating RRD file...")
        rrdtool.create(
            rrd_file,
            '--start', str(start_time),
            '--step', '300',  # 5-minute intervals
            'DS:uptime:GAUGE:600:0:100',  # Uptime percentage
            'DS:latency:GAUGE:600:0:1000',  # Latency in ms
            'RRA:AVERAGE:0.5:1:288',  # Daily (5-min intervals)
            'RRA:AVERAGE:0.5:12:168',  # Weekly (1-hour intervals)
            'RRA:AVERAGE:0.5:24:720',  # Monthly (30-min intervals)
            'RRA:AVERAGE:0.5:288:365'  # Yearly (1-day intervals)
        )
        print(f"RRD file created successfully: {rrd_file}")
        
        # Check if the file exists
        if os.path.exists(rrd_file):
            print(f"File exists: {rrd_file}")
            print(f"File size: {os.path.getsize(rrd_file)} bytes")
        else:
            print(f"File does not exist: {rrd_file}")
        
        return True
    except Exception as e:
        print(f"Error creating RRD file: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_create_rrd()
    sys.exit(0 if success else 1) 