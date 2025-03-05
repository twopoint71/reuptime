# Project Context

## Overview
This is a Flask web application called "ReUptime" for monitoring AWS instance uptime. The application uses SQLite for data storage and RRDtool for metrics collection. It provides a web-based interface for managing hosts, monitoring their uptime, and visualizing metrics using Chart.js.

## Architecture Decisions

### No Jinja Templates
- The application does NOT use Jinja templates for rendering HTML
- Instead, it serves static HTML files and uses client-side JavaScript to dynamically update the UI
- All HTML is stored in the static directory and served directly
- API endpoints return JSON data that is consumed by client-side JavaScript
- This approach provides a cleaner separation between frontend and backend

### ICMP Monitor Daemon
- A separate daemon process handles host monitoring via ICMP ping
- The daemon runs independently from the web application
- It checks all hosts every 5 seconds and updates the database and RRD files
- This approach offloads monitoring from the web application, improving responsiveness
- The daemon can be run as a systemd service or controlled via the admin interface
- The daemon includes database initialization to ensure it can run independently
- PID file and status file management for reliable daemon control and status reporting

### Admin Interface
- A dedicated admin page for system management
- Real-time monitoring of daemon status
- Controls for starting and stopping the daemon
- System information display
- Monitor log viewer
- Dark mode support
- Responsive design using Bootstrap 5

## Key Components

### Database
- Uses SQLite directly with the `sqlite3` module
- Database file: `uptime.db`
- Main tables:
  - `hosts` with columns:
    - `id` (INTEGER PRIMARY KEY)
    - `aws_account_label` (TEXT)
    - `aws_account_id` (TEXT)
    - `aws_region` (TEXT)
    - `aws_instance_id` (TEXT)
    - `aws_instance_ip` (TEXT)
    - `aws_instance_name` (TEXT)
    - `created_at` (TIMESTAMP)
    - `last_check` (TIMESTAMP)
    - `is_active` (BOOLEAN)
  - `deleted_hosts` with the same columns as `hosts` plus:
    - `deleted_at` (TIMESTAMP)

### RRD Metrics
- Uses RRDtool for time-series data storage
- Metrics collected:
  - Uptime percentage (0-100%)
  - Latency (in milliseconds)
- Data resolution: 5-second intervals
- Data retention periods:
  - Daily data: 288 points (5-minute intervals)
  - Weekly data: 168 points (1-hour intervals)
  - Monthly data: 720 points (30-minute intervals)
  - Yearly data: 365 points (1-day intervals)
- Metrics are visualized using Chart.js in the frontend
- The application supports different time ranges for metrics visualization (5 minutes to 1 year)
- Auto-refresh functionality for real-time metrics updates

### Frontend
- Uses Bootstrap 5 for responsive UI components
- Chart.js for interactive metrics visualization
- JavaScript for dynamic content loading and user interactions
- Supports both light and dark themes
- Modal dialogs for host details, metrics graphs, and management actions
- All HTML is static (no server-side templating)
- Client-side rendering of dynamic content
- Bootstrap Icons for UI elements
- Responsive design for mobile and desktop

### ICMP Monitor
- Python daemon that runs independently from the web application
- Connects to the SQLite database to retrieve host information
- Pings each host every 5 seconds using ICMP
- Updates host status in the database
- Records uptime and latency metrics in RRD database
- Logs all activity to a log file
- Can be run as a systemd service or controlled via the admin interface
- Handles errors gracefully and continues monitoring
- Comprehensive test suite for all functionality
- Command-line interface for start, stop, and status operations
- PID file management for reliable daemon control
- Status file with JSON data for real-time status reporting
- Database initialization to ensure it can run independently

### API Endpoints
- `/api/hosts` - Get all hosts
- `/api/deleted_hosts` - Get all deleted hosts
- `/api/metrics/<host_id>` - Get metrics for a specific host with optional time range parameter
- `/api/restore_host` - Restore a deleted host
- `/api/permanently_delete_host` - Permanently delete a host
- `/api/monitor_log` - Get the monitor log
- `/api/daemon/status` - Get the daemon status
- `/api/daemon/start` - Start the daemon
- `/api/daemon/stop` - Stop the daemon
- `/api/system_info` - Get system information

