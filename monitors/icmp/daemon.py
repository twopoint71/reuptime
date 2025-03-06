#!/usr/bin/env python3
"""
ICMP Monitor Daemon

This daemon pings all hosts in the database every 5 seconds and records the results
in the RRD database. It runs continuously in the background.
"""

import os
import sys
import time
import signal
import logging
import threading
from datetime import datetime
import argparse
import json
import atexit
import subprocess
import math

# Add the parent directory to the path so we can import from the root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from rrd_utils import get_rrd_path, update_rrd, get_aggregate_rrd_path, init_aggregate_rrd, update_aggregate_rrd
from db import get_db, init_db, get_default_db_path  # Import get_default_db_path from db.py

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'icmp_monitor.log'))
    ]
)
logger = logging.getLogger('icmp_monitor')

# Global variables
running = True
# Get database path from db.py instead of hardcoding it
db_path = get_default_db_path()
pid_file = os.path.abspath(os.path.join(os.path.dirname(__file__), 'daemon.pid'))
status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), 'daemon_status.json'))
app_config = {
    'TESTING': False,
    'DATABASE': db_path,
    'MONITOR_LOG_PATH': os.path.join(os.path.dirname(__file__), 'icmp_monitor.log')
}

def get_all_hosts():
    """Get all hosts from the database."""
    with get_db(app_config) as db:
        return db.execute('SELECT * FROM hosts').fetchall()

def check_host(host):
    """
    Check a host's status using ICMP ping and update metrics.
    
    Args:
        host: A database row containing host information
        
    Returns:
        tuple: (success, latency) where success is a boolean and latency is in ms
    """
    try:
        # Perform ICMP check with shorter timeout (1 second)
        # Add -W 1 to set the timeout to 1 second
        result = subprocess.run(
            ['ping', '-c', '1', '-W', '2', host['host_ip_address']],
            capture_output=True, text=True, timeout=2  # Also reduce the subprocess timeout to 2 seconds
        )
        success = result.returncode == 0
        
        # Update host status in database
        with get_db(app_config) as db:
            db.execute('''
                UPDATE hosts 
                SET last_check = CURRENT_TIMESTAMP, is_active = ?
                WHERE id = ?
            ''', (1 if success else 0, host['id']))
            db.commit()
        
        # Extract latency from ping output
        latency = 0
        if success and 'time=' in result.stdout:
            latency_str = result.stdout.split('time=')[-1].split()[0]
            try:
                latency = float(latency_str)
            except ValueError:
                logger.warning(f"Could not parse latency from ping output: {result.stdout}")
        
        # Update RRD database
        rrd_file = get_rrd_path(host['id'], app_config)
        if os.path.exists(rrd_file):
            update_rrd(rrd_file, int(time.time()), 100 if success else 0, latency)
            logger.debug(f"Updated RRD for host {host['host_name']} (ID: {host['id']}): success={success}, latency={latency}ms")
        else:
            logger.warning(f"RRD file not found for host {host['host_name']} (ID: {host['id']})")
            # Try to create the RRD file
            try:
                from rrd_utils import init_rrd
                logger.info(f"Attempting to create RRD file for host {host['host_name']} (ID: {host['id']})")
                init_rrd(host['id'], app_config)
                logger.info(f"Successfully created RRD file for host {host['host_name']} (ID: {host['id']})")
                # Update the newly created RRD file
                update_rrd(rrd_file, int(time.time()), 100 if success else 0, latency)
            except Exception as e:
                logger.error(f"Failed to create RRD file for host {host['host_name']} (ID: {host['id']}): {str(e)}")
        
        # Log the result
        if success:
            logger.info(f"Host {host['host_name']} ({host['host_ip_address']}) is UP with latency {latency}ms")
        else:
            logger.warning(f"Host {host['host_name']} ({host['host_ip_address']}) is DOWN")
        
        return success, latency
    except subprocess.TimeoutExpired:
        logger.warning(f"Ping timeout for host {host['host_name']} (ID: {host['id']})")
        with get_db(app_config) as db:
            db.execute('''
                UPDATE hosts 
                SET last_check = CURRENT_TIMESTAMP, is_active = 0
                WHERE id = ?
            ''', (host['id'],))
            db.commit()
        
        # Update RRD with 0 uptime and max latency
        rrd_file = get_rrd_path(host['id'], app_config)
        if os.path.exists(rrd_file):
            update_rrd(rrd_file, int(time.time()), 0, 1000)
        
        return False, 1000
    except Exception as e:
        logger.error(f"Error checking host {host['host_name']} (ID: {host['id']}): {str(e)}")
        with get_db(app_config) as db:
            db.execute('''
                UPDATE hosts 
                SET last_check = CURRENT_TIMESTAMP, is_active = 0
                WHERE id = ?
            ''', (host['id'],))
            db.commit()
        
        # Update RRD with 0 uptime and max latency
        rrd_file = get_rrd_path(host['id'], app_config)
        if os.path.exists(rrd_file):
            update_rrd(rrd_file, int(time.time()), 0, 1000)
        
        return False, 1000

