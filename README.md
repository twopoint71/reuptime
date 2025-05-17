# ReUptime

A lightweight, self-hosted uptime monitoring solution for tracking the availability of your servers and services.

## Features

- **Simple Host Monitoring**: Track uptime and response time for servers and services
- **Real-time Metrics**: View performance metrics with interactive charts
- **Alerting**: Get notified when hosts go down or come back online
- **Historical Data**: Store and visualize historical uptime and performance data
- **Responsive UI**: Mobile-friendly interface with dark mode support
- **Low Resource Usage**: Minimal system requirements for the monitoring daemon

## Quick Start

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/reuptime.git
   cd reuptime
   ```

2. Set up a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Initialize the database:
   ```
   ./manage.py makemigrations
   ./manage.py migrate
   ```

5. DEVELOPMENT: Start the application:
   ```
   ./manage.py runserver 0.0.0.0:8000
   ```

7. Start the monitoring daemon (also available on admin page):
   ```
   ./manage.py monitor_icmp start
   ```

8. Access the web interface at http://localhost:8000

## Architecture

ReUptime has been converted to Django for a more opinionated desgin. This was hand coded and AI was used to speed up the grunt work and even straighten some files up. No "vibing" was used in the creation of this project.

There are 3 main parts:
1. **Web App**: A standard djano web app to interface with the monitor and rrd services.
2. **Monitor**: A service app in the Django ecosystem to run various monitors (we're starting with ICMP)
3. **RRD**: A service to interface with and manage all the RRD files

## TODOS
There are unfinished items all over, but I have to get this to prod to start catching data
1. Implement additional monitor types. The web app framework is sort of there to support this in host and graph interactions.
2. Implement alert notifications. Under Admin Tools > Global Settings add a configuration item for a destination email relay.
3. Fix the CSV imports
4. The suggestion box is open.

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
