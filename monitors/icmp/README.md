# ICMP Monitor Daemon

This daemon pings all hosts in the database every 5 seconds and records the results in the RRD database. It runs continuously in the background.

## Features

- Monitors all hosts in the database using ICMP ping
- Updates host status in the database
- Records uptime and latency metrics in RRD database
- Runs as a daemon process
- Handles errors gracefully
- Logs all activity to a log file
- Can be controlled via a shell script or systemd service

## Requirements

- Python 3.6+
- RRDtool
- SQLite3
- Access to ping command (requires appropriate permissions)

## Installation

1. Ensure the virtual environment is set up and activated:
   ```bash
   cd /home/bsmith/reuptime
   source .venv/bin/activate
   ```

2. Fix permissions for the scripts (if needed):
   ```bash
   sudo bash monitors/icmp/fix_permissions.sh
   ```
   This script will:
   - Change ownership of all files in the directory to the current user
   - Make the necessary scripts executable

3. The following files should now be executable:
   - `monitors/icmp/daemon.py`
   - `monitors/icmp/control.sh`
   - `monitors/icmp/fix_permissions.sh`
   - `monitors/icmp/run_tests.sh`
   - `monitors/icmp/install_service.sh`

## Usage

### Using the Control Script

The control script provides a simple interface to start, stop, and manage the daemon:

```bash
# Start the daemon
./monitors/icmp/control.sh start

# Stop the daemon
./monitors/icmp/control.sh stop

# Restart the daemon
./monitors/icmp/control.sh restart

# Check the status of the daemon
./monitors/icmp/control.sh status

# View the last 50 lines of the log
./monitors/icmp/control.sh log

# Follow the log in real-time
./monitors/icmp/control.sh follow
```

### Using Systemd

To install and use the systemd service:

1. Run the installation script:
   ```bash
   sudo bash monitors/icmp/install_service.sh
   ```
   This script will:
   - Fix permissions for the scripts
   - Copy the service file to the systemd directory
   - Update the service file with the correct paths
   - Reload systemd
   - Enable the service

2. Start the service:
   ```bash
   sudo systemctl start icmp-monitor
   ```

3. Check the status:
   ```bash
   sudo systemctl status icmp-monitor
   ```

4. View the logs:
   ```bash
   sudo journalctl -u icmp-monitor -f
   ```

## Testing

To run the tests for the ICMP monitor daemon:

```bash
bash monitors/icmp/run_tests.sh
```

This script will:
- Activate the virtual environment
- Run the tests using pytest
- Display the test results

## Configuration

The daemon accepts the following command-line arguments:

- `--interval`: Interval between checks in seconds (default: 5)
- `--debug`: Enable debug logging

Example:
```bash
python monitors/icmp/daemon.py --interval 10 --debug
```

## Logs

Logs are written to `monitors/icmp/icmp_monitor.log` and also to the console.

## Troubleshooting

1. **Daemon won't start**: Check the log file for errors. Ensure the database exists and is accessible.

2. **Permission denied**: Ensure the user has permission to run the ping command. You may need to run the daemon as root or use capabilities:
   ```bash
   sudo setcap cap_net_raw+ep /usr/bin/ping
   ```

3. **Database errors**: Ensure the database path is correct and the database is not locked by another process.

4. **RRD errors**: Ensure the RRD files exist and are writable. Check that RRDtool is installed correctly.

5. **File permission issues**: If you encounter permission issues, run the fix_permissions.sh script:
   ```bash
   sudo bash monitors/icmp/fix_permissions.sh
   ``` 