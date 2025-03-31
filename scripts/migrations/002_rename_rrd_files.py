import os
import sqlite3
import shutil
from pathlib import Path

def migrate(config):
    """Rename RRD files to use UUID instead of host ID."""
    db_path = config['DATABASE']
    rrd_dir = os.path.join(os.path.dirname(db_path), 'rrd')

    # Ensure RRD directory exists
    if not os.path.exists(rrd_dir):
        print("RRD directory not found, skipping migration")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all host ID to UUID mappings
        cursor.execute('''
            SELECT id, uuid FROM hosts
            UNION
            SELECT id, uuid FROM unmonitored_hosts
        ''')
        id_to_uuid = {row[0]: row[1] for row in cursor.fetchall()}

        # Get all existing RRD files
        rrd_files = [f for f in os.listdir(rrd_dir) if f.endswith('.rrd')]

        # Create a temporary directory for safe renaming
        temp_dir = os.path.join(rrd_dir, 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        # Rename files using UUID
        for rrd_file in rrd_files:
            try:
                # Extract host ID from filename (host_123.rrd -> 123)
                host_id = int(rrd_file.split('_')[1].split('.')[0])

                if host_id in id_to_uuid:
                    old_path = os.path.join(rrd_dir, rrd_file)
                    new_name = f"host_{id_to_uuid[host_id]}.rrd"
                    new_path = os.path.join(rrd_dir, new_name)

                    # Move to temp directory first
                    temp_path = os.path.join(temp_dir, new_name)
                    shutil.move(old_path, temp_path)

                    # Then move to final location
                    shutil.move(temp_path, new_path)
                    print(f"Renamed {rrd_file} to {new_name}")
                else:
                    print(f"Warning: No UUID found for host ID {host_id}")

            except Exception as e:
                print(f"Error processing {rrd_file}: {str(e)}")
                continue

        # Clean up temp directory
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

        print("Successfully renamed RRD files to use UUIDs")

    except Exception as e:
        print(f"Migration failed: {str(e)}")
        # Attempt to restore from temp directory if it exists
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                shutil.move(os.path.join(temp_dir, file), os.path.join(rrd_dir, file))
            os.rmdir(temp_dir)
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    # This would be run directly for testing
    from db import get_default_db_path
    config = {'DATABASE': get_default_db_path()}
    migrate(config)