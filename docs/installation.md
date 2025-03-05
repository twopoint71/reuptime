# Installation Guide

This guide will walk you through the process of installing and configuring ReUptime on your system.

## Prerequisites

- Python 3.7 or higher
- pip (Python package manager)
- Git (optional, for cloning the repository)

## Installation Steps

1. **Get the Code**

   Either clone the repository using Git:
   ```
   git clone https://github.com/yourusername/reuptime.git
   cd reuptime
   ```

   Or download and extract the ZIP file from the project's repository.

2. **Set Up a Virtual Environment**

   It's recommended to use a virtual environment to avoid conflicts with other Python packages:
   ```
   python -m venv .venv
   ```

   Activate the virtual environment:
   - On Linux/macOS:
     ```
     source .venv/bin/activate
     ```
   - On Windows:
     ```
     .venv\Scripts\activate
     ```

3. **Install Dependencies**

   Install all required packages:
   ```
   pip install -r requirements.txt
   ```

4. **Initialize the Database**

   Create the SQLite database and tables:
   ```
   flask --app app init-db
   ```

5. **Configure the Application**

   Create a `.env` file in the project root directory to configure environment variables:
   ```
   FLASK_APP=app
   FLASK_ENV=production  # Use 'development' for development mode
   SECRET_KEY=your_secure_random_key
   ```

   Generate a secure random key:
   ```
   python -c "import secrets; print(secrets.token_hex(16))"
   ```

6. **Create RRD Directory**

   Create a directory for RRD files:
   ```
   mkdir -p rrd
   ```

7. **Make Control Script Executable**

   ```
   chmod +x monitors/icmp/control.sh
   ```

## Running the Application

1. **Start the Web Application**

   For development:
   ```
   flask --app app run
   ```

   For production, use a WSGI server like Gunicorn:
   ```
   gunicorn 'app:app' --bind 0.0.0.0:8000
   ```

2. **Start the Monitoring Daemon**

   ```
   ./monitors/icmp/control.sh start
   ```

3. **Verify Installation**

   Access the web interface at http://localhost:5000 (or http://localhost:8000 if using Gunicorn)

## Troubleshooting

- **Database Issues**: If you encounter database errors, try removing the `instance/reuptime.sqlite` file and reinitializing the database.
- **Daemon Not Starting**: Check the daemon log with `./monitors/icmp/control.sh log` for error messages.
- **Permission Errors**: Ensure the application has write permissions to the `rrd` directory and the `instance` directory. 