### Dependencies
- Flask: Web framework
- rrdtool: For metrics collection and visualization
- python-dotenv: For environment variable management
- Chart.js: For interactive metrics visualization
- Bootstrap 5: For UI components
- Bootstrap Icons: For UI icons

## Setup Instructions

1. Install system dependencies:
```bash
wsl -u bsmith bash -ic "sudo apt-get update && sudo apt-get install -y rrdtool libssl-dev libffi-dev python3-dev librrd-dev python3-rrdtool"
```

2. Create and activate virtual environment:
```bash
wsl -u bsmith bash -ic "cd /home/bsmith/reuptime && pyenv local 3.11.11 && python -m venv .venv && source .venv/bin/activate"
```

3. Install Python dependencies:
```bash
wsl -u bsmith bash -ic "cd /home/bsmith/reuptime && source .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
```

4. Initialize the database:
```bash
wsl -u bsmith bash -ic "cd /home/bsmith/reuptime && source .venv/bin/activate && python -c 'from app import init_db; init_db()'"
```

5. Generate example data (optional):
```bash
wsl -u bsmith bash -ic "cd /home/bsmith/reuptime && source .venv/bin/activate && python generate_example_hosts.py"
```

6. Run the application:
```bash
wsl -u bsmith bash -ic "cd /home/bsmith/reuptime && source .venv/bin/activate && python app.py"
```

7. Set up the ICMP monitor daemon (optional):
```bash
wsl -u bsmith bash -ic "cd /home/bsmith/reuptime && sudo bash fix_permissions_sudo.sh && python monitors/icmp/daemon.py --action start"
```

## Database Operations
The application uses direct SQLite operations through the `get_db()` function, which provides a connection with proper row factory configuration. All database operations are performed using parameterized SQL queries to prevent SQL injection.

Example database operations:
```python
# Query hosts
with get_db() as db:
    hosts = db.execute('SELECT * FROM hosts').fetchall()

# Insert a host
with get_db() as db:
    db.execute('''
        INSERT INTO hosts (aws_account_label, aws_account_id, ...)
        VALUES (?, ?, ...)
    ''', (label, account_id, ...))
    db.commit()

# Update a host
with get_db() as db:
    db.execute('''
        UPDATE hosts 
        SET last_check = CURRENT_TIMESTAMP, is_active = ?
        WHERE id = ?
    ''', (is_active, host_id))
    db.commit()

# Delete a host (soft delete - moves to deleted_hosts table)
with get_db() as db:
    # First get the host data
    host = db.execute('SELECT * FROM hosts WHERE id = ?', (host_id,)).fetchone()
    
    # Insert into deleted_hosts
    db.execute('''
        INSERT INTO deleted_hosts (
            aws_account_label, aws_account_id, aws_region,
            aws_instance_id, aws_instance_ip, aws_instance_name,
            created_at, last_check, is_active, deleted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (
        host['aws_account_label'], host['aws_account_id'], host['aws_region'],
        host['aws_instance_id'], host['aws_instance_ip'], host['aws_instance_name'],
        host['created_at'], host['last_check'], host['is_active']
    ))
    
    # Delete from hosts
    db.execute('DELETE FROM hosts WHERE id = ?', (host_id,))
    db.commit()
```

## RRD Operations
The application uses the `rrd_utils.py` module for RRD operations:

```python
# Initialize RRD database
init_rrd(host_id, app.config)

# Update RRD with new metrics
update_rrd(rrd_file, timestamp, uptime_value, latency_value)

# Fetch RRD data for visualization with optional time range
rrd_data = fetch_rrd_data(rrd_file, start_time=None, end_time=None)

# Format RRD data for Chart.js
chart_data = format_rrd_data_for_chart(rrd_data)
```

## Daemon Control
The application provides multiple ways to control the ICMP monitor daemon:

### Command Line
```bash
# Start the daemon
python monitors/icmp/daemon.py --action start

# Stop the daemon
python monitors/icmp/daemon.py --action stop

# Check daemon status
python monitors/icmp/daemon.py --action status
```

### Admin Interface
The admin interface at `/static/admin.html` provides a user-friendly way to:
- Start the daemon
- Stop the daemon
- Check daemon status
- View the monitor log
- View system information

