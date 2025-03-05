import os
import subprocess
from datetime import datetime
from pathlib import Path

def setup_directories(config):
    """Create necessary directories for RRD files."""
    base_dir = os.path.dirname(config['DATABASE']) if config['TESTING'] else '.'
    
    # If base_dir is empty, use current directory
    if not base_dir:
        base_dir = '.'
    
    directories = [
        os.path.join(base_dir, 'rrd'),
        os.path.join(base_dir, 'monitors', 'icmp')
    ]
    
    for directory in directories:
        try:
            print(f"Creating directory: {directory}")
            Path(directory).mkdir(parents=True, exist_ok=True)
            
            # Ensure directory has proper permissions
            try:
                os.chmod(directory, 0o755)
                print(f"Directory created and permissions set: {directory}")
            except Exception as e:
                print(f"Warning: Could not set permissions for directory {directory}: {str(e)}")
        except Exception as e:
            print(f"Error creating directory {directory}: {str(e)}")
    
    # Create an empty log file if it doesn't exist
    log_file = config['MONITOR_LOG_PATH']
    if not os.path.exists(log_file):
        try:
            print(f"Creating log file: {log_file}")
            # Ensure the directory exists
            log_dir = os.path.dirname(log_file)
            if not os.path.exists(log_dir):
                Path(log_dir).mkdir(parents=True, exist_ok=True)
                try:
                    os.chmod(log_dir, 0o755)
                except Exception as e:
                    print(f"Warning: Could not set permissions for log directory {log_dir}: {str(e)}")
            
            with open(log_file, 'w') as f:
                f.write(f"[INFO] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Log file created\n")
            
            try:
                os.chmod(log_file, 0o644)
                print(f"Log file created and permissions set: {log_file}")
            except Exception as e:
                print(f"Warning: Could not set permissions for log file {log_file}: {str(e)}")
        except Exception as e:
            print(f"Error creating log file {log_file}: {str(e)}")

def read_last_n_lines(file_path, n):
    """Read the last n lines from a file."""
    try:
        # Use the tail command to get the last n lines
        result = subprocess.run(
            ['tail', '-n', str(n), file_path],
            capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        # Fallback to Python implementation if tail command fails
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                return ''.join(lines[-n:])
        except Exception as e:
            return f"Error reading log file: {str(e)}"

def check_host(host, config):
    """Check a host's status and update metrics."""
    import time
    import subprocess
    import os
    from db import get_db
    from rrd_utils import get_rrd_path, update_rrd
    
    try:
        # Perform ICMP check
        result = subprocess.run(['ping', '-c', '1', host['host_ip_address']],
                              capture_output=True, text=True)
        success = result.returncode == 0
        
        # Update host status
        with get_db(config) as db:
            db.execute('''
                UPDATE hosts 
                SET last_check = CURRENT_TIMESTAMP, is_active = ?
                WHERE id = ?
            ''', (1 if success else 0, host['id']))
            db.commit()
        
        # Update RRD database
        rrd_file = get_rrd_path(host['id'], config)
        if os.path.exists(rrd_file):
            try:
                # Extract latency from ping output
                latency = 0
                if success and 'time=' in result.stdout:
                    latency_str = result.stdout.split('time=')[-1].split()[0]
                    latency = float(latency_str)
                
                update_rrd(rrd_file, int(time.time()), 100 if success else 0, latency)
            except Exception as e:
                print(f"Error updating RRD file: {str(e)}")
        
        return success
    except Exception as e:
        print(f"Error checking host {host['host_name']}: {str(e)}")
        with get_db(config) as db:
            db.execute('''
                UPDATE hosts 
                SET last_check = CURRENT_TIMESTAMP, is_active = 0
                WHERE id = ?
            ''', (host['id'],))
            db.commit()
        return False 