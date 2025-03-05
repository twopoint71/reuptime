#!/bin/bash

# Script to fix permissions for all files and directories in the ReUptime project
# Run this script if you encounter permission issues

# Get the directory of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Fixing permissions for ReUptime project..."

# Create directories if they don't exist
mkdir -p rrd
mkdir -p monitors/icmp

# Fix permissions for directories
echo "Setting directory permissions..."
find . -type d -exec chmod 755 {} \;

# Fix permissions for Python files
echo "Setting permissions for Python files..."
find . -name "*.py" -exec chmod 644 {} \;

# Fix permissions for shell scripts
echo "Setting permissions for shell scripts..."
find . -name "*.sh" -exec chmod 755 {} \;

# Fix permissions for the database file
echo "Setting permissions for database file..."
if [ -f uptime.db ]; then
    chmod 644 uptime.db
    echo "Database file permissions set."
else
    echo "Database file not found. It will be created with the correct permissions when the application runs."
fi

# Fix permissions for RRD files
echo "Setting permissions for RRD files..."
if [ -d rrd ]; then
    find rrd -name "*.rrd" -exec chmod 644 {} \;
    echo "RRD file permissions set."
else
    echo "RRD directory not found. It will be created with the correct permissions when the application runs."
fi

# Fix permissions for log files
echo "Setting permissions for log files..."
if [ -d monitors/icmp ]; then
    find monitors/icmp -name "*.log" -exec chmod 644 {} \;
    echo "Log file permissions set."
else
    echo "Monitors directory not found. It will be created with the correct permissions when the application runs."
fi

echo "Permissions fixed successfully!"
echo "You can now run the application with: python app.py" 