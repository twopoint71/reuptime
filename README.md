# ReUptime

A lightweight, self-hosted uptime monitoring solution for tracking the availability of your servers and services.

## Features

- **Simple Host Monitoring**: Track uptime and response time for servers and services
- **Real-time Metrics**: View performance metrics with interactive charts
- **Alerting**: Get notified when hosts go down or come back online
- **Historical Data**: Store and visualize historical uptime and performance data
- **Responsive UI**: Mobile-friendly interface with dark mode support
- **Low Resource Usage**: Minimal system requirements for the monitoring daemon

## Base Start
1. Clone the repository:
   ```
   git clone https://github.com/twopoint71/reuptime.git
   cd reuptime
   ```

## Docker-compose Start
1. Docker compose to build and start
   ```
   docker-compose up -d --build
   ```
  
## Non-docker-compose Start
1. Build the container
    ```
    sudo docker build -t reuptime:latest .
    ```

2. Create docker volume
    ```
    sudo docker volume create reuptime_data
    ```

3. Start container
    ```
    sudo docker run -d \
        --name reuptime \
        --publish 8000:8000 \
        --volume reuptime_data:/app/instance \
        --restart unless-stopped \
        --cap-add=NET_ADMIN \
        --environment TZ="Greenwich Mean Time" \
        reuptime:latest
    ```

## After Start
3. Access the web interface at http://localhost:8000

## Architecture

ReUptime has been converted to Django for a more opinionated desgin.

There are 3 main parts:
1. **Web App**: A standard djano web app to interface with the monitor and rrd services.
2. **Monitor**: A service app in the Django ecosystem to run various monitors (we're starting with ICMP)
3. **RRD**: A service to interface with and manage all the RRD files

## TODOS
There are unfinished items all over, but I have to get this to prod to start catching data
1. Implement additional monitor types. The web app framework is sort of there to support this in host and graph interactions.
2. Implement alert notifications. Under Admin Tools > Global Settings add a configuration item for a destination email relay.
3. Fix the CSV imports
4. Write Tests
5. The suggestion box is open.

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
