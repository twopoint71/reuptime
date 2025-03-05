#!/bin/bash

# This script runs the tests for the ICMP monitor daemon

# Get the directory of this script
SCRIPT_DIR=$(dirname "$0")
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)

# Activate the virtual environment
source "$PROJECT_ROOT/.venv/bin/activate"

echo "Running tests for ICMP monitor daemon..."
cd "$PROJECT_ROOT"

# Run the original ICMP monitor tests
echo "Running basic ICMP monitor tests..."
python -m pytest tests/test_icmp_monitor.py -v

# Store the exit code of the first test run
BASIC_TESTS_RESULT=$?

# Store the exit code of the second test run
RRD_DB_TESTS_RESULT=$?

# Check the exit codes
if [ $BASIC_TESTS_RESULT -eq 0 ] && [ $RRD_DB_TESTS_RESULT -eq 0 ]; then
    echo -e "\nAll tests passed!"
    exit 0
else
    echo -e "\nSome tests failed."
    exit 1
fi
