// Function to create or update a chart
function createOrUpdateChart(canvasId, hostId) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    let chart = Chart.getChart(canvasId);
    
    if (chart) {
        chart.destroy();
    }
    
    // Fetch data from API
    fetch(`/api/metrics/${hostId}`)
        .then(response => response.json())
        .then(data => {
            chart = new Chart(ctx, {
                type: 'line',
                data: data,
                options: {
                    responsive: true,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Value'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Time'
                            }
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: 'Host Metrics'
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error fetching metrics:', error);
        });
}

// Function to refresh chart data periodically
function startChartRefresh(canvasId, hostId, interval = 300000) { // 5 minutes default
    createOrUpdateChart(canvasId, hostId);
    setInterval(() => createOrUpdateChart(canvasId, hostId), interval);
}

// Function to set up graph modals for all hosts
function setupGraphModals() {
    // Get all graph buttons
    const graphButtons = document.querySelectorAll('.graph-btn');
    
    // Add click event listeners to each button
    graphButtons.forEach(button => {
        const hostId = button.getAttribute('data-host-id');
        const chartId = `metricsChart${hostId}`;
        
        button.addEventListener('click', function() {
            // Wait for the modal to be shown before creating the chart
            setTimeout(() => {
                createOrUpdateChart(chartId, hostId);
            }, 100);
        });
    });
}

// Function to initialize the page with hosts data
function initializeHostsTable() {
    fetch('/api/hosts')
        .then(response => response.json())
        .then(hosts => {
            const tableBody = document.querySelector('#hostsTable tbody');
            if (!tableBody) return;
            
            // Clear existing table rows
            tableBody.innerHTML = '';
            
            // Create modals container if it doesn't exist
            let modalsContainer = document.getElementById('modalsContainer');
            if (!modalsContainer) {
                modalsContainer = document.createElement('div');
                modalsContainer.id = 'modalsContainer';
                document.body.appendChild(modalsContainer);
            } else {
                modalsContainer.innerHTML = '';
            }
            
            // Add each host to the table
            hosts.forEach(host => {
                // Create table row
                const row = document.createElement('tr');
                
                // Add host data to row
                row.innerHTML = `
                    <td>${host.aws_instance_name}</td>
                    <td>${host.aws_instance_ip}</td>
                    <td>${host.aws_region}</td>
                    <td>
                        <span class="badge ${host.is_active ? 'bg-success' : 'bg-danger'}">
                            ${host.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </td>
                    <td>${host.last_check || 'Never'}</td>
                    <td>
                        <button type="button" class="btn btn-sm btn-secondary" data-bs-toggle="modal" data-bs-target="#hostDetails${host.id}">
                            Details
                        </button>
                        <a href="/metrics/${host.id}" class="btn btn-sm btn-info">Metrics</a>
                        <button type="button" class="btn btn-sm btn-primary graph-btn" data-bs-toggle="modal" data-bs-target="#graphModal${host.id}" data-host-id="${host.id}">
                            Graph
                        </button>
                    </td>
                `;
                
                tableBody.appendChild(row);
                
                // Create details modal
                const detailsModal = document.createElement('div');
                detailsModal.className = 'modal fade';
                detailsModal.id = `hostDetails${host.id}`;
                detailsModal.setAttribute('tabindex', '-1');
                detailsModal.setAttribute('aria-labelledby', `hostDetailsLabel${host.id}`);
                detailsModal.setAttribute('aria-hidden', 'true');
                
                detailsModal.innerHTML = `
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="hostDetailsLabel${host.id}">Host Details: ${host.aws_instance_name}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <dl class="row">
                                    <dt class="col-sm-4">Account Label</dt>
                                    <dd class="col-sm-8">${host.aws_account_label}</dd>
                                    
                                    <dt class="col-sm-4">Account ID</dt>
                                    <dd class="col-sm-8">${host.aws_account_id}</dd>
                                    
                                    <dt class="col-sm-4">Region</dt>
                                    <dd class="col-sm-8">${host.aws_region}</dd>
                                    
                                    <dt class="col-sm-4">Instance ID</dt>
                                    <dd class="col-sm-8">${host.aws_instance_id}</dd>
                                    
                                    <dt class="col-sm-4">Instance IP</dt>
                                    <dd class="col-sm-8">${host.aws_instance_ip}</dd>
                                    
                                    <dt class="col-sm-4">Instance Name</dt>
                                    <dd class="col-sm-8">${host.aws_instance_name}</dd>
                                    
                                    <dt class="col-sm-4">Status</dt>
                                    <dd class="col-sm-8">
                                        <span class="badge ${host.is_active ? 'bg-success' : 'bg-danger'}">
                                            ${host.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </dd>
                                    
                                    <dt class="col-sm-4">Last Check</dt>
                                    <dd class="col-sm-8">${host.last_check || 'Never'}</dd>
                                    
                                    <dt class="col-sm-4">Created At</dt>
                                    <dd class="col-sm-8">${host.created_at}</dd>
                                </dl>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-danger" onclick="deleteHost(${host.id}, '${host.aws_instance_name}')">Delete Host</button>
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                `;
                
                modalsContainer.appendChild(detailsModal);
                
                // Create graph modal
                const graphModal = document.createElement('div');
                graphModal.className = 'modal fade';
                graphModal.id = `graphModal${host.id}`;
                graphModal.setAttribute('tabindex', '-1');
                graphModal.setAttribute('aria-labelledby', `graphModalLabel${host.id}`);
                graphModal.setAttribute('aria-hidden', 'true');
                
                graphModal.innerHTML = `
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="graphModalLabel${host.id}">Metrics Graph: ${host.aws_instance_name}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <canvas id="metricsChart${host.id}"></canvas>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                `;
                
                modalsContainer.appendChild(graphModal);
            });
            
            // Set up event listeners for the graph buttons
            setupGraphModals();
        })
        .catch(error => {
            console.error('Error fetching hosts:', error);
        });
}

// Function to delete a host
function deleteHost(hostId, hostName) {
    fetch(`/delete_host/${hostId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Store the deleted host ID for potential undo
            // window.lastDeletedHostId = hostId;
            
            // Get the ID of the entry in the deleted_hosts table
            fetch('/api/deleted_hosts')
                .then(response => response.json())
                .then(deletedHosts => {
                    // Find the most recently deleted host that matches our original host ID
                    // We're looking for the host that was just deleted
                    const recentlyDeletedHost = deletedHosts.find(host => 
                        host.aws_instance_id === data.deleted_host_data.aws_instance_id &&
                        host.aws_instance_name === data.deleted_host_data.aws_instance_name
                    );
                    
                    if (recentlyDeletedHost) {
                        window.lastDeletedHostId = recentlyDeletedHost.id;
                        
                        // Update the toast message with the host name
                        document.getElementById('deletedHostName').textContent = hostName || 'Host';
                        
                        // Show the undo toast
                        const undoToast = new bootstrap.Toast(document.getElementById('undoToast'));
                        undoToast.show();
                    }
                })
                .catch(error => {
                    console.error('Error fetching deleted hosts:', error);
                });
            
            // Close any open modals
            const openModals = document.querySelectorAll('.modal.show');
            openModals.forEach(modal => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            });
            
            // Refresh the hosts table
            initializeHostsTable();
        } else {
            alert('Failed to delete host: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to delete host');
    });
}

// Function to undo a host deletion
function undoDelete() {
    if (window.lastDeletedHostId) {
        fetch(`/undo_delete/${window.lastDeletedHostId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                console.log('Successfully restored host with ID:', data.restored_host_id);
                
                // Hide the toast
                const undoToast = bootstrap.Toast.getInstance(document.getElementById('undoToast'));
                if (undoToast) {
                    undoToast.hide();
                }
                
                // Refresh the hosts table
                initializeHostsTable();
            } else {
                console.error('Failed to undo deletion:', data.error);
                alert('Failed to undo deletion: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to undo deletion: ' + error.message);
        });
    } else {
        console.error('No deleted host ID found');
        alert('Cannot undo: No recently deleted host found');
    }
}

