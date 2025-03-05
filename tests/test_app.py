import pytest
import os
from io import BytesIO
from app import app
from db import get_db
from utils import check_host
from rrd_utils import get_rrd_path
import rrdtool
from datetime import datetime

def test_index_page(client):
    """Test that the index page loads correctly."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Hosts' in response.data

def test_import_hosts_no_file(client):
    """Test importing hosts with no file."""
    response = client.post('/import')
    assert response.status_code == 400
    assert b'No file uploaded' in response.data

def test_import_hosts_empty_file(client):
    """Test importing hosts with an empty file."""
    response = client.post('/import', data={'csv_file': (BytesIO(b''), 'test.csv')})
    assert response.status_code == 400
    assert b'No file selected' in response.data

def test_import_hosts_invalid_file(client):
    """Test importing hosts with an invalid file type."""
    response = client.post('/import', data={'csv_file': (BytesIO(b'test'), 'test.txt')})
    assert response.status_code == 400
    assert b'File must be a CSV' in response.data

def test_import_hosts_success(client, sample_csv, app_with_db):
    """Test successfully importing hosts from CSV."""
    response = client.post('/import', data={'csv_file': (BytesIO(sample_csv.encode()), 'test.csv')})
    assert response.status_code == 302
    # Check that it redirects to the index page with the hosts_imported parameter
    assert b'/?hosts_imported=1' in response.data

    # Verify host was added to database
    with get_db(app_with_db.config) as db:
        host = db.execute('SELECT * FROM hosts WHERE aws_instance_name = ?', ('Test Instance',)).fetchone()
        assert host is not None
        assert host['aws_account_label'] == 'Test Account'
        assert host['aws_account_id'] == '123456789012'

def test_get_metrics_redirect(client):
    """Test that the /metrics endpoint redirects to /api/metrics."""
    response = client.get('/metrics/999', follow_redirects=False)
    assert response.status_code == 301
    assert response.location == '/api/metrics/999'

def test_get_metrics_redirect_with_query_params(client):
    """Test that the /metrics endpoint redirects to /api/metrics with query parameters."""
    response = client.get('/metrics/999?range=24h', follow_redirects=False)
    assert response.status_code == 301
    assert response.location == '/api/metrics/999?range=24h'

def test_get_metrics_nonexistent_host(client):
    """Test getting metrics for a nonexistent host."""
    response = client.get('/api/metrics/999')
    
    # The application creates a new RRD file for nonexistent hosts
    # and returns a 200 status code with empty data
    assert response.status_code == 200
    
    # Check that the response is JSON
    data = response.get_json()
    assert data is not None
    
    # Check that the response has the expected structure
    assert 'labels' in data
    assert 'datasets' in data
    
    # The datasets should be empty or contain default values
    for dataset in data['datasets']:
        assert 'data' in dataset
        # Either the data is empty or contains default values (all zeros or NaN)
        # We don't need to check the exact values

def test_get_metrics_success(client, sample_host, monkeypatch):
    """Test getting metrics for a host."""
    # Mock the format_rrd_data_for_chart function to return a valid response
    def mock_format_rrd_data(rrd_data):
        return {
            'labels': ['2023-01-01 00:00:00', '2023-01-01 00:05:00'],
            'datasets': [
                {
                    'label': 'Uptime',
                    'data': [1, 1],
                    'borderColor': 'rgba(75, 192, 192, 1)',
                    'fill': False
                },
                {
                    'label': 'Latency',
                    'data': [10, 15],
                    'borderColor': 'rgba(153, 102, 255, 1)',
                    'fill': False
                }
            ]
        }
    
    monkeypatch.setattr('routes.api_routes.format_rrd_data_for_chart', mock_format_rrd_data)
    
    # Send a request to get metrics for the host
    response = client.get(f'/api/metrics/{sample_host["id"]}')
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response is JSON
    data = response.get_json()
    assert data is not None
    
    # Check that the response has the expected structure
    assert 'labels' in data
    assert isinstance(data['labels'], list)
    
    assert 'datasets' in data
    assert len(data['datasets']) == 2
    
    # Check the structure of each dataset
    for dataset in data['datasets']:
        assert 'label' in dataset
        assert 'data' in dataset
        assert 'borderColor' in dataset
        assert 'fill' in dataset

def test_add_host_missing_fields(client):
    """Test adding a host with missing fields."""
    response = client.post('/add_host', data={})
    assert response.status_code == 400
    assert b'aws_account_label is required' in response.data

def test_add_host_invalid_account_id(client):
    """Test adding a host with an invalid AWS account ID."""
    response = client.post('/add_host', data={
        'aws_account_label': 'Test Account',
        'aws_account_id': '123',  # Invalid: not 12 digits
        'aws_region': 'us-east-1',
        'aws_instance_id': 'i-1234567890abcdef0',
        'aws_instance_ip': '192.168.1.1',
        'aws_instance_name': 'test-instance'
    })
    assert response.status_code == 400
    assert b'AWS Account ID must be 12 digits' in response.data

def test_add_host_success(client, app_with_db):
    """Test successfully adding a host."""
    response = client.post('/add_host', data={
        'aws_account_label': 'Test Account',
        'aws_account_id': '123456789012',
        'aws_region': 'us-east-1',
        'aws_instance_id': 'i-1234567890abcdef0',
        'aws_instance_ip': '192.168.1.1',
        'aws_instance_name': 'test-instance'
    })
    assert response.status_code == 302
    # Check that it redirects to the index page with the host_added parameter
    assert b'/?host_added=test-instance' in response.data

    # Verify host was added to database
    with get_db(app_with_db.config) as db:
        host = db.execute('SELECT * FROM hosts WHERE aws_instance_name = ?', ('test-instance',)).fetchone()
        assert host is not None
        assert host['aws_account_label'] == 'Test Account'
        assert host['aws_account_id'] == '123456789012'

    # Verify RRD file was created
    rrd_file = get_rrd_path(host['id'], app_with_db.config)
    assert os.path.exists(rrd_file)

def test_host_details_button_present(client, sample_host):
    """Test that the details button functionality is available."""
    # Check that the API endpoint returns the sample host
    api_response = client.get('/api/hosts')
    assert api_response.status_code == 200
    hosts_data = api_response.get_json()
    
    # Find the sample host in the API response
    sample_host_in_response = False
    for host in hosts_data:
        if host['id'] == sample_host['id']:
            sample_host_in_response = True
            break
    assert sample_host_in_response, "Sample host not found in API response"
    
    # Check that the index page has the necessary container for hosts table
    response = client.get('/')
    assert response.status_code == 200
    assert b'id="hostsTable"' in response.data
    assert b'id="modalsContainer"' in response.data

def test_host_details_modal_content(client, sample_host):
    """Test that the host details data is available via API."""
    # Check that the API endpoint returns the sample host with all required data
    api_response = client.get('/api/hosts')
    assert api_response.status_code == 200
    hosts_data = api_response.get_json()
    
    # Find the sample host in the API response and verify its data
    sample_host_found = False
    for host in hosts_data:
        if host['id'] == sample_host['id']:
            sample_host_found = True
            assert host['aws_account_label'] == sample_host['aws_account_label']
            assert host['aws_account_id'] == sample_host['aws_account_id']
            assert host['aws_region'] == sample_host['aws_region']
            assert host['aws_instance_id'] == sample_host['aws_instance_id']
            assert host['aws_instance_ip'] == sample_host['aws_instance_ip']
            assert host['aws_instance_name'] == sample_host['aws_instance_name']
            assert ('is_active' in host) == ('is_active' in sample_host)
            if 'is_active' in host and 'is_active' in sample_host:
                assert host['is_active'] == sample_host['is_active']
            break
    assert sample_host_found, "Sample host not found in API response"

def test_host_details_modal_structure(client, sample_host):
    """Test that the page has the necessary JavaScript for modals."""
    response = client.get('/')
    assert response.status_code == 200
    
    # Check for the modals container
    assert b'id="modalsContainer"' in response.data
    
    # Check that the main.js file is included
    assert b'src="/static/js/main.js"' in response.data or b'static/js/main.js' in response.data

def test_delete_host_not_found(client):
    """Test deleting a non-existent host."""
    response = client.post('/delete_host/999')
    assert response.status_code == 404
    assert b'Host not found' in response.data

def test_delete_host_success(client, sample_host, app_with_db):
    """Test successfully deleting a host."""
    response = client.post(f'/delete_host/{sample_host["id"]}')
    assert response.status_code == 200
    
    # Verify host was removed from hosts table
    with get_db(app_with_db.config) as db:
        host = db.execute('SELECT * FROM hosts WHERE id = ?', (sample_host["id"],)).fetchone()
        assert host is None
        
        # Verify host was added to deleted_hosts table
        deleted_host = db.execute('SELECT * FROM deleted_hosts WHERE aws_instance_name = ?', (sample_host["aws_instance_name"],)).fetchone()
        assert deleted_host is not None

def test_undo_delete_not_found(client):
    """Test undoing deletion of a non-existent host."""
    response = client.post('/undo_delete/999')
    assert response.status_code == 404
    assert b'No host to restore' in response.data

def test_undo_delete_success(client, sample_host, app_with_db):
    """Test successfully restoring a deleted host."""
    # First delete the host
    client.post(f'/delete_host/{sample_host["id"]}')
    
    # Get the ID of the deleted host
    with get_db(app_with_db.config) as db:
        deleted_host = db.execute('SELECT * FROM deleted_hosts WHERE aws_instance_name = ?', (sample_host["aws_instance_name"],)).fetchone()
        deleted_host_id = deleted_host['id']
    
    # Now restore the host
    response = client.post(f'/undo_delete/{deleted_host_id}')
    assert response.status_code == 200
    
    # Verify host was removed from deleted_hosts table
    with get_db(app_with_db.config) as db:
        deleted_host = db.execute('SELECT * FROM deleted_hosts WHERE id = ?', (deleted_host_id,)).fetchone()
        assert deleted_host is None
        
        # Verify host was added back to hosts table
        restored_host_id = response.get_json()['restored_host_id']
        host = db.execute('SELECT * FROM hosts WHERE id = ?', (restored_host_id,)).fetchone()
        assert host is not None
        assert host['aws_instance_name'] == sample_host['aws_instance_name']

def test_delete_button_present(client, sample_host):
    """Test that the delete functionality is available."""
    # Check that the API endpoint returns the sample host
    api_response = client.get('/api/hosts')
    assert api_response.status_code == 200
    
    # Check that the main.js file is included (which contains the deleteHost function)
    response = client.get('/')
    assert response.status_code == 200
    assert b'src="/static/js/main.js"' in response.data or b'static/js/main.js' in response.data
    
    # Check that the delete endpoint works
    delete_response = client.post(f'/delete_host/{sample_host["id"]}')
    assert delete_response.status_code == 200
    assert b'success' in delete_response.data

def test_undo_toast_present(client, sample_host):
    """Test that the undo toast notification is present."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'undoToast' in response.data
    assert b'Host Deleted' in response.data
    assert b'Undo' in response.data