def check_host_thread(host):
    """Thread function to check a host."""
    success, latency = check_host(host)
    status = "UP" if success else "DOWN"

def run_checks():
    """Run checks on all hosts in parallel."""
    hosts = get_all_hosts()
    if not hosts:
        logger.warning("No hosts found in database")
        return
    
    logger.info(f"Checking {len(hosts)} hosts...")
    threads = []
    
    for host in hosts:
        thread = threading.Thread(target=check_host_thread, args=(host,))
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    logger.info(f"Completed checking {len(hosts)} hosts")
    
    # Spawn a new thread to calculate and store aggregate uptime
    aggregate_thread = threading.Thread(target=get_aggregate_uptime)
    aggregate_thread.daemon = True
    aggregate_thread.start()
    aggregate_thread.join()  # Wait for the aggregate calculation to complete

def signal_handler(sig, frame):
    """Handle signals to gracefully shut down the daemon."""
    global running
    logger.info("Received signal to stop. Shutting down...")
    running = False

def update_status(status, message=None):
    """Update the daemon status file."""
    try:
        status_data = {
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'pid': os.getpid(),
            'message': message
        }
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
        logger.debug(f"Updated status to {status}")
    except Exception as e:
        logger.error(f"Error updating status file: {str(e)}")

def cleanup():
    """Clean up resources when the daemon exits."""
    try:
        if os.path.exists(pid_file):
            os.remove(pid_file)
        update_status('stopped', 'Daemon stopped')
        logger.info("Daemon cleanup completed")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

def get_aggregate_uptime():
    """
    Get the aggregate uptime statistics for all hosts and store in a dedicated RRD file.
    This runs as a separate thread after each monitoring cycle.
    """
    try:
        logger.debug("Starting aggregate uptime calculation")
        
        # Get all hosts
        hosts = get_all_hosts()
        if not hosts:
            logger.warning("No hosts found for aggregate uptime calculation")
            return
        
        # Count hosts up and down
        hosts_up = 0
        hosts_down = 0
        total_hosts = len(hosts)
        
        # Get the current timestamp aligned to the interval
        current_time = int(time.time())
        aligned_timestamp = math.floor(current_time / 20) * 20  # Align to 20-second interval
        
        # Check each host's status
        for host in hosts:
            if host['is_active']:
                hosts_up += 1
            else:
                hosts_down += 1
        
        # Calculate uptime percentage
        uptime_percent = 0
        if total_hosts > 0:
            uptime_percent = round((hosts_up / total_hosts) * 100, 2)
        
        logger.info(f"Aggregate uptime: {uptime_percent}% (Up: {hosts_up}, Down: {hosts_down}, Total: {total_hosts})")
        
        # Import the necessary functions from rrd_utils
        from rrd_utils import get_aggregate_rrd_path, init_aggregate_rrd, update_aggregate_rrd
        
        # Get the path to the aggregate RRD file
        aggregate_rrd = get_aggregate_rrd_path(app_config)
        
        # Create the RRD file if it doesn't exist
        if not os.path.exists(aggregate_rrd):
            logger.info(f"Creating aggregate uptime RRD file: {aggregate_rrd}")
            aggregate_rrd = init_aggregate_rrd(app_config)
        
        # Update the RRD file with current values
        logger.debug(f"Updating aggregate RRD at {aligned_timestamp} with values: hosts_up={hosts_up}, hosts_down={hosts_down}, uptime_percent={uptime_percent}")
        success = update_aggregate_rrd(aggregate_rrd, aligned_timestamp, hosts_up, hosts_down, uptime_percent)
        
        if success:
            logger.debug(f"Successfully updated aggregate uptime RRD")
        else:
            logger.error(f"Failed to update aggregate uptime RRD")
        
    except Exception as e:
        logger.error(f"Error calculating aggregate uptime: {str(e)}", exc_info=True)