// Function to toggle dark mode
function toggleDarkMode() {
    const body = document.body;
    const html = document.documentElement;
    const icon = document.querySelector('#darkModeToggle i');
    const text = document.querySelector('#darkModeToggle span');
    const navbar = document.querySelector('.navbar');
    const darkModeToggle = document.getElementById('darkModeToggle');
    
    // Toggle dark mode class on body
    body.classList.toggle('dark-mode');
    
    // Update icon and localStorage
    if (body.classList.contains('dark-mode')) {
        // Switching to dark mode
        icon.classList.remove('fa-moon');
        icon.classList.add('fa-sun');
        if (text) text.textContent = 'Toggle Light Mode';
        localStorage.setItem('darkMode', 'enabled');
        
        // Update navbar classes for dark mode
        if (navbar) {
            navbar.classList.remove('navbar-light', 'bg-light');
            navbar.classList.add('navbar-dark', 'bg-dark');
        }
        
        // Update dark mode toggle button
        if (darkModeToggle) {
            darkModeToggle.classList.remove('btn-outline-secondary');
            darkModeToggle.classList.add('btn-outline-light');
        }
    } else {
        // Switching to light mode
        icon.classList.remove('fa-sun');
        icon.classList.add('fa-moon');
        if (text) text.textContent = 'Toggle Dark Mode';
        localStorage.setItem('darkMode', 'disabled');
        
        // Update navbar classes for light mode
        if (navbar) {
            navbar.classList.remove('navbar-dark', 'bg-dark');
            navbar.classList.add('navbar-light', 'bg-light');
        }
        
        // Update dark mode toggle button
        if (darkModeToggle) {
            darkModeToggle.classList.remove('btn-outline-light');
            darkModeToggle.classList.add('btn-outline-secondary');
        }
        
        // Ensure dark mode classes are removed
        html.classList.remove('dark-mode-preload');
    }
}

