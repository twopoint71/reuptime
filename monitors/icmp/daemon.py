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

# Add these global variables near the top with other globals
host_status_totals = {
    'hosts_up': 0,
    'hosts_down': 0,
    'total_hosts': 0
}

def get_all_hosts():
    """Get all hosts from the database."""
    with get_db(app_config) as db:
        return db.execute('SELECT * FROM hosts').fetchall()

def check_host(host, app_config):
    """Check a host's status and update metrics."""
    try:
        # Perform ICMP check
        result = subprocess.run(['ping', '-c', '1', '-w', '2', host['host_ip_address']], capture_output=True, text=True)
        success = result.returncode == 0

        # Handle status updates and downtime allotment - moved outside try/except
        try:
            # Check if we should use downtime allotment
            if not success and host['downtime_allotment'] > 0:
                # Get current allotment before updating
                current_allotment = host['downtime_allotment']
                new_allotment = current_allotment - 1

                # Use a downtime allotment point and treat as success
                with get_db(app_config) as db:
                    db.execute('''
                        UPDATE hosts
                        SET downtime_allotment = ?,
                            last_check = CURRENT_TIMESTAMP,
                            is_active = 1
                        WHERE uuid = ?
                    ''', (new_allotment, host['uuid']))
                    db.commit()

                success = True  # Treat as success for RRD and status updates
                logger.info(f"Used downtime allotment point for host {host['host_name']} ({new_allotment} remaining)")
            else:
                # Normal status update
                with get_db(app_config) as db:
                    db.execute('''
                        UPDATE hosts
                        SET last_check = CURRENT_TIMESTAMP,
                            is_active = ?
                        WHERE uuid = ?
                    ''', (1 if success else 0, host['uuid']))
                    db.commit()

            # Update status counters
            if success:
                host_status_totals['hosts_up'] += 1
            else:
                host_status_totals['hosts_down'] += 1

            # Update RRD database
            rrd_file = get_rrd_path(host['uuid'], app_config)
            if os.path.exists(rrd_file):
                try:
                    # Extract latency from ping output
                    latency = 0
                    if success and 'time=' in result.stdout:
                        latency_str = result.stdout.split('time=')[-1].split()[0]
                        latency = float(latency_str)

                    update_rrd(rrd_file, int(time.time()), 100 if success else 0, latency)
                except Exception as e:
                    logger.error(f"Error updating RRD file: {str(e)}")
            else:
                logger.warning(f"RRD file not found: {rrd_file}")

        except Exception as e:
            logger.error(f"Error updating host status: {str(e)}")
            # Don't raise here, we want to continue with other hosts

        return success

    except Exception as e:
        logger.error(f"Error checking host {host['host_name']}: {str(e)}")
        return False

def check_host_thread(host):
    """Thread function to check a host."""
    success = check_host(host, app_config)  # Only get the success value
    status = "UP" if success else "DOWN"

def run_checks():
    """Run checks on all hosts in parallel."""
    global host_status_totals

    # Check and reset allotments before running checks
    check_and_reset_allotments()

    hosts = get_all_hosts()
    if not hosts:
        logger.warning("No hosts found in database")
        return

    # Reset totals at the start of each check cycle
    host_status_totals['hosts_up'] = 0
    host_status_totals['hosts_down'] = 0
    host_status_totals['total_hosts'] = len(hosts)

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

    # Update aggregate RRD with the current totals
    update_aggregate_stats()

def update_aggregate_stats():
    """Update aggregate statistics using the current totals."""
    try:
        current_time = int(time.time())
        aligned_timestamp = math.floor(current_time / 20) * 20  # Align to 20-second interval

        uptime_percent = 0
        if host_status_totals['total_hosts'] > 0:
            uptime_percent = round((host_status_totals['hosts_up'] / host_status_totals['total_hosts']) * 100, 2)

        logger.info(f"Aggregate uptime: {uptime_percent}% (Up: {host_status_totals['hosts_up']}, "
                   f"Down: {host_status_totals['hosts_down']}, Total: {host_status_totals['total_hosts']})")

        aggregate_rrd = get_aggregate_rrd_path(app_config)

        if not os.path.exists(aggregate_rrd):
            logger.info(f"Creating aggregate uptime RRD file: {aggregate_rrd}")
            aggregate_rrd = init_aggregate_rrd(app_config)

        success = update_aggregate_rrd(
            aggregate_rrd,
            aligned_timestamp,
            host_status_totals['hosts_up'],
            host_status_totals['hosts_down'],
            uptime_percent
        )

        if not success:
            logger.error("Failed to update aggregate uptime RRD")

    except Exception as e:
        logger.error(f"Error updating aggregate stats: {str(e)}", exc_info=True)

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

def check_and_reset_allotments():
    """
    Check and reset downtime allotments based on calendar weeks.
    Resets occur on even-numbered weeks of the year.
    """
    try:
        with get_db(app_config) as db:
            # Get current week number (1-53)
            db.execute('''
                UPDATE hosts
                SET downtime_allotment = (
                    SELECT value
                    FROM settings
                    WHERE key = 'default_downtime_allotment'
                    LIMIT 1
                ),
                last_allotment_reset = CURRENT_TIMESTAMP
                WHERE (
                    -- Only reset on even-numbered weeks
                    CAST(strftime('%W', CURRENT_TIMESTAMP) AS INTEGER) % 2 = 0
                    -- Only reset if we haven't already reset this week
                    AND strftime('%W', last_allotment_reset) != strftime('%W', CURRENT_TIMESTAMP)
                )
            ''')

            # Log which hosts were reset
            reset_hosts = db.execute('''
                SELECT host_name, downtime_allotment
                FROM hosts
                WHERE strftime('%W', last_allotment_reset) = strftime('%W', CURRENT_TIMESTAMP)
                AND date(last_allotment_reset) = date(CURRENT_TIMESTAMP)
            ''').fetchall()

            if reset_hosts:
                logger.info(f"Week {datetime.now().strftime('%W')}: Reset downtime allotment for {len(reset_hosts)} hosts")
                for host in reset_hosts:
                    logger.debug(f"Reset downtime allotment for host {host['host_name']}")

            db.commit()
    except Exception as e:
        logger.error(f"Error checking/resetting downtime allotments: {str(e)}")

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