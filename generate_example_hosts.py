from app import app, get_db, init_rrd, get_rrd_path
from datetime import datetime, timedelta
import random
import rrdtool
import os
import time
import sqlite3
import argparse
from app import init_db, setup_directories
from rrd_utils import get_last_update

def generate_hosts(refresh_existing=False, num_hosts=10):
    """
    Generate example hosts with metrics.
    
    Args:
        refresh_existing (bool): If True, keep existing hosts and only add new ones if fewer than num_hosts exist.
                                If False, delete all existing hosts and create new ones.
        num_hosts (int): Number of hosts to generate.
    """
    with app.app_context():
        # Initialize database and create necessary directories
        init_db()
        setup_directories()
        
        # regions (use popular cloud provider regions)
        regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-2', 'sa-east-1']

        # Example account labels
        account_labels = ['Production', 'Staging', 'Development', 'Testing', 'QA']
        
        with get_db() as db:
            # Check if we're refreshing or replacing hosts
            if refresh_existing:
                # Count existing hosts
                existing_count = db.execute('SELECT COUNT(*) FROM hosts').fetchone()[0]
                print(f"Found {existing_count} existing hosts")
                
                # If we have enough hosts already, just update their metrics
                if existing_count >= num_hosts:
                    hosts = db.execute('SELECT id, host_name, is_active FROM hosts').fetchall()
                    print(f"Refreshing metrics for {len(hosts)} existing hosts")
                    
                    for host in hosts:
                        update_host_metrics(host['id'], host['host_name'], bool(host['is_active']))
                    
                    db.commit()
                    print(f"Successfully refreshed metrics for {len(hosts)} existing hosts!")
                    return
                
                # If we don't have enough hosts, we'll add more to reach num_hosts
                hosts_to_add = num_hosts - existing_count
                print(f"Adding {hosts_to_add} new hosts to reach target of {num_hosts}")
            else:
                # Clear existing hosts
                print("Deleting all existing hosts")
                db.execute('DELETE FROM hosts')
                db.commit()
                hosts_to_add = num_hosts
            
            # Generate new hosts if needed
            if hosts_to_add > 0:
                for i in range(hosts_to_add):
                    # Generate random account ID (12 digits)
                    account_id = ''.join([str(random.randint(0, 9)) for _ in range(12)])

                    # Generate random instance ID
                    instance_id = f'i-{random.randint(1000000000, 9999999999)}abcdef{random.randint(0, 9)}'

                    # Generate random IP (for demonstration)
                    ip = f'10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}'

                    # Generate random name
                    name = f'Server-{random.randint(1, 100)}'

                    # Randomly set active status
                    is_active = random.choice([True, False])

                    # Generate random timestamps
                    created_at = datetime.utcnow() - timedelta(days=random.randint(1, 30))
                    last_check = datetime.utcnow() - timedelta(minutes=random.randint(0, 60)) if is_active else None

                    cursor = db.execute('''
                        INSERT INTO hosts (
                            account_label, account_id, region,
                            host_id, host_ip_address, host_name,
                            is_active, last_check, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        random.choice(account_labels),
                        account_id,
                        random.choice(regions),
                        instance_id,
                        ip,
                        name,
                        1 if is_active else 0,
                        last_check,
                        created_at
                    ))
                    host_id = cursor.lastrowid
                    
                    # Initialize RRD database and add metrics
                    update_host_metrics(host_id, name, is_active)
                
                db.commit()
                print(f"Successfully generated {hosts_to_add} new hosts with metrics!")
            
            # If we're refreshing, also update metrics for existing hosts
            if refresh_existing and existing_count > 0:
                hosts = db.execute('SELECT id, host_name, is_active FROM hosts LIMIT ?', 
                                  (existing_count,)).fetchall()
                print(f"Refreshing metrics for {len(hosts)} existing hosts")
                
                for host in hosts:
                    update_host_metrics(host['id'], host['host_name'], bool(host['is_active']))
                
                db.commit()
                print(f"Successfully refreshed metrics for {len(hosts)} existing hosts!")

def update_host_metrics(host_id, host_name, is_active):
    """
    Update metrics for a host.
    
    Args:
        host_id (int): Host ID
        host_name (str): Host name
        is_active (bool): Whether the host is active
    """
    # Initialize RRD database for the host
    init_rrd(host_id, app.config)

    # Generate sample metrics for the last 24 hours
    rrd_file = get_rrd_path(host_id)
    if os.path.exists(rrd_file):
        # Verify the database is ready by trying to read its info
        try:
            rrdtool.info(rrd_file)
        except rrdtool.OperationalError as e:
            print(f"Warning: RRD database for host {host_id} is not ready: {str(e)}")
            return

        # Get the last update time from the RRD file
        last_update_info = get_last_update(rrd_file)
        
        if last_update_info:
            # Use the last update timestamp as the base for new data points
            # Add 300 seconds (5 minutes) to avoid timestamp conflicts
            base_timestamp = last_update_info['timestamp'] + 300
            print(f"Using last update timestamp as base: {base_timestamp} for host {host_id}")
        else:
            # If no last update info, use current time minus 24 hours
            base_timestamp = int((time.time() - 86400) / 300) * 300  # Round to nearest 5 minutes
            print(f"No last update info, using time-24h as base: {base_timestamp} for host {host_id}")

        # Generate data points in memory first
        data_points = []

        # Generate timestamps in chronological order, starting from base_timestamp
        # Make sure we don't generate timestamps in the future
        current_time = int(time.time())
        end_timestamp = min(current_time - 300, base_timestamp + (287 * 300))  # Ensure we don't go into the future
        
        # Generate up to 288 points (24 hours at 5-minute intervals) or fewer if we hit current time
        timestamps = []
        timestamp = base_timestamp
        while timestamp <= end_timestamp and len(timestamps) < 288:
            timestamps.append(timestamp)
            timestamp += 300

        # Generate data points with timestamps in order
        for timestamp in timestamps:
            # Generate random uptime between 95-100% for active hosts, 0-5% for inactive
            uptime = random.uniform(95, 100) if is_active else random.uniform(0, 5)
            # Generate random latency between 1-50ms for active hosts, 1000-2000ms for inactive
            latency = random.uniform(1, 50) if is_active else random.uniform(1000, 2000)
            data_points.append((timestamp, uptime, latency))

        # Write all data points to RRD file in chronological order
        try:
            if data_points:
                # First, try to update with the first data point to establish the base
                first_timestamp, first_uptime, first_latency = data_points[0]
                rrdtool.update(rrd_file, f'{first_timestamp}:{first_uptime}:{first_latency}')

                # Then update with the rest of the data points
                for timestamp, uptime, latency in data_points[1:]:
                    rrdtool.update(rrd_file, f'{timestamp}:{uptime}:{latency}')
                
                print(f"Updated metrics for host {host_id} ({host_name}) with {len(data_points)} data points")
            else:
                print(f"No new data points to add for host {host_id} ({host_name})")
        except rrdtool.OperationalError as e:
            print(f"Warning: Could not update RRD file for host {host_id}: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate example hosts with metrics')
    parser.add_argument('--refresh', action='store_true', help='Refresh existing hosts instead of replacing them')
    parser.add_argument('--num-hosts', type=int, default=10, help='Number of hosts to generate (default: 10)')
    args = parser.parse_args()
    
    generate_hosts(refresh_existing=args.refresh, num_hosts=args.num_hosts)
