#!/bin/bash

# This script fixes the permissions of the files in the monitors/icmp directory
# It needs to be run with sudo

echo "Fixing permissions for ICMP monitor files..."

# Change ownership of all files in the directory to the current user
sudo chown -R $(whoami):$(whoami) $(dirname "$0")

# Make the scripts executable
sudo chmod +x $(dirname "$0")/daemon.py
sudo chmod +x $(dirname "$0")/control.sh
sudo chmod +x $(dirname "$0")/fix_permissions.sh
sudo chmod +x $(dirname "$0")/run_tests.sh
sudo chmod +x $(dirname "$0")/install_service.sh

echo "Permissions fixed successfully!"
echo "The following files are now executable:"
echo "- daemon.py"
echo "- control.sh"
echo "- fix_permissions.sh"
echo "- run_tests.sh"
echo "- install_service.sh"

# Show the new permissions
echo -e "\nCurrent permissions:"
ls -la $(dirname "$0") 