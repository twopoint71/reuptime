import os
import sys
import unittest
import sqlite3
import tempfile
import time
import rrdtool
import shutil
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the daemon module and rrd_utils
from monitors.icmp import daemon
from rrd_utils import init_rrd, update_rrd, get_rrd_path, fetch_rrd_data

class TestICMPRRDAndDB(unittest.TestCase):
    def setUp(self):
        # Create a temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Create a temporary directory for RRD files
        self.rrd_dir = tempfile.mkdtemp()
        
        # Create a test database with the hosts table
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute('''
            CREATE TABLE hosts (
                id INTEGER PRIMARY KEY,
                account_label TEXT,
                account_id TEXT,
                region TEXT,
                host_id TEXT,
                host_ip_address TEXT,
                host_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_check TIMESTAMP,
                is_active BOOLEAN DEFAULT 0
            )
        ''')
        
        # Insert a test host
        self.conn.execute('''
            INSERT INTO hosts (account_label, account_id, region, host_id, host_ip_address, host_name)
            VALUES ('Test Account', '123456789012', 'us-west-2', 'i-12345678', '192.168.1.1', 'Test Instance 1')
        ''')
        self.conn.commit()
        
        # Set the database path for the daemon
        daemon.db_path = self.db_path
        
        # Create a config object for RRD functions
        self.config = {
            'RRD_DIR': self.rrd_dir
        }
        
    def tearDown(self):
        # Close the database connection
        self.conn.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)
        
        # Remove the temporary RRD directory
        shutil.rmtree(self.rrd_dir)
    
    def test_init_and_update_rrd(self):
        """Test initializing and updating an RRD file."""
        # Get the host ID
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM hosts LIMIT 1")
        host_id = cursor.fetchone()[0]
        
        # Initialize the RRD file
        rrd_file = get_rrd_path(host_id, self.config)
        init_rrd(host_id, self.config)
        
        # Verify the RRD file was created
        self.assertTrue(os.path.exists(rrd_file), f"RRD file {rrd_file} was not created")
        
        # Update the RRD file with test data
        current_time = int(time.time())
        update_rrd(rrd_file, current_time, 100, 25)  # 100% uptime, 25ms latency
        
        # Wait a moment to ensure the update is processed
        time.sleep(1)
        
        # Update again with different values
        update_rrd(rrd_file, current_time + 5, 0, 0)  # 0% uptime, 0ms latency
        
        # Fetch the data from the RRD file
        rrd_data = fetch_rrd_data(rrd_file, start_time=current_time - 10, end_time=current_time + 10)
        
        # Verify we got data back
        self.assertIsNotNone(rrd_data, "Failed to fetch RRD data")
        
        # Verify the structure of the data
        time_info, ds_names, data = rrd_data
        self.assertEqual(len(ds_names), 2, "Expected 2 data sources")
        self.assertIn('uptime', ds_names, "Expected 'uptime' data source")
        self.assertIn('latency', ds_names, "Expected 'latency' data source")
        
        # Verify we have data points
        self.assertTrue(len(data) > 0, "No data points returned")
    
    def test_update_host_status_in_db(self):
        """Test updating host status in the SQLite database."""
        # Get the host ID
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM hosts LIMIT 1")
        host_id = cursor.fetchone()[0]
        
        # Update the host status in the database
        with sqlite3.connect(self.db_path) as db:
            db.execute('''
                UPDATE hosts 
                SET last_check = CURRENT_TIMESTAMP, is_active = ?
                WHERE id = ?
            ''', (1, host_id))
            db.commit()
        
        # Verify the update
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_active FROM hosts WHERE id = ?", (host_id,))
        is_active = cursor.fetchone()[0]
        self.assertEqual(is_active, 1, "Host status was not updated correctly")
    
    @patch('subprocess.run')
    def test_check_host_updates_db_and_rrd(self, mock_subprocess_run):
        """Test that check_host updates both the database and RRD file."""
        # Mock the subprocess.run function to return a successful ping
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=25.4 ms"
        mock_subprocess_run.return_value = mock_process
        
        # Get the host ID and IP
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, host_ip_address FROM hosts LIMIT 1")
        host_id, host_ip = cursor.fetchone()
        
        # Set up the RRD file
        rrd_file = get_rrd_path(str(host_id) + 'test', self.config)

        init_rrd(str(host_id) + 'test', self.config)
        
        # Patch the get_rrd_path function to use our temporary directory
        with patch('monitors.icmp.daemon.get_rrd_path', return_value=rrd_file):
            # Call the check_host function
            host = {
                'id': host_id,
                'host_ip_address': host_ip,
                'host_name': 'Test Instance 1'
            }            
            daemon.check_host(host)
            
            # Verify the database was updated
            cursor = self.conn.cursor()
            cursor.execute("SELECT is_active FROM hosts WHERE id = ?", (host_id,))
            is_active = cursor.fetchone()[0]
            self.assertEqual(is_active, 1, "Host status was not updated correctly in the database")
            
            # Verify the RRD file was updated
            rrd_data = fetch_rrd_data(rrd_file)
            print(rrd_data)
            self.assertIsNotNone(rrd_data, "Failed to fetch RRD data")
            
            # Verify the structure of the data
            time_info, ds_names, data = rrd_data
            self.assertEqual(len(ds_names), 2, "Expected 2 data sources")
            
            # Verify we have data points
            self.assertTrue(len(data) > 0, "No data points returned from RRD")

if __name__ == '__main__':
    unittest.main() 