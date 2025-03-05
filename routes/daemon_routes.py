from flask import jsonify, request
import os
import sys
import time
import json
import subprocess
import pytz
from datetime import datetime

def register_daemon_routes(app):
    """Register routes for daemon management."""
    
    @app.route('/api/daemon/status')
    def daemon_status():
        """Get the status of the ICMP monitor daemon."""
        try:
            status_file = os.path.join(app.config['MONITOR_PATH'], 'icmp', 'daemon_status.json')
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    status_data = json.load(f)
                
                # Check if the process is still running
                if 'pid' in status_data:
                    try:
                        pid = int(status_data['pid'])
                        # Try to send signal 0 to the process to check if it's running
                        os.kill(pid, 0)
                    except (ProcessLookupError, ValueError):
                        # Process is not running
                        status_data['status'] = 'stopped'
                        status_data['message'] = 'Process is not running but status file exists'
                
                status_data['last_update'] = datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d %H:%M:%S %Z')
                return jsonify(status_data)
            else:
                return jsonify({
                    'status': 'unknown',
                    'message': 'Status file not found'
                })
        except Exception as e:
            return jsonify({
                'error': str(e)
            }), 500
    
    @app.route('/api/daemon/start', methods=['POST'])
    def start_daemon():
        """Start the ICMP monitor daemon."""
        try:
            # Check if daemon is already running
            status_file = os.path.join(app.config['MONITOR_PATH'], 'icmp', 'daemon_status.json')
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    status_data = json.load(f)
                
                if 'pid' in status_data:
                    try:
                        pid = int(status_data['pid'])
                        # Try to send signal 0 to the process to check if it's running
                        os.kill(pid, 0)
                        # Process is running
                        return jsonify({
                            'error': f'Daemon is already running with PID {pid}'
                        }), 400
                    except (ProcessLookupError, ValueError):
                        # Process is not running, continue with starting
                        pass
            
            # Start the daemon
            daemon_script = os.path.join(app.config['MONITOR_PATH'], 'icmp', 'daemon.py')
            
            # Make sure the script is executable
            try:
                os.chmod(daemon_script, 0o755)
            except Exception as e:
                print(f"Warning: Could not set executable permission on daemon script: {str(e)}")
            
            # Start the daemon in the background
            process = subprocess.Popen(
                [sys.executable, daemon_script, '--action', 'start'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True  # Detach from parent process
            )
            
            # Wait a short time to see if the process starts successfully
            time.sleep(1)
            
            # Check if the process is still running
            if process.poll() is None:
                # Process is still running
                return jsonify({
                    'success': True,
                    'message': 'Daemon started successfully'
                })
            else:
                # Process exited
                stdout, stderr = process.communicate()
                return jsonify({
                    'error': f'Daemon failed to start: {stderr.decode()}'
                }), 500
        except Exception as e:
            return jsonify({
                'error': str(e)
            }), 500
    
    @app.route('/api/daemon/stop', methods=['POST'])
    def stop_daemon():
        """Stop the ICMP monitor daemon."""
        try:
            # Run the daemon script with stop action
            daemon_script = os.path.join(app.config['MONITOR_PATH'], 'icmp', 'daemon.py')
            
            # Make sure the script is executable
            try:
                os.chmod(daemon_script, 0o755)
            except Exception as e:
                print(f"Warning: Could not set executable permission on daemon script: {str(e)}")
            
            result = subprocess.run(
                [sys.executable, daemon_script, '--action', 'stop'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return jsonify({
                    'success': True,
                    'message': 'Daemon stopped successfully'
                })
            else:
                return jsonify({
                    'error': f'Failed to stop daemon: {result.stderr}'
                }), 500
        except Exception as e:
            return jsonify({
                'error': str(e)
            }), 500 