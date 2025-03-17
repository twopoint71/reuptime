from flask import request, jsonify, redirect, url_for
import os
import csv
from datetime import datetime
from db import get_db
from utils import setup_directories, check_host
from rrd_utils import init_rrd, get_rrd_path

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
            host_ids = []

            with get_db(app.config) as db:
                for row in csv_data:
                    cursor = db.execute('''
                        INSERT INTO hosts (
                            account_label, account_id, region,
                            host_id, host_ip_address, host_name,
                            created_at, last_check, is_active
                        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                    ''', (
                        row['Account Label'],
                        row['Account Id'],
                        row['Region'],
                        row['Host Id'],
                        row['Host IP Address'],
                        row['Hostname']
                    ))
                    host_id = cursor.lastrowid
                    host_ids.append(host_id)
                    imported_count += 1
                db.commit()

            # Initialize RRD database for each new host
            for host_id in host_ids:
                try:
                    print(f"Initializing RRD for imported host {host_id}")
                    init_rrd(host_id, app.config)
                    print(f"RRD initialization successful for imported host {host_id}")
                except Exception as e:
                    print(f"Error initializing RRD for imported host {host_id}: {str(e)}")
                    # Log the error but don't fail the request
                    with open(app.config['MONITOR_LOG_PATH'], 'a') as f:
                        f.write(f"[ERROR] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Failed to create RRD file for imported host ID {host_id}: {str(e)}\n")

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
                cursor = db.execute('''
                    INSERT INTO hosts (
                        account_label, account_id, region,
                        host_id, host_ip_address, host_name,
                        created_at, last_check, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                ''', (
                    request.form['account_label'],
                    request.form['account_id'],
                    request.form['region'],
                    request.form['host_id'],
                    request.form['host_ip_address'],
                    request.form['host_name']
                ))
                host_id = cursor.lastrowid
                db.commit()

            # Initialize RRD database for the new host
            try:
                print(f"Initializing RRD for host {host_id}")
                init_rrd(host_id, app.config)
                print(f"RRD initialization successful for host {host_id}")
            except Exception as e:
                print(f"Error initializing RRD for host {host_id}: {str(e)}")
                # Log the error but don't fail the request
                with open(app.config['MONITOR_LOG_PATH'], 'a') as f:
                    f.write(f"[ERROR] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Failed to create RRD file for host ID {host_id}: {str(e)}\n")

            # Redirect to the main page with a success parameter
            return redirect(url_for('host_list', host_added=request.form['host_name']))

        except Exception as e:
            print(f"Error adding host: {str(e)}")  # Add logging for debugging
            return jsonify({'error': str(e)}), 500

    @app.route('/check_host/<int:host_id>', methods=['POST'])
    def check_host_route(host_id):
        """Route to check a specific host's status."""
        with get_db(app.config) as db:
            host = db.execute('SELECT * FROM hosts WHERE id = ?', (host_id,)).fetchone()
            if not host:
                return jsonify({'success': False, 'error': 'Host not found'}), 404

        success = check_host(host, app.config)
        return jsonify({
            'success': True,
            'is_active': 1 if success else 0
        })

    @app.route('/unmonitor_host/<int:host_id>', methods=['POST'])
    def unmonitor_host(host_id):
        """Unmonitor a host and its associated RRD database."""
        with get_db(app.config) as db:
            # Get the host to unmonitor
            host = db.execute('SELECT * FROM hosts WHERE id = ?', (host_id,)).fetchone()
            if not host:
                return jsonify({'success': False, 'error': 'Host not found'}), 404

            # Store host data in unmonitored_hosts table
            db.execute('''
                INSERT INTO unmonitored_hosts (
                    account_label, account_id, region,
                    host_id, host_ip_address, host_name,
                    created_at, last_check, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                host['account_label'],
                host['account_id'],
                host['region'],
                host['host_id'],
                host['host_ip_address'],
                host['host_name'],
                host['created_at'],
                host['last_check'],
                host['is_active']
            ))

            # Delete RRD database if it exists
            rrd_file = get_rrd_path(host_id, app.config)
            if os.path.exists(rrd_file):
                os.remove(rrd_file)

            db.execute('DELETE FROM hosts WHERE id = ?', (host_id,))
            db.commit()

            # Return the unmonitored host data in the response
            host_dict = dict(host)
            # Convert datetime objects to strings
            for key in ['created_at', 'last_check']:
                if host_dict[key] and not isinstance(host_dict[key], str):
                    host_dict[key] = host_dict[key].strftime('%Y-%m-%d %H:%M:%S')

            return jsonify({
                'success': True,
                'unmonitored_host_data': host_dict
            })

    @app.route('/restore_host/<int:host_id>', methods=['POST'])
    def restore_host(host_id):
        """Restore the last unmonitored host."""
        with get_db(app.config) as db:
            # Get the unmonitored host
            unmonitored_host = db.execute('SELECT * FROM unmonitored_hosts WHERE id = ?', (host_id,)).fetchone()

            if not unmonitored_host:
                return jsonify({'success': False, 'error': 'No host to restore'}), 404

            try:
                # Insert the host back into the hosts table
                cursor = db.execute('''
                    INSERT INTO hosts (
                        account_label, account_id, region,
                        host_id, host_ip_address, host_name,
                        created_at, last_check, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    unmonitored_host['account_label'],
                    unmonitored_host['account_id'],
                    unmonitored_host['region'],
                    unmonitored_host['host_id'],
                    unmonitored_host['host_ip_address'],
                    unmonitored_host['host_name'],
                    unmonitored_host['created_at'],
                    unmonitored_host['last_check'],
                    unmonitored_host['is_active']
                ))
                restored_id = cursor.lastrowid

                # Initialize RRD database for the restored host
                init_rrd(restored_id, app.config)

                # Remove the host from unmonitored_hosts
                db.execute('DELETE FROM unmonitored_hosts WHERE id = ?', (host_id,))
                db.commit()

                # Return the restored host ID
                return jsonify({
                    'success': True,
                    'restored_host_id': restored_id
                })
            except Exception as e:
                db.rollback()  # Rollback any changes if an error occurs
                print(f"Error restoring host: {str(e)}")  # Add logging for debugging
                return jsonify({
                    'success': False,
                    'error': f"Failed to restore host: {str(e)}"
                }), 500