def main():
    """Main function to run the daemon."""
    parser = argparse.ArgumentParser(description='ICMP Monitor Daemon')
    parser.add_argument('--interval', type=int, default=20, help='Interval between checks in seconds (default: 20)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--action', choices=['start', 'stop', 'status'], default='start', 
                        help='Action to perform (start, stop, status)')
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Handle different actions
    if args.action == 'status':
        if os.path.exists(status_file):
            try:
                with open(status_file, 'r') as f:
                    status = json.load(f)
                print(f"Daemon status: {status['status']}")
                print(f"Last update: {status['timestamp']}")
                if 'pid' in status:
                    print(f"PID: {status['pid']}")
                if 'message' in status and status['message']:
                    print(f"Message: {status['message']}")
                return 0
            except Exception as e:
                print(f"Error reading status file: {str(e)}")
                return 1
        else:
            print("Daemon is not running")
            return 1
    
    elif args.action == 'stop':
        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                print(f"Stopping daemon with PID {pid}...")
                os.kill(pid, signal.SIGTERM)
                print("Stop signal sent")
                return 0
            except ProcessLookupError:
                print("Daemon is not running, removing stale PID file")
                os.remove(pid_file)
                update_status('stopped', 'Daemon was not running')
                return 0
            except Exception as e:
                print(f"Error stopping daemon: {str(e)}")
                return 1
        else:
            print("Daemon is not running")
            return 0
    
    # Start action
    # Check if already running
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            # Check if process is still running
            os.kill(pid, 0)  # This will raise an exception if the process is not running
            print(f"Daemon is already running with PID {pid}")
            return 1
        except ProcessLookupError:
            print("Removing stale PID file")
            os.remove(pid_file)
        except Exception as e:
            print(f"Error checking daemon status: {str(e)}")
    
    # Write PID file
    try:
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
    except Exception as e:
        print(f"Error writing PID file: {str(e)}")
        return 1
    
    # Register cleanup handler
    atexit.register(cleanup)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info(f"Starting ICMP monitor daemon with {args.interval} second interval")
    logger.info(f"Using database: {db_path}")
    
    try:
        # Initialize the database using the imported function
        init_db(app_config)
        
        # Update status
        update_status('running', f'Daemon started with {args.interval} second interval')
        
        # Initial check to make sure everything is working
        run_checks()
        
        # Main loop
        while running:
            start_time = time.time()
            run_checks()
            
            # Calculate sleep time to maintain consistent interval
            elapsed = time.time() - start_time
            sleep_time = max(0.1, args.interval - elapsed)
            
            if sleep_time < 1:
                logger.warning(f"Check took longer than interval: {elapsed:.2f}s > {args.interval}s")
            
            # Sleep until next check
            time.sleep(sleep_time)
    
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        update_status('error', str(e))
        return 1
    
    logger.info("ICMP monitor daemon stopped")
    update_status('stopped', 'Daemon stopped normally')
    return 0

if __name__ == "__main__":
    sys.exit(main()) 