import os
import sqlite3

def get_db(config):
    """Connect to the database and return a connection object."""
    db_path = config['DATABASE']
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return db

def reinit_db(config):
    """Reinitialize the database with required tables."""
    with get_db(config) as db:
        db.execute('DROP TABLE IF EXISTS hosts')
        db.execute('DROP TABLE IF EXISTS deleted_hosts')
        db.commit()
        init_db(config)
        print('Database dropped and recreated.')

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
                account_label TEXT,
                account_id TEXT,
                region TEXT,
                host_id TEXT,
                host_ip_address TEXT,
                host_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_check TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                downtime_allotment INTEGER DEFAULT 0,
                last_allotment_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create unmonitored_hosts table
        db.execute('''
            CREATE TABLE IF NOT EXISTS unmonitored_hosts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_label TEXT,
                account_id TEXT,
                region TEXT,
                host_id TEXT,
                host_ip_address TEXT,
                host_name TEXT,
                created_at TIMESTAMP,
                last_check TIMESTAMP,
                is_active INTEGER,
                unmonitored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create settings table
        db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value INTEGER,
                description TEXT
            )
        ''')
        
        # Insert default downtime allotment setting if it doesn't exist
        db.execute('''
            INSERT OR IGNORE INTO settings (key, value, description)
            VALUES (
                'default_downtime_allotment',
                0,
                'Default bi-weekly downtime allotment for hosts'
            )
        ''')
        
        db.commit() 

# Did not want to hardcode the database path, but the alternative is rather messy
def get_default_db_path():
    """Return the database path from environment variable or default location."""
    return os.environ.get('REUPTIME_DB_PATH', 
        os.path.abspath(os.path.join(os.path.dirname(__file__), 'instance/reuptime.sqlite'))) 