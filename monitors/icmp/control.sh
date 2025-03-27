#!/bin/bash
# Control script for ICMP Monitor Daemon

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DAEMON_PATH="$SCRIPT_DIR/daemon.py"
PID_FILE="$SCRIPT_DIR/icmp_monitor.pid"
LOG_FILE="$SCRIPT_DIR/icmp_monitor.log"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
STATUS_FILE="$SCRIPT_DIR/daemon_status.json"

# Check if virtual environment exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment not found at $VENV_PYTHON"
    echo "Please create and activate the virtual environment first."
    exit 1
fi

# Make daemon.py executable
chmod +x "$DAEMON_PATH"

# Function to start the daemon using the same approach as the web interface
start() {
    # Check if daemon is already running by reading the status file
    if [ -f "$STATUS_FILE" ]; then
        PID=$(jq -r '.pid // 0' "$STATUS_FILE" 2>/dev/null)
        if [ -n "$PID" ] && [ "$PID" != "null" ] && [ "$PID" -gt 0 ] && ps -p "$PID" > /dev/null; then
            echo "ICMP Monitor Daemon is already running with PID $PID"
            return 0
        fi
    fi
    
    echo "Starting ICMP Monitor Daemon..."
    # Start the daemon with the same parameters as the web interface
    nohup "$VENV_PYTHON" "$DAEMON_PATH" --action start > "$LOG_FILE" 2>&1 &
    
    # Wait a moment for the daemon to initialize
    sleep 2
    
    # Check if the daemon started successfully by reading the status file
    if [ -f "$STATUS_FILE" ]; then
        STATUS=$(jq -r '.status' "$STATUS_FILE" 2>/dev/null)
        PID=$(jq -r '.pid // 0' "$STATUS_FILE" 2>/dev/null)
        if [ "$STATUS" = "running" ] && [ -n "$PID" ] && [ "$PID" != "null" ] && [ "$PID" -gt 0 ]; then
            echo "ICMP Monitor Daemon started with PID $PID"
            return 0
        fi
    fi
    
    echo "Failed to start daemon or verify its status. Check the log file for details."
    return 1
}

# Function to stop the daemon using the same approach as the web interface
stop() {
    echo "Stopping ICMP Monitor Daemon..."
    # Use the daemon.py script with stop action, just like the web interface
    "$VENV_PYTHON" "$DAEMON_PATH" --action stop
    
    # Wait a moment for the daemon to stop
    sleep 5
    
    # Check if the daemon stopped successfully
    if [ -f "$STATUS_FILE" ]; then
        STATUS=$(jq -r '.status' "$STATUS_FILE" 2>/dev/null)
        if [ "$STATUS" = "stopped" ] || [ "$STATUS" = "error" ]; then
            echo "ICMP Monitor Daemon stopped successfully"
            return 0
        fi
    fi
    
    # If status file doesn't indicate stopped, check if process is still running
    if [ -f "$STATUS_FILE" ]; then
        PID=$(jq -r '.pid // 0' "$STATUS_FILE" 2>/dev/null)
        if [ -n "$PID" ] && [ "$PID" != "null" ] && [ "$PID" -gt 0 ] && ! ps -p "$PID" > /dev/null; then
            echo "ICMP Monitor Daemon is not running (process terminated)"
            return 0
        elif [ -n "$PID" ] && [ "$PID" != "null" ] && [ "$PID" -gt 0 ]; then
            echo "Warning: Daemon process with PID $PID is still running"
            echo "Attempting to force termination..."
            kill -9 "$PID" 2>/dev/null
            return 1
        fi
    fi
    
    echo "Daemon status could not be determined"
    return 1
}