def test_check_host_success(client, sample_host, mocker, app_with_db):
    """Test successfully checking a host's status."""
    # Mock the check_host function to return True (success)
    mocker.patch('utils.check_host', return_value=True)
    
    response = client.post(f'/check_host/{sample_host["id"]}')
    assert response.status_code == 200
    
    # Check that the response is JSON
    data = response.get_json()
    assert data is not None
    
    # Check that the response has the expected structure
    assert data['success'] is True
    assert data['is_active'] == 1
    
    # Verify host status was updated in the database
    with get_db(app_with_db.config) as db:
        host = db.execute('SELECT * FROM hosts WHERE id = ?', (sample_host["id"],)).fetchone()
        assert host['is_active'] == 1

def test_check_host_failure(client, sample_host, monkeypatch):
    """Test checking a host when the check fails."""
    # Mock the check_host function to return False (check failed)
    def mock_check_host(host, config=None):
        return False
    
    monkeypatch.setattr('routes.host_routes.check_host', mock_check_host)
    
    # Send a request to check the host
    response = client.post(f'/check_host/{sample_host["id"]}')
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response is JSON
    data = response.get_json()
    assert data is not None
    
    # Check that the response indicates success (API call succeeded)
    # but the host check itself failed (is_active = 0)
    assert data['success'] is True
    assert data['is_active'] == 0

