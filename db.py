import os
import sqlite3

def get_db(config):
    """Connect to the database and return a connection object."""
    db_path = config['DATABASE']
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return db

def init_db(config):
    """Initialize the database with required tables."""
    # Ensure the database directory exists and has the correct permissions
    db_path = config['DATABASE']
    db_dir = os.path.dirname(db_path)
    
    # If db_path doesn't have a directory component (e.g., 'uptime.db'), use current directory
    if not db_dir:
        db_dir = '.'
    
    # Create the directory if it doesn't exist
    if not os.path.exists(db_dir):
        print(f"Creating database directory: {db_dir}")
        os.makedirs(db_dir, exist_ok=True)
    
    # Set directory permissions
    try:
        print(f"Setting permissions for database directory: {db_dir}")
        os.chmod(db_dir, 0o755)
    except Exception as e:
        print(f"Warning: Could not set permissions for database directory: {str(e)}")
    
    # If the database file exists, ensure it has the correct permissions
    if os.path.exists(db_path):
        try:
            print(f"Setting permissions for database file: {db_path}")
            os.chmod(db_path, 0o644)
        except Exception as e:
            print(f"Warning: Could not set permissions for database file: {str(e)}")
    
    with get_db(config) as db:
        # Create hosts table
        db.execute('''
            CREATE TABLE IF NOT EXISTS hosts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aws_account_label TEXT,
                aws_account_id TEXT,
                aws_region TEXT,
                aws_instance_id TEXT,
                aws_instance_ip TEXT,
                aws_instance_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_check TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Create deleted_hosts table
        db.execute('''
            CREATE TABLE IF NOT EXISTS deleted_hosts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aws_account_label TEXT,
                aws_account_id TEXT,
                aws_region TEXT,
                aws_instance_id TEXT,
                aws_instance_ip TEXT,
                aws_instance_name TEXT,
                created_at TIMESTAMP,
                last_check TIMESTAMP,
                is_active INTEGER,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit() 