// Function to initialize dark mode based on user preference
function initializeDarkMode() {
    const darkMode = localStorage.getItem('darkMode');
    const darkModeToggle = document.getElementById('darkModeToggle');
    const icon = document.querySelector('#darkModeToggle i');
    const text = document.querySelector('#darkModeToggle span');
    const navbar = document.querySelector('.navbar');
    
    // Remove preload class to allow transitions
    setTimeout(() => {
        document.documentElement.classList.remove('dark-mode-preload');
        document.body.classList.remove('dark-mode-preload');
    }, 100);
    
    if (darkMode === 'enabled') {
        // Apply dark mode
        document.body.classList.add('dark-mode');
        if (icon) {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
        }
        if (text) text.textContent = 'Toggle Light Mode';
        
        // Update navbar classes for dark mode
        if (navbar) {
            navbar.classList.remove('navbar-light', 'bg-light');
            navbar.classList.add('navbar-dark', 'bg-dark');
        }
        
        // Update dark mode toggle button
        if (darkModeToggle) {
            darkModeToggle.classList.remove('btn-outline-secondary');
            darkModeToggle.classList.add('btn-outline-light');
        }
    } else {
        // Ensure light mode
        document.body.classList.remove('dark-mode');
        if (icon) {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
        }
        if (text) text.textContent = 'Toggle Dark Mode';
        
        // Update navbar classes for light mode
        if (navbar) {
            navbar.classList.remove('navbar-dark', 'bg-dark');
            navbar.classList.add('navbar-light', 'bg-light');
        }
        
        // Update dark mode toggle button
        if (darkModeToggle) {
            darkModeToggle.classList.remove('btn-outline-light');
            darkModeToggle.classList.add('btn-outline-secondary');
        }
    }
    
    // Add event listener to dark mode toggle button
    if (darkModeToggle) {
        // Remove any existing event listeners to prevent duplicates
        darkModeToggle.removeEventListener('click', toggleDarkMode);
        // Add the event listener
        darkModeToggle.addEventListener('click', toggleDarkMode);
    }
}

// Initialize the page when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeHostsTable();
    initializeDarkMode();
    
    // Set up event listener for the undo link
    const undoLink = document.querySelector('#undoLink');
    if (undoLink) {
        undoLink.addEventListener('click', function(e) {
            e.preventDefault();
            undoDelete();
        });
    }
}); 