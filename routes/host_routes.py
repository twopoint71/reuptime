from flask import request, jsonify, redirect, url_for
import os
import csv
from datetime import datetime
from db import get_db
from utils import setup_directories, check_host
from rrd_utils import init_rrd, get_rrd_path
from uuid import uuid4

def register_host_routes(app):
    """Register routes for host management."""

    @app.route('/import', methods=['POST'])
    def import_hosts():
        """Import hosts from a CSV file."""
        if 'csv_file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['csv_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400

        try:
            stream = file.stream.read().decode("UTF8")
            if not stream.strip():
                return jsonify({'error': 'No file selected'}), 400

            csv_data = csv.DictReader(stream.splitlines())

            # Check if the CSV has any rows
            if not any(csv_data):
                return jsonify({'error': 'No file selected'}), 400

            # Reset the file pointer and create a new reader
            file.seek(0)
            stream = file.stream.read().decode("UTF8")
            csv_data = csv.DictReader(stream.splitlines())

            # Ensure directories exist
            setup_directories(app.config)

            imported_count = 0
            host_uuids = []

            with get_db(app.config) as db:
                for row in csv_data:
                    # Generate UUID once and reuse it
                    new_uuid = str(uuid4())
                    cursor = db.execute('''
                        INSERT INTO hosts (
                            uuid, account_label, account_id, region,
                            host_id, host_ip_address, host_name,
                            created_at, last_check, is_active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                    ''', (
                        new_uuid,
                        row['Account Label'],
                        row['Account Id'],
                        row['Region'],
                        row['Host Id'],
                        row['Host IP Address'],
                        row['Hostname']
                    ))
                    host_uuids.append(new_uuid)  # Store the UUID instead of lastrowid
                    imported_count += 1
                db.commit()

            # Initialize RRD database for each new host
            for host_uuid in host_uuids:
                try:
                    print(f"Initializing RRD for imported host {host_uuid}")
                    init_rrd(host_uuid, app.config)
                    print(f"RRD initialization successful for imported host {host_uuid}")
                except Exception as e:
                    print(f"Error initializing RRD for imported host {host_uuid}: {str(e)}")
                    # Log the error but don't fail the request
                    with open(app.config['MONITOR_LOG_PATH'], 'a') as f:
                        f.write(f"[ERROR] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Failed to create RRD file for imported host ID {host_uuid}: {str(e)}\n")

            # Redirect to the main page with a success parameter
            return redirect(url_for('monitored_hosts', hosts_imported=imported_count))

        except Exception as e:
            print(f"Error importing hosts: {str(e)}")  # Add logging for debugging
            return jsonify({'error': str(e)}), 500

    @app.route('/add_host', methods=['POST'])
    def add_host():
        """Add a new host."""
        try:
            # Validate required fields
            required_fields = [
                'account_label', 'account_id', 'region',
                'host_id', 'host_ip_address', 'host_name'
            ]

            for field in required_fields:
                if not request.form.get(field):
                    return jsonify({'error': f'{field} is required'}), 400

            # Ensure directories exist
            setup_directories(app.config)

            with get_db(app.config) as db:
                # Generate UUID once and reuse it
                new_uuid = str(uuid4())
                cursor = db.execute('''
                    INSERT INTO hosts (
                        uuid, account_label, account_id, region,
                        host_id, host_ip_address, host_name,
                        created_at, last_check, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                ''', (
                    new_uuid,
                    request.form['account_label'],
                    request.form['account_id'],
                    request.form['region'],
                    request.form['host_id'],
                    request.form['host_ip_address'],
                    request.form['host_name']
                ))
                db.commit()

            # Use the UUID we generated for RRD
            try:
                print(f"Initializing RRD for host {new_uuid}")
                init_rrd(new_uuid, app.config)
                print(f"RRD initialization successful for host {new_uuid}")
            except Exception as e:
                print(f"Error initializing RRD for host {new_uuid}: {str(e)}")
                # Log the error but don't fail the request
                with open(app.config['MONITOR_LOG_PATH'], 'a') as f:
                    f.write(f"[ERROR] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Failed to create RRD file for host ID {new_uuid}: {str(e)}\n")

            # Redirect to the main page with a success parameter
            return redirect(url_for('monitored_hosts', host_added=request.form['host_name']))

        except Exception as e:
            print(f"Error adding host: {str(e)}")  # Add logging for debugging
            return jsonify({'error': str(e)}), 500

    @app.route('/check_host/<uuid:host_uuid>', methods=['POST'])
    def check_host_route(host_uuid):
        """Route to check a specific host's status."""
        try:
            with get_db(app.config) as db:
                # Get the host details
                host = db.execute('''
                    SELECT account_label, account_id, region,
                           host_id, host_ip_address, host_name,
                           created_at, last_check, is_active
                    FROM hosts
                    WHERE uuid = ?
                ''', (host_uuid,)).fetchone()

                if not host:
                    return jsonify({'success': False, 'error': 'Host not found'}), 404

                # Check the host's status
                is_active = check_host(host, app.config)

                # Update the host's status in the database
                db.execute('''
                    UPDATE hosts
                    SET is_active = ?,
                        last_check = datetime('now')
                    WHERE uuid = ?
                ''', (1 if is_active else 0, host_uuid))
                db.commit()

                return jsonify({
                    'success': True,
                    'is_active': 1 if is_active else 0
                })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/unmonitor_host/<uuid:host_uuid>', methods=['POST'])
    def unmonitor_host(host_uuid):
        """Route to unmonitor a host."""
        try:
            # Convert UUID to string
            host_uuid_str = str(host_uuid)

            with get_db(app.config) as db:
                # Get the host details before removing it
                host = db.execute('''
                    SELECT id, account_label, account_id, region,
                           host_id, host_ip_address, host_name,
                           created_at, last_check, is_active
                    FROM hosts
                    WHERE uuid = ?
                ''', (host_uuid_str,)).fetchone()

                if not host:
                    return jsonify({'success': False, 'error': 'Host not found'}), 404

                # Insert into unmonitored_hosts table
                db.execute('''
                    INSERT INTO unmonitored_hosts (
                        uuid, account_label, account_id, region,
                        host_id, host_ip_address, host_name,
                        created_at, last_check, is_active, unmonitored_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (
                    host_uuid_str, host['account_label'], host['account_id'],
                    host['region'], host['host_id'], host['host_ip_address'],
                    host['host_name'], host['created_at'], host['last_check'],
                    host['is_active']
                ))

                # Delete from hosts table
                db.execute('DELETE FROM hosts WHERE uuid = ?', (host_uuid_str,))
                db.commit()

                return jsonify({
                    'success': True,
                    'unmonitored_host_data': {
                        'uuid': host_uuid_str,
                        'host_id': host['host_id'],
                        'host_name': host['host_name']
                    }
                })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/restore_host/<uuid:host_uuid>', methods=['POST'])
    def restore_host(host_uuid):
        """Route to restore a host to monitored state."""
        try:
            # Convert UUID to string
            host_uuid_str = str(host_uuid)

            with get_db(app.config) as db:
                # Get the unmonitored host details
                unmonitored_host = db.execute('''
                    SELECT account_label, account_id, region,
                           host_id, host_ip_address, host_name,
                           created_at, last_check, is_active
                    FROM unmonitored_hosts
                    WHERE uuid = ?
                ''', (host_uuid_str,)).fetchone()

                if not unmonitored_host:
                    return jsonify({'success': False, 'error': 'No host to restore'}), 404

                # Insert back into hosts table
                db.execute('''
                    INSERT INTO hosts (
                        uuid, account_label, account_id, region,
                        host_id, host_ip_address, host_name,
                        created_at, last_check, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    host_uuid_str, unmonitored_host['account_label'],
                    unmonitored_host['account_id'], unmonitored_host['region'],
                    unmonitored_host['host_id'], unmonitored_host['host_ip_address'],
                    unmonitored_host['host_name'], unmonitored_host['created_at'],
                    unmonitored_host['last_check'], unmonitored_host['is_active']
                ))

                # Delete from unmonitored_hosts table
                db.execute('DELETE FROM unmonitored_hosts WHERE uuid = ?', (host_uuid_str,))
                db.commit()

                return jsonify({
                    'success': True,
                    'restored_host_uuid': host_uuid_str
                })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500