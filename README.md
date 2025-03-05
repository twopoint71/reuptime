# ReUptime

A lightweight, self-hosted uptime monitoring solution for tracking the availability of your servers and services.

## Features

- **Simple Host Monitoring**: Track uptime and response time for servers and services
- **Real-time Metrics**: View performance metrics with interactive charts
- **Alerting**: Get notified when hosts go down or come back online
- **Historical Data**: Store and visualize historical uptime and performance data
- **Responsive UI**: Mobile-friendly interface with dark mode support
- **Low Resource Usage**: Minimal system requirements for the monitoring daemon
- **API-First Design**: RESTful API for all functionality

## Quick Start

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/reuptime.git
   cd reuptime
   ```

2. Set up a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Initialize the database:
   ```
   flask --app app init-db
   ```

5. Start the application:
   ```
   flask --app app run
   ```

6. Start the monitoring daemon:
   ```
   ./monitors/icmp/control.sh start
   ```

7. Access the web interface at http://localhost:5000

## Architecture

ReUptime consists of two main components:

1. **Web Application**: Flask-based web interface and API for managing hosts and viewing metrics
2. **Monitoring Daemon**: Background process that performs regular checks on hosts

### Monitoring Daemon

The monitoring daemon runs in the background and performs ICMP (ping) checks on configured hosts at regular intervals. It stores the results in RRD (Round Robin Database) files for efficient time-series data storage.

You can control the daemon using the provided control script:

## Documentation

For more detailed documentation, please see the [docs](./docs) directory:

- [Architecture](./docs/architecture.md)
- [API Reference](./docs/api-reference.md)
- [Daemon Control](./docs/daemon-control.md)
- [Database Schema](./docs/database-schema.md)
- [Frontend Guide](./docs/frontend-guide.md)

## Tips
If the ping service is run in user space, it may fail due to permissions.
Check if cap_net_raw is available with

    getcap /bin/ping

If cap_net_raw permissions are not available, try the following command to allow the permission in user space.

	sudo setcap cap_net_raw+p /bin/ping

Use this header CSV file imports:

    "Account Label","Account Id","Region","Host Id","Host IP Address","Hostname"

## License

This project is licensed under the MIT License - see the LICENSE file for details.