### API Endpoints
```python
# Get daemon status
response = requests.get('/api/daemon/status')

# Start the daemon
response = requests.post('/api/daemon/start')

# Stop the daemon
response = requests.post('/api/daemon/stop')
```

## Testing
Run tests with:
```bash
wsl -u bsmith bash -ic "cd /home/bsmith/reuptime && source .venv/bin/activate && pytest -v"
```

The project uses pytest fixtures for test setup and teardown, including:
- Creating a test database
- Setting up test RRD files
- Mocking external dependencies like subprocess calls for ping
- Sample host data for testing host operations
- Sample CSV data for testing import functionality

### ICMP Monitor Tests
Run ICMP monitor tests with:
```bash
wsl -u bsmith bash -ic "cd /home/bsmith/reuptime && bash monitors/icmp/run_tests.sh"
```

The ICMP monitor tests include:
- Testing the daemon's ability to check host status
- Testing the daemon's ability to update the database
- Testing the daemon's ability to update RRD files
- Testing the daemon's error handling
- Testing the daemon's threading functionality
- Testing the daemon's signal handling
- Testing the daemon's main loop
- Testing the daemon's PID file management
- Testing the daemon's status file management
- Testing the daemon's command-line interface

### API Tests
The API tests include:
- Testing all API endpoints
- Testing error handling
- Testing response formats
- Testing authentication (if implemented)
- Testing the daemon control API endpoints

## Test Coverage Gaps

The following areas need additional test coverage:

1. **Daemon Control API Endpoints**:
   - `/api/daemon/status`
   - `/api/daemon/start`
   - `/api/daemon/stop`
   - `/api/system_info`

2. **Enhanced Daemon Functionality**:
   - `init_db()` function
   - `update_status()` function
   - `cleanup()` function
   - Command-line arguments handling

3. **Admin Interface**:
   - HTML structure
   - JavaScript functionality

## File Structure
```
reuptime/
├── app.py                 # Main application file
├── rrd_utils.py           # RRD utility functions
├── requirements.txt       # Python dependencies
├── generate_example_hosts.py  # Script to generate test data
├── uptime.db              # SQLite database file
├── .python-version        # pyenv Python version file
├── pytest.ini             # pytest configuration
├── conftest.py            # pytest fixtures
├── CONTEXT.md             # Project context and documentation
├── fix_permissions.sh     # Script to fix permissions
├── fix_permissions_sudo.sh # Script to fix permissions with sudo
├── rrd/                   # RRD database files
├── monitors/              # Monitoring daemons
│   └── icmp/              # ICMP ping monitor
│       ├── daemon.py      # ICMP monitor daemon
│       ├── daemon.pid     # PID file for the daemon
│       ├── daemon_status.json # Status file for the daemon
│       ├── icmp_monitor.log # Log file for the daemon
│       └── README.md      # Documentation for the ICMP monitor
├── static/                # Static files served directly (no templating)
│   ├── css/
│   │   └── style.css      # Custom CSS styles
│   ├── js/
│   │   ├── main.js        # Main JavaScript functionality
│   │   └── deleted_hosts.js # JavaScript for deleted hosts page
│   ├── index.html         # Main dashboard HTML
│   ├── deleted_hosts.html # Deleted hosts page HTML
│   ├── monitor_log.html   # Monitor log page HTML
│   ├── admin.html         # Admin interface HTML
└── tests/
    ├── conftest.py        # Test fixtures
    ├── test_app.py        # Application tests
    ├── test_charts.py     # Chart generation tests
    └── test_icmp_monitor.py # ICMP monitor tests
```

## Environment
- Operating System: Windows 10 (WSL Debian)
- Python Version: 3.11.11
- Database: SQLite 3
- Web Server: Flask Development Server (for production, use Gunicorn or uWSGI)
- Browser Support: Modern browsers (Chrome, Firefox, Safari, Edge)

## Future Improvements
- Add user authentication and authorization
- Add email notifications for down hosts
- Add more monitoring types (HTTP, TCP, etc.)
- Add more visualization options
- Add host grouping and tagging
- Add scheduled reports
- Add API documentation using Swagger/OpenAPI
- Add more comprehensive test coverage
- Add Docker support for easier deployment 