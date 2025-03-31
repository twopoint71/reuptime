import uuid
import sqlite3
import os
from datetime import datetime

def generate_uuid():
    return str(uuid.uuid4())

def migrate(config):
    """Add UUID column to hosts and unmonitored_hosts tables."""
    db_path = config['DATABASE']

    # Ensure database directory exists
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Add UUID column to hosts table
        cursor.execute('''
            ALTER TABLE hosts
            ADD COLUMN uuid TEXT
        ''')

        # Add UUID column to unmonitored_hosts table
        cursor.execute('''
            ALTER TABLE unmonitored_hosts
            ADD COLUMN uuid TEXT
        ''')

        # Generate and update UUIDs for existing hosts
        cursor.execute('SELECT id FROM hosts')
        hosts = cursor.fetchall()
        for host in hosts:
            new_uuid = generate_uuid()
            cursor.execute('''
                UPDATE hosts
                SET uuid = ?
                WHERE id = ?
            ''', (new_uuid, host[0]))

        # Generate and update UUIDs for existing unmonitored hosts
        cursor.execute('SELECT id FROM unmonitored_hosts')
        unmonitored = cursor.fetchall()
        for host in unmonitored:
            new_uuid = generate_uuid()
            cursor.execute('''
                UPDATE unmonitored_hosts
                SET uuid = ?
                WHERE id = ?
            ''', (new_uuid, host[0]))

        # Create unique indexes on UUID columns
        cursor.execute('''
            CREATE UNIQUE INDEX idx_hosts_uuid
            ON hosts(uuid)
        ''')

        cursor.execute('''
            CREATE UNIQUE INDEX idx_unmonitored_hosts_uuid
            ON unmonitored_hosts(uuid)
        ''')

        conn.commit()
        print("Successfully added UUID columns and populated with unique identifiers")

    except Exception as e:
        print(f"Migration failed: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    # This would be run directly for testing
    from db import get_default_db_path
    config = {'DATABASE': get_default_db_path()}
    migrate(config)