# Uptime Monitor

A project to monitor host uptime via ICMP.

## Features

- **Host Management**: Standard CRUD operations on a per-host basis via a browser-based UI
- **CSV Import**: Bulk import hosts from a CSV file.
- **Uptime Monitoring**: Check host availability using ICMP (ping)
- **Metrics Collection**: Track uptime statistics (success rate, latency) for each host. Stores up to 13 months of metrics per host.
- **Visualization**: View uptime metrics with RRDTool-generated graphs
- **Persistent Storage**: Store host data in SQLite3 database
- **Time Series Data**: Store metrics data in RRDTool databases
- **Dark Mode**: Toggle between light and dark themes for better visibility in different environments

#### Importing Hosts from CSV

1. Click the "Import Hosts" button
2. Prepare a CSV file with the following columns (in order):
   - AWS Account Label
   - AWS Account ID
   - AWS Region
   - AWS Instance ID
   - AWS Instance IP Address
   - AWS Instance Name
3. Select the CSV file
4. Check "File has header row" if your CSV includes a header
5. Click "Import" to upload and process the file

### Viewing Metrics

The metrics section displays uptime statistics for each host:

- Uptime percentage
- Average latency
- Number of checks
- Number of failures
- Last downtime

You can select different time periods from the dropdown menu to view metrics for different timeframes.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
