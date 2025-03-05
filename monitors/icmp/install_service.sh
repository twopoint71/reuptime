#!/bin/bash

# This script installs the ICMP monitor as a systemd service

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

# Get the directory of this script
SCRIPT_DIR=$(dirname "$0")
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)

echo "Installing ICMP monitor as a systemd service..."

# Fix permissions
bash "$SCRIPT_DIR/fix_permissions.sh"

# Copy the service file to the systemd directory
cp "$SCRIPT_DIR/icmp-monitor.service" /etc/systemd/system/

# Update the service file with the correct paths
sed -i "s|/home/bsmith/reuptime|$PROJECT_ROOT|g" /etc/systemd/system/icmp-monitor.service

# Reload systemd
systemctl daemon-reload

# Enable the service
systemctl enable icmp-monitor

echo "Service installed successfully!"
echo "You can now start the service with: sudo systemctl start icmp-monitor"
echo "Check the status with: sudo systemctl status icmp-monitor"
echo "View the logs with: sudo journalctl -u icmp-monitor -f" 