def test_deleted_hosts_page(client):
    """Test that the deleted hosts page loads correctly."""
    response = client.get('/deleted_hosts')
    assert response.status_code == 200
    assert b'Deleted Hosts' in response.data

def test_api_deleted_hosts_empty(client, app_with_db):
    """Test getting deleted hosts when there are none."""
    response = client.get('/api/deleted_hosts')
    assert response.status_code == 200
    
    # Check that the response is JSON
    data = response.get_json()
    assert data is not None
    
    # Check that the response is an empty list
    assert isinstance(data, list)
    assert len(data) == 0

def test_api_deleted_hosts_with_data(client, sample_host, app_with_db):
    """Test getting deleted hosts when there are some."""
    # First delete a host to create a deleted host entry
    client.post(f'/delete_host/{sample_host["id"]}')
    
    response = client.get('/api/deleted_hosts')
    assert response.status_code == 200
    
    # Check that the response is JSON
    data = response.get_json()
    assert data is not None
    
    # Check that the response is a list with at least one item
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Check that the deleted host is in the response
    deleted_host = next((h for h in data if h['aws_instance_name'] == sample_host['aws_instance_name']), None)
    assert deleted_host is not None
    assert deleted_host['aws_account_label'] == sample_host['aws_account_label']
    assert deleted_host['aws_account_id'] == sample_host['aws_account_id']

