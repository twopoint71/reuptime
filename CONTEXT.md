# Project Context

## Overview
This is a Flask web application called "ReUptime" for monitoring AWS instance uptime. The application uses SQLite for data storage and RRDtool for metrics collection and visualization. It provides a web-based interface for managing hosts, monitoring their uptime, and visualizing metrics.

## Architecture Decisions

### No Jinja Templates
- The application does NOT use Jinja templates for rendering HTML
- Instead, it serves static HTML files and uses client-side JavaScript to dynamically update the UI
- All HTML is stored in the static directory and served directly
- API endpoints return JSON data that is consumed by client-side JavaScript
- This approach provides a cleaner separation between frontend and backend

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
- Data resolution: 5-minute intervals
- Data retention periods:
  - Daily data: 288 points (5-minute intervals)
  - Weekly data: 168 points (1-hour intervals)
  - Monthly data: 720 points (30-minute intervals)
  - Yearly data: 365 points (1-day intervals)

### Frontend
- Uses Bootstrap 5 for responsive UI components
- Chart.js for interactive metrics visualization
- JavaScript for dynamic content loading and user interactions
- Supports both light and dark themes
- Modal dialogs for host details, metrics graphs, and management actions
- All HTML is static (no server-side templating)
- Client-side rendering of dynamic content

### Dependencies
- Flask: Web framework
- rrdtool: For metrics collection and visualization
- python-dotenv: For environment variable management
- Chart.js: For interactive metrics visualization
- Bootstrap 5: For UI components

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

# Fetch RRD data for visualization
rrd_data = fetch_rrd_data(rrd_file)

# Format RRD data for Chart.js
chart_data = format_rrd_data_for_chart(rrd_data)
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
├── rrd/                   # RRD database files
├── static/                # Static files served directly (no templating)
│   ├── css/
│   │   └── style.css      # Custom CSS styles
│   ├── js/
│   │   ├── main.js        # Main JavaScript functionality
│   │   └── deleted_hosts.js # JavaScript for deleted hosts page
│   ├── index.html         # Main dashboard HTML
│   ├── deleted_hosts.html # Deleted hosts page HTML
│   └── graphs/            # Generated graph images
└── tests/
    ├── conftest.py        # Test fixtures
    ├── test_app.py        # Application tests
    └── test_charts.py     # Chart generation tests
```

## Environment
- Operating System: Windows 10 (WSL Debian)
- Shell: WSL (not PowerShell)
- Python Version: 3.11.11 (via pyenv)
- Virtual Environment: `.venv`

## Important Notes
1. All terminal commands must be run in WSL using `wsl -u bsmith bash -ic "command"`
2. pyenv is available and should be used for Python version management
3. The project uses SQLite3 for database storage
4. RRDTool is required for metrics storage and graph generation
5. The application runs on Flask with debug mode enabled
6. Host status is checked using ICMP ping
7. The application supports both light and dark themes
8. No server-side templating is used - all HTML is static and served directly

## Key Dependencies
- Flask 3.0.2
- Flask-SQLAlchemy 3.1.1
- python-dotenv 1.0.1
- Werkzeug 3.0.1
- pytest 8.0.0
- pytest-cov 4.1.0
- pytest-mock 3.12.0
- rrdtool (system package)

## Features
1. **Host Management**: Add, edit, and delete AWS instances
2. **CSV Import**: Bulk import hosts from a CSV file
3. **Uptime Monitoring**: Check host availability using ICMP ping
4. **Metrics Collection**: Track uptime percentage and latency
5. **Visualization**: View metrics with both RRDtool static graphs and interactive Chart.js charts
6. **Host History**: View and restore deleted hosts
7. **Dark/Light Theme**: Toggle between dark and light UI themes
8. **Responsive Design**: Mobile-friendly interface using Bootstrap 5
9. **Soft Delete**: Hosts are moved to a deleted_hosts table rather than permanently deleted
10. **Undo Delete**: Ability to restore deleted hosts

## API Endpoints
- `/` - Main dashboard
- `/deleted_hosts` - View deleted hosts
- `/import` - CSV import endpoint (POST)
- `/metrics/<host_id>` - Get host metrics
- `/graph/<host_id>` - Get host uptime graph
- `/add_host` - Add a new host (POST)
- `/check_host/<host_id>` - Check a host's status (POST)
- `/delete_host/<host_id>` - Delete a host (POST)
- `/undo_delete/<host_id>` - Restore a deleted host (POST)
- `/host/<host_id>` - Host details page
- `/api/metrics/<host_id>` - JSON API for metrics data
- `/api/hosts` - JSON API for all hosts
- `/api/deleted_hosts` - JSON API for deleted hosts
- `/api/restore_host` - Restore a deleted host (POST)
- `/api/permanently_delete_host` - Permanently delete a host (POST)

## User Interface
The application provides a clean, responsive user interface with the following key elements:
1. Navigation bar with links to main dashboard and deleted hosts
2. Host management buttons (Add Host, Import Hosts)
3. Hosts table showing key information and status
4. Modal dialogs for host details, metrics graphs, and management actions
5. Toast notifications for actions like deletion with undo option
6. Interactive charts for visualizing uptime metrics
7. Responsive design that works on desktop and mobile devices 