# Function to check the status of the daemon using the status file
status() {
    if [ -f "$STATUS_FILE" ]; then
        # Read status information from the status file
        STATUS=$(jq -r '.status' "$STATUS_FILE" 2>/dev/null)
        PID=$(jq -r '.pid // 0' "$STATUS_FILE" 2>/dev/null)
        MESSAGE=$(jq -r '.message' "$STATUS_FILE" 2>/dev/null)
        STARTED=$(jq -r '.timestamp // "unknown"' "$STATUS_FILE" 2>/dev/null)
        
        # Verify if the process is actually running
        if [ -n "$PID" ] && [ "$PID" != "null" ] && [ "$PID" -gt 0 ]; then
            if ps -p "$PID" > /dev/null; then
                PROCESS_STATUS="Process is running (secondary verification)"
            else
                PROCESS_STATUS="Process is NOT running (secondary verification)"
                STATUS="stopped (stale)"
            fi
        else
            PROCESS_STATUS="No valid PID found"
            STATUS="unknown"
        fi
        
        echo "=== ICMP Monitor Daemon Status ==="
        echo "Status: $STATUS"
        echo "Process: $PROCESS_STATUS"
        echo "PID: $PID"
        echo "Message: $MESSAGE"
        echo "Started: $STARTED"
        echo "Status File: $STATUS_FILE"
        
        # Return success if daemon is running
        if [ "$STATUS" = "running" ] && [ "$PROCESS_STATUS" = "Process is running" ]; then
            return 0
        else
            return 1
        fi
    else
        echo "Status file not found at $STATUS_FILE"
        echo "Daemon is likely not running or was not started properly"
        return 1
    fi
}

# Function to restart the daemon
restart() {
    stop
    sleep 2
    start
}

# Function to show the log
log() {
    if [ -f "$LOG_FILE" ]; then
        tail -n 50 "$LOG_FILE"
    else
        echo "Log file not found"
    fi
}

# Function to show the log in follow mode
follow() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo "Log file not found"
    fi
}

# Function to display help information
show_help() {
    echo "ICMP Monitor Daemon Control Script"
    echo "=================================="
    echo
    echo "This script manages the ICMP Monitor Daemon using the same Python interface"
    echo "as the web application. It uses the daemon status file to track the daemon state."
    echo
    echo "Commands:"
    echo "  start   - Start the ICMP Monitor Daemon if it's not already running"
    echo "            Uses the daemon.py script with --action start parameter"
    echo "            Verifies startup by checking the daemon_status.json file"
    echo
    echo "  stop    - Stop the running ICMP Monitor Daemon"
    echo "            Uses the daemon.py script with --action stop parameter"
    echo "            Verifies shutdown by checking the daemon_status.json file"
    echo "            Will attempt to force kill the process if graceful shutdown fails"
    echo
    echo "  restart - Stop and then start the ICMP Monitor Daemon"
    echo "            Useful for applying configuration changes"
    echo
    echo "  status  - Display detailed status information about the daemon"
    echo "            Shows status, PID, message, check interval, and last check time"
    echo "            Verifies if the process is actually running"
    echo
    echo "  log     - Display the last 50 lines of the daemon log file"
    echo "            Log file: $LOG_FILE"
    echo
    echo "  follow  - Display and follow the daemon log file in real-time"
    echo "            Press Ctrl+C to exit"
    echo
    echo "Examples:"
    echo "  control.sh start"
    echo "  control.sh stop"
    echo "  control.sh status"
    echo
    echo "Files:"
    echo "  Daemon Script: $DAEMON_PATH"
    echo "  Status File:   $STATUS_FILE"
    echo "  Log File:      $LOG_FILE"
    echo
    echo "Note: This script requires the 'jq' utility for parsing JSON status files."
    echo
}

# Check if jq is installed
check_dependencies() {
    if ! command -v jq &> /dev/null; then
        echo "Error: jq is not installed but is required for parsing JSON status files"
        echo "Please install jq using your package manager:"
        echo "  For Debian/Ubuntu: sudo apt-get install jq"
        echo "  For CentOS/RHEL: sudo yum install jq"
        echo "  For macOS: brew install jq"
        exit 1
    fi
}

# Check dependencies
check_dependencies

# Main script logic
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    log)
        log
        ;;
    follow)
        follow
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        show_help
        exit 1
        ;;
esac

exit 0 