def test_api_restore_host_missing_id(client):
    """Test restoring a host without providing an ID."""
    response = client.post('/api/restore_host', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert 'Host ID is required' in data['error']

def test_api_restore_host_nonexistent(client):
    """Test restoring a non-existent host."""
    response = client.post('/api/restore_host', json={'host_id': 999})
    assert response.status_code == 404
    data = response.get_json()
    assert data['success'] is False
    assert 'No host to restore' in data['error']

def test_api_restore_host_success(client, sample_host, app_with_db):
    """Test successfully restoring a host via the API."""
    # First delete the host
    client.post(f'/delete_host/{sample_host["id"]}')
    
    # Get the ID of the deleted host
    with get_db(app_with_db.config) as db:
        deleted_host = db.execute('SELECT * FROM deleted_hosts WHERE aws_instance_name = ?', (sample_host["aws_instance_name"],)).fetchone()
        deleted_host_id = deleted_host['id']
    
    # Now restore the host via the API
    response = client.post('/api/restore_host', json={'host_id': deleted_host_id})
    assert response.status_code == 200
    
    # Check that the response is JSON
    data = response.get_json()
    assert data is not None
    
    # Check that the response has the expected structure
    assert data['success'] is True
    assert 'restored_host_id' in data
    
    # Verify host was removed from deleted_hosts table
    with get_db(app_with_db.config) as db:
        deleted_host = db.execute('SELECT * FROM deleted_hosts WHERE id = ?', (deleted_host_id,)).fetchone()
        assert deleted_host is None
        
        # Verify host was added back to hosts table
        restored_host_id = data['restored_host_id']
        host = db.execute('SELECT * FROM hosts WHERE id = ?', (restored_host_id,)).fetchone()
        assert host is not None
        assert host['aws_instance_name'] == sample_host['aws_instance_name']

def test_api_permanently_delete_host_missing_id(client):
    """Test permanently deleting a host without providing an ID."""
    response = client.post('/api/permanently_delete_host', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert 'Host ID is required' in data['error']

def test_api_permanently_delete_host_nonexistent(client):
    """Test permanently deleting a non-existent host."""
    response = client.post('/api/permanently_delete_host', json={'host_id': 999})
    assert response.status_code == 404
    data = response.get_json()
    assert data['success'] is False
    assert 'Host not found' in data['error']

def test_api_permanently_delete_host_success(client, sample_host, app_with_db):
    """Test successfully permanently deleting a host via the API."""
    # First delete the host
    client.post(f'/delete_host/{sample_host["id"]}')
    
    # Get the ID of the deleted host
    with get_db(app_with_db.config) as db:
        deleted_host = db.execute('SELECT * FROM deleted_hosts WHERE aws_instance_name = ?', (sample_host["aws_instance_name"],)).fetchone()
        deleted_host_id = deleted_host['id']
    
    # Now permanently delete the host via the API
    response = client.post('/api/permanently_delete_host', json={'host_id': deleted_host_id})
    assert response.status_code == 200
    
    # Check that the response is JSON
    data = response.get_json()
    assert data is not None
    
    # Check that the response has the expected structure
    assert data['success'] is True
    
    # Verify host was removed from deleted_hosts table
    with get_db(app_with_db.config) as db:
        deleted_host = db.execute('SELECT * FROM deleted_hosts WHERE id = ?', (deleted_host_id,)).fetchone()
        assert deleted_host is None

def test_navigation_links(app_with_db):
    """Test that navigation links are present and working"""
    with app_with_db.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200
        assert b'Hosts' in response.data
        assert b'Deleted Hosts' in response.data

def test_navigation_brand_link(app_with_db):
    """Test that the brand link works correctly"""
    with app_with_db.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200
        assert b'ReUptime' in response.data 