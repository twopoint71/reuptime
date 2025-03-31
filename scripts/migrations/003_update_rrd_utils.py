import os
import sqlite3
from rrd_utils import get_rrd_path, init_rrd

def migrate(config):
    """Update RRD utilities to use UUIDs instead of host IDs."""
    db_path = config['DATABASE']

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

        # Update rrd_utils.py
        rrd_utils_path = os.path.join(os.path.dirname(db_path), '..', 'rrd_utils.py')

        if not os.path.exists(rrd_utils_path):
            print(f"RRD utils file not found: {rrd_utils_path}")
            return

        # Read the current content
        with open(rrd_utils_path, 'r') as f:
            content = f.read()

        # Find the start and end of the get_rrd_path function
        start_marker = 'def get_rrd_path(host_id, app_config=None):'
        end_marker = 'def init_rrd(host_id, app_config):'

        start_pos = content.find(start_marker)
        if start_pos == -1:
            print("Could not find get_rrd_path function")
            return

        end_pos = content.find(end_marker, start_pos)
        if end_pos == -1:
            print("Could not find end of get_rrd_path function")
            return

        # Update the get_rrd_path function
        new_get_rrd_path = '''def get_rrd_path(host_id, app_config=None):
    """Get the correct RRD file path based on testing configuration."""
    if "RRD_DIR" not in app_config:
        app_config = {'TESTING': False}
        rrd_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance/rrd')
    else:
        rrd_dir = app_config['RRD_DIR']

    # Ensure the directory exists
    os.makedirs(rrd_dir, exist_ok=True)

    # If host_id is an integer, it's a legacy ID - get the UUID
    if isinstance(host_id, int):
        try:
            with sqlite3.connect(app_config['DATABASE']) as db:
                cursor = db.execute("""
                    SELECT uuid FROM hosts WHERE id = ?
                    UNION
                    SELECT uuid FROM unmonitored_hosts WHERE id = ?
                """, (host_id, host_id))
                result = cursor.fetchone()
                if result:
                    host_id = result[0]
                else:
                    raise ValueError(f"No UUID found for host ID {host_id}")
        except Exception as e:
            print(f"Error getting UUID for host ID {host_id}: {str(e)}")
            raise

    return os.path.join(rrd_dir, f'host_{host_id}.rrd')'''

        # Replace the old function with the new one
        new_content = content[:start_pos] + new_get_rrd_path + content[end_pos:]

        # Write the updated content
        with open(rrd_utils_path, 'w') as f:
            f.write(new_content)

        print("Successfully updated RRD utilities to use UUIDs")

    except Exception as e:
        print(f"Migration failed: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    # This would be run directly for testing
    from db import get_default_db_path
    config = {'DATABASE': get_default_db_path()}
    migrate(config)