# Monitoring Daemon

The monitoring daemon is a background process that performs regular checks on configured hosts and records their status and performance metrics.

## Overview

The daemon is implemented in Python and uses ICMP (ping) to check host availability. It runs as a separate process from the web application and communicates with it through the database and status files.

## Architecture

The daemon consists of the following components:

1. **Main Process**: Manages the daemon lifecycle and scheduling
2. **Check Engine**: Performs ICMP checks on hosts
3. **RRD Manager**: Stores metrics in RRD files
4. **Status Manager**: Updates daemon status information

## Control Script

The daemon can be managed using the `control.sh` script located in the `monitors/icmp` directory: 