import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call
import sqlite3
import tempfile
import time
from argparse import Namespace

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the daemon module
from monitors.icmp import daemon

class TestICMPMonitor(unittest.TestCase):
    def setUp(self):
        # Create a temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Create a test database with the hosts table
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute('''
            CREATE TABLE hosts (
                id INTEGER PRIMARY KEY,
                aws_account_label TEXT,
                aws_account_id TEXT,
                aws_region TEXT,
                aws_instance_id TEXT,
                aws_instance_ip TEXT,
                aws_instance_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_check TIMESTAMP,
                is_active BOOLEAN DEFAULT 0
            )
        ''')
        
        # Insert some test hosts
        self.conn.execute('''
            INSERT INTO hosts (aws_account_label, aws_account_id, aws_region, aws_instance_id, aws_instance_ip, aws_instance_name)
            VALUES ('Test Account', '123456789012', 'us-west-2', 'i-12345678', '192.168.1.1', 'Test Instance 1')
        ''')
        self.conn.execute('''
            INSERT INTO hosts (aws_account_label, aws_account_id, aws_region, aws_instance_id, aws_instance_ip, aws_instance_name)
            VALUES ('Test Account', '123456789012', 'us-west-2', 'i-87654321', '192.168.1.2', 'Test Instance 2')
        ''')
        self.conn.commit()
        
        # Set the database path for the daemon
        daemon.db_path = self.db_path
        
        # Create a mock RRD file path
        self.rrd_path = os.path.join(os.path.dirname(self.db_path), 'test_rrd.rrd')
        
    def tearDown(self):
        # Close the database connection
        self.conn.close()
        
        # Remove the temporary database file
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    @patch('threading.Thread')
    def test_run_checks(self, mock_thread):
        # Mock the Thread class
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        # Mock get_all_hosts to return our test hosts
        original_get_all_hosts = daemon.get_all_hosts
        daemon.get_all_hosts = MagicMock()
        test_hosts = [
            {'id': 1, 'aws_instance_ip': '192.168.1.1', 'aws_instance_name': 'Test Instance 1'},
            {'id': 2, 'aws_instance_ip': '192.168.1.2', 'aws_instance_name': 'Test Instance 2'}
        ]
        daemon.get_all_hosts.return_value = test_hosts
        
        try:
            # Call the run_checks function
            daemon.run_checks()
            
            # Verify that Thread was called for each host
            self.assertEqual(mock_thread.call_count, 2)
            mock_thread.assert_has_calls([
                call(target=daemon.check_host_thread, args=(test_hosts[0],)),
                call(target=daemon.check_host_thread, args=(test_hosts[1],))
            ], any_order=True)
            
            # Verify that start was called on each thread
            self.assertEqual(mock_thread_instance.start.call_count, 2)
            
            # Verify that join was called on each thread
            self.assertEqual(mock_thread_instance.join.call_count, 2)
        finally:
            # Restore the original get_all_hosts function
            daemon.get_all_hosts = original_get_all_hosts
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('monitors.icmp.daemon.update_rrd')
    def test_check_host_success(self, mock_update_rrd, mock_path_exists, mock_subprocess_run):
        # Mock the subprocess.run function to return a successful ping
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=0.123 ms"
        mock_subprocess_run.return_value = mock_process
        
        # Mock os.path.exists to return True for the RRD file
        mock_path_exists.return_value = True
        
        # Create a test host
        test_host = {'id': 1, 'aws_instance_ip': '192.168.1.1', 'aws_instance_name': 'Test Instance 1'}
        
        # Call the check_host function
        success, latency = daemon.check_host(test_host)
        
        # Verify the result
        self.assertTrue(success)
        self.assertAlmostEqual(latency, 0.123, places=3)
        
        # Verify that update_rrd was called with the correct arguments
        mock_update_rrd.assert_called_once()
        args = mock_update_rrd.call_args[0]
        self.assertEqual(args[1], int(time.time()))  # timestamp
        self.assertEqual(args[2], 100)  # uptime (100%)
        self.assertAlmostEqual(args[3], 0.123, places=3)  # latency
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('monitors.icmp.daemon.update_rrd')
    def test_check_host_failure(self, mock_update_rrd, mock_path_exists, mock_subprocess_run):
        # Mock the subprocess.run function to return a failed ping
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_subprocess_run.return_value = mock_process
        
        # Mock os.path.exists to return True for the RRD file
        mock_path_exists.return_value = True
        
        # Create a test host
        test_host = {'id': 1, 'aws_instance_ip': '192.168.1.1', 'aws_instance_name': 'Test Instance 1'}
        
        # Call the check_host function
        success, latency = daemon.check_host(test_host)
        
        # Verify the result
        self.assertFalse(success)
        self.assertEqual(latency, 0)
        
        # Verify that update_rrd was called with the correct arguments
        mock_update_rrd.assert_called_once()
        args = mock_update_rrd.call_args[0]
        self.assertEqual(args[1], int(time.time()))  # timestamp
        self.assertEqual(args[2], 0)  # uptime (0%)
        self.assertEqual(args[3], 0)  # latency
    
    @patch('monitors.icmp.daemon.check_host')
    def test_check_host_thread(self, mock_check_host):
        # Mock the check_host function to return a successful ping
        mock_check_host.return_value = (True, 0.123)
        
        # Create a test host
        test_host = {'id': 1, 'aws_instance_ip': '192.168.1.1', 'aws_instance_name': 'Test Instance 1'}
        
        # Call the check_host_thread function
        daemon.check_host_thread(test_host)
        
        # Verify that check_host was called with the correct arguments
        mock_check_host.assert_called_once_with(test_host)
    
    def test_get_all_hosts(self):
        # Call the get_all_hosts function
        hosts = daemon.get_all_hosts()
        
        # Verify that hosts were returned
        self.assertEqual(len(hosts), 2)
        self.assertEqual(hosts[0]['id'], 1)
        self.assertEqual(hosts[0]['aws_instance_ip'], '192.168.1.1')
        self.assertEqual(hosts[1]['id'], 2)
        self.assertEqual(hosts[1]['aws_instance_ip'], '192.168.1.2')
    
    @patch('argparse.ArgumentParser.parse_args')
    @patch('monitors.icmp.daemon.run_checks')
    @patch('time.sleep')
    def test_main_loop(self, mock_sleep, mock_run_checks, mock_parse_args):
        """Test the main loop of the ICMP monitor."""
        import monitors.icmp.daemon
        
        # Mock the parse_args function to return a namespace with the required attributes
        mock_args = Namespace(interval=5, debug=False, action='start')
        mock_parse_args.return_value = mock_args
        
        # Save the original running state
        original_running = monitors.icmp.daemon.running
        
        try:
            # Mock the sleep function to exit the loop after one iteration
            def side_effect(seconds):
                monitors.icmp.daemon.running = False
            mock_sleep.side_effect = side_effect
            
            # Set running state for the test
            monitors.icmp.daemon.running = True
            
            # Run the main function
            result = monitors.icmp.daemon.main()
            
            # Assert that run_checks was called at least once
            self.assertGreaterEqual(mock_run_checks.call_count, 1)
            self.assertEqual(result, 0)
        finally:
            # Restore the original running state
            monitors.icmp.daemon.running = original_running
    
    def test_signal_handler(self):
        # Set the running flag to True
        daemon.running = True
        
        # Call the signal_handler function
        daemon.signal_handler(None, None)
        
        # Verify that the running flag was set to False
        self.assertFalse(daemon.running)

if __name__ == '__main__':
    unittest.main() 