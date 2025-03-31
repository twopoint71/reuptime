import os
import sqlite3
from datetime import datetime

def get_migrations_table(cursor):
    """Create migrations table if it doesn't exist."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

def get_applied_migrations(cursor):
    """Get list of applied migrations."""
    cursor.execute('SELECT name FROM migrations')
    return {row[0] for row in cursor.fetchall()}

def run_migrations(config):
    """Run all pending migrations."""
    db_path = config['DATABASE']

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Ensure migrations table exists
        get_migrations_table(cursor)

        # Get list of applied migrations
        applied = get_applied_migrations(cursor)

        # Get all migration files
        migration_dir = os.path.dirname(__file__)
        migration_files = sorted([
            f for f in os.listdir(migration_dir)
            if f.endswith('.py') and f != '__init__.py'
        ])

        # Run each pending migration
        for migration_file in migration_files:
            if migration_file not in applied:
                print(f"Running migration: {migration_file}")

                # Import and run migration
                module_name = f"scripts.migrations.{os.path.splitext(migration_file)[0]}"
                module = __import__(module_name, fromlist=['migrate'])

                # Run the migration
                module.migrate(config)

                # Record successful migration
                cursor.execute(
                    'INSERT INTO migrations (name) VALUES (?)',
                    (migration_file,)
                )
                conn.commit()

                print(f"Successfully applied migration: {migration_file}")

        print("All migrations completed successfully")

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
    run_migrations(config)