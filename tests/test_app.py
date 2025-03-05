import pytest
import os
from io import BytesIO
from app import app, get_db, check_host, get_rrd_path, get_graph_path
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

def test_import_hosts_success(client, sample_csv):
    """Test successfully importing hosts from CSV."""
    response = client.post('/import', data={'csv_file': (BytesIO(sample_csv.encode()), 'test.csv')})
    assert response.status_code == 200
    assert b'Hosts imported successfully' in response.data
    
    # Verify host was added to database
    with get_db() as db:
        host = db.execute('SELECT * FROM hosts WHERE aws_instance_name = ?', ('Test Instance',)).fetchone()
        assert host is not None
        assert host['aws_account_label'] == 'Test Account'
        assert host['aws_account_id'] == '123456789012'

def test_get_metrics_nonexistent_host(client):
    """Test getting metrics for a nonexistent host."""
    response = client.get('/metrics/999')
    assert response.status_code == 404

def test_get_metrics_success(client, sample_host):
    """Test getting metrics for an existing host."""
    # Update RRD database with some test data
    rrd_file = get_rrd_path(sample_host['id'])
    rrdtool.update(rrd_file, f'N:100:50')  # 100% uptime, 50ms latency
    
    response = client.get(f'/metrics/{sample_host["id"]}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['host_id'] == sample_host['id']
    assert data['host_name'] == sample_host['aws_instance_name']
    assert 'metrics' in data

def test_get_graph_nonexistent_host(client):
    """Test getting graph for a nonexistent host."""
    response = client.get('/graph/999')
    assert response.status_code == 404

def test_get_graph_success(client, sample_host):
    """Test getting graph for an existing host."""
    # Update RRD database with some test data
    rrd_file = get_rrd_path(sample_host['id'])
    rrdtool.update(rrd_file, f'N:100:50')  # 100% uptime, 50ms latency
    
    response = client.get(f'/graph/{sample_host["id"]}')
    assert response.status_code == 200
    assert response.mimetype == 'image/png'

def test_add_host_missing_fields(client):
    """Test adding a host with missing fields."""
    response = client.post('/add_host', data={})
    assert response.status_code == 400
    assert b'aws_account_label is required' in response.data

def test_add_host_invalid_account_id(client):
    """Test adding a host with invalid AWS account ID."""
    response = client.post('/add_host', data={
        'aws_account_label': 'Test',
        'aws_account_id': '123',  # Invalid: not 12 digits
        'aws_region': 'us-east-1',
        'aws_instance_id': 'i-1234567890abcdef0',
        'aws_instance_ip': '10.0.0.1',
        'aws_instance_name': 'Test Server'
    })
    assert response.status_code == 400
    assert b'AWS Account ID must be 12 digits' in response.data

def test_add_host_success(client):
    """Test successfully adding a host."""
    response = client.post('/add_host', data={
        'aws_account_label': 'Test',
        'aws_account_id': '123456789012',
        'aws_region': 'us-east-1',
        'aws_instance_id': 'i-1234567890abcdef0',
        'aws_instance_ip': '10.0.0.1',
        'aws_instance_name': 'Test Server'
    })
    assert response.status_code == 200
    assert b'Host added successfully' in response.data
    
    # Verify host was added to database
    with get_db() as db:
        host = db.execute('SELECT * FROM hosts WHERE aws_instance_name = ?', ('Test Server',)).fetchone()
        assert host is not None
        assert host['aws_account_label'] == 'Test'
        assert host['aws_account_id'] == '123456789012'

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

def test_delete_host_success(client, sample_host):
    """Test successfully deleting a host."""
    response = client.post(f'/delete_host/{sample_host["id"]}')
    assert response.status_code == 200
    assert b'success' in response.data
    
    # Verify host was deleted from database
    with get_db() as db:
        host = db.execute('SELECT * FROM hosts WHERE id = ?', (sample_host['id'],)).fetchone()
        assert host is None

def test_undo_delete_not_found(client):
    """Test undoing deletion of a non-existent host."""
    response = client.post('/undo_delete/999')
    assert response.status_code == 404
    assert b'No host to restore' in response.data

def test_undo_delete_success(client, sample_host):
    """Test successfully undoing a host deletion."""
    # First delete the host
    delete_response = client.post(f'/delete_host/{sample_host["id"]}')
    assert delete_response.status_code == 200
    assert b'success' in delete_response.data
    
    # Get the deleted host ID from the deleted_hosts table
    with get_db() as db:
        deleted_host = db.execute('''
            SELECT id FROM deleted_hosts 
            WHERE aws_instance_name = ? 
            ORDER BY deleted_at DESC 
            LIMIT 1
        ''', (sample_host['aws_instance_name'],)).fetchone()
        assert deleted_host is not None
        deleted_host_id = deleted_host['id']
    
    # Then undo the deletion
    response = client.post(f'/undo_delete/{deleted_host_id}')
    assert response.status_code == 200
    assert b'success' in response.data
    
    # Verify host was restored to database with matching data
    with get_db() as db:
        # Find the restored host by matching the data
        restored_host = db.execute('''
            SELECT * FROM hosts 
            WHERE aws_account_label = ? 
            AND aws_account_id = ? 
            AND aws_region = ? 
            AND aws_instance_id = ? 
            AND aws_instance_ip = ? 
            AND aws_instance_name = ?
        ''', (
            sample_host['aws_account_label'],
            sample_host['aws_account_id'],
            sample_host['aws_region'],
            sample_host['aws_instance_id'],
            sample_host['aws_instance_ip'],
            sample_host['aws_instance_name']
        )).fetchone()
        
        assert restored_host is not None
        assert restored_host['aws_account_label'] == sample_host['aws_account_label']
        assert restored_host['aws_account_id'] == sample_host['aws_account_id']
        assert restored_host['aws_region'] == sample_host['aws_region']
        assert restored_host['aws_instance_id'] == sample_host['aws_instance_id']
        assert restored_host['aws_instance_ip'] == sample_host['aws_instance_ip']
        assert restored_host['aws_instance_name'] == sample_host['aws_instance_name']
        assert restored_host['is_active'] == sample_host['is_active']
        
        # Verify the host was removed from deleted_hosts
        deleted_host = db.execute('SELECT * FROM deleted_hosts WHERE id = ?', (deleted_host_id,)).fetchone()
        assert deleted_host is None

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

def test_check_host_success(client, sample_host, mocker):
    """Test successful host check."""
    # Mock the subprocess.run call
    mock_result = mocker.Mock()
    mock_result.returncode = 0
    mock_result.stdout = '64 bytes from 10.0.0.1: icmp_seq=1 ttl=64 time=1.234ms'
    mocker.patch('subprocess.run', return_value=mock_result)
    
    # Check the host
    success = check_host(sample_host)
    assert success is True
    
    # Verify host status was updated
    with get_db() as db:
        host = db.execute('SELECT * FROM hosts WHERE id = ?', (sample_host['id'],)).fetchone()
        assert host['is_active'] == 1
        assert host['last_check'] is not None

def test_check_host_failure(client, sample_host, mocker):
    """Test failed host check."""
    # Mock the subprocess.run call
    mock_result = mocker.Mock()
    mock_result.returncode = 1
    mock_result.stdout = ''
    mocker.patch('subprocess.run', return_value=mock_result)
    
    # Check the host
    
    success = check_host(sample_host)
    assert success is False
    
    # Verify host status was updated
    with get_db() as db:
        host = db.execute('SELECT * FROM hosts WHERE id = ?', (sample_host['id'],)).fetchone()
        assert host['is_active'] == 0
        assert host['last_check'] is not None 

def test_deleted_hosts_page(client):
    """Test that the deleted hosts page loads correctly."""
    response = client.get('/deleted_hosts')
    assert response.status_code == 200
    assert b'Deleted Hosts' in response.data

def test_api_deleted_hosts_empty(client):
    """Test the API endpoint for deleted hosts when there are none."""
    # Ensure there are no deleted hosts
    with get_db() as db:
        db.execute('DELETE FROM deleted_hosts')
        db.commit()
    
    response = client.get('/api/deleted_hosts')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_api_deleted_hosts_with_data(client, sample_host):
    """Test the API endpoint for deleted hosts when there are some."""
    # First delete a host to create a deleted host entry
    delete_response = client.post(f'/delete_host/{sample_host["id"]}')
    assert delete_response.status_code == 200
    
    # Now check the deleted hosts API
    response = client.get('/api/deleted_hosts')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Verify the deleted host data
    deleted_host = data[0]  # Most recent deletion should be first
    assert deleted_host['aws_instance_name'] == sample_host['aws_instance_name']
    assert deleted_host['aws_instance_ip'] == sample_host['aws_instance_ip']
    assert deleted_host['aws_region'] == sample_host['aws_region']
    assert 'deleted_at' in deleted_host
    assert deleted_host['deleted_at'] is not None

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

def test_api_restore_host_success(client, sample_host):
    """Test successfully restoring a host via the API."""
    # First delete a host to create a deleted host entry
    delete_response = client.post(f'/delete_host/{sample_host["id"]}')
    assert delete_response.status_code == 200
    
    # Get the deleted host ID
    with get_db() as db:
        deleted_host = db.execute('''
            SELECT id FROM deleted_hosts 
            WHERE aws_instance_name = ? 
            ORDER BY deleted_at DESC 
            LIMIT 1
        ''', (sample_host['aws_instance_name'],)).fetchone()
        assert deleted_host is not None
        deleted_host_id = deleted_host['id']
    
    # Now restore the host
    response = client.post('/api/restore_host', json={'host_id': deleted_host_id})
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert 'restored_host_id' in data
    
    # Verify the host was restored
    with get_db() as db:
        restored_host = db.execute('SELECT * FROM hosts WHERE aws_instance_name = ?', 
                                  (sample_host['aws_instance_name'],)).fetchone()
        assert restored_host is not None
        
        # Verify the host was removed from deleted_hosts
        deleted_host = db.execute('SELECT * FROM deleted_hosts WHERE id = ?', 
                                 (deleted_host_id,)).fetchone()
        assert deleted_host is None

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

def test_api_permanently_delete_host_success(client, sample_host):
    """Test successfully permanently deleting a host via the API."""
    # First delete a host to create a deleted host entry
    delete_response = client.post(f'/delete_host/{sample_host["id"]}')
    assert delete_response.status_code == 200
    
    # Get the deleted host ID
    with get_db() as db:
        deleted_host = db.execute('''
            SELECT id FROM deleted_hosts 
            WHERE aws_instance_name = ? 
            ORDER BY deleted_at DESC 
            LIMIT 1
        ''', (sample_host['aws_instance_name'],)).fetchone()
        assert deleted_host is not None
        deleted_host_id = deleted_host['id']
    
    # Now permanently delete the host
    response = client.post('/api/permanently_delete_host', json={'host_id': deleted_host_id})
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    
    # Verify the host was permanently deleted
    with get_db() as db:
        deleted_host = db.execute('SELECT * FROM deleted_hosts WHERE id = ?', 
                                 (deleted_host_id,)).fetchone()
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