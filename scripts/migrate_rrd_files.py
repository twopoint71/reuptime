import sqlite3
import os
from pathlib import Path

def migrate_rrd_files():
    # Configuration - you'll need to set these paths
    DB_PATH = ''
    RRD_DIR = ''

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all hosts with their IDs and UUIDs
    cursor.execute('SELECT id, uuid FROM hosts')
    hosts = cursor.fetchall()

    # Track statistics
    moved = 0
    missing = 0
    already_correct = 0

    for host in hosts:
        old_file = Path(RRD_DIR) / f'host_{host["id"]}.rrd'
        new_file = Path(RRD_DIR) / f'host_{host["uuid"]}.rrd'

        print(f'Checking host ID {host["id"]} (UUID: {host["uuid"]})')

        if new_file.exists():
            print(f'  ✓ Already using new naming convention: {new_file}')
            already_correct += 1
            continue

        if old_file.exists():
            try:
                old_file.rename(new_file)
                print(f'  → Moved {old_file} to {new_file}')
                moved += 1
            except Exception as e:
                print(f'  ! Error moving file: {e}')
        else:
            print(f'  ! Missing RRD file for host')
            missing += 1

    # Print summary
    print("\nMigration Summary:")
    print(f"Total hosts checked: {len(hosts)}")
    print(f"Already using new convention: {already_correct}")
    print(f"Files moved: {moved}")
    print(f"Missing files: {missing}")

    conn.close()

if __name__ == '__main__':
    migrate_rrd_files()