// @ts-nocheck
var utils = {
    "actionDelay": function() {
        self = this;
        self.callback = null;
        self.data = null;
        self.savedText = null;
        self.seconds = null;
        self.target = null;
        self.timeoutId = null;

        self.cancelDelay = function() {
            self.target.innerHTML = self.savedText;
            clearTimeout(self.timeoutId);
        },

        self.initiateDelay = function() {
            self.target = event.target;
            self.target.addEventListener('mouseup', self.cancelDelay, false);
            self.target.addEventListener('mouseleave', self.cancelDelay, false);
            self.savedText = self.target.innerHTML;
            self.seconds = 2;
            self.target.style.width = Math.ceil(self.target.getBoundingClientRect().width) + 'px';
            self.delay();
        }

        self.delay = function() {
            self.target.innerHTML = self.seconds;
            self.timeoutId = setTimeout(() => {
                if (self.seconds < 2) {
                    self.callback(self.data);
                } else {
                    self.seconds--;
                    self.delay();
                }
            }, 1000);
        }
    },

    "html": {
        "div": function(content="") {
            var ele = document.createElement('div');
            ele.append(content);
            return ele;
        },
        "select": function(content="") {
            var ele = document.createElement('select');
            ele.append(content);
            return ele;
        },
        "option": function(content="", value="") {
            var ele = document.createElement('option');
            ele.append(content);
            ele.setAttribute("value", value);
            return ele;
        },
        "span": function(content="") {
            var ele = document.createElement('span');
            ele.append(content);
            return ele;
        }
    },

    // order can be ASC(ending) or DESC(ending)
    "tableColumnSort": function(event) {
        var self = this;
        self.columnIndex = document.getElementById('sortBy').value;
        self.order =  document.getElementById('orderBy').value;
        self.tableId = document.getElementById('orderBy').getAttribute('data-table-id');
        self.tbody = document.querySelector(`#${self.tableId} tbody`);
        self.rows = Array.from(self.tbody.querySelectorAll('tr'));

        // untested with numerical data, all table data for this project is strings
        self.rows.sort((rowX, rowZ) => {
            cellX = rowX.querySelector(`td:nth-child(${self.columnIndex})`).innerText.trim().toString();
            cellZ = rowZ.querySelector(`td:nth-child(${self.columnIndex})`).innerText.trim().toString();

            return (cellX > cellZ ? 1 : -1) * (self.order == 'ASC' ? 1 : -1);
        });

        self.rows.forEach((row) => self.tbody.appendChild(row));
    }

}

// Function to create or update a chart
function createOrUpdateChart(canvasId, hostUuid, timeRange = '24h') {
    const ctx = document.getElementById(canvasId).getContext('2d');
    let chart = Chart.getChart(canvasId);

    if (chart) {
        chart.destroy();
    }

    // Fetch data from API with time range parameter
    fetch(`/api/metrics/${hostUuid}?range=${timeRange}&t=${Date.now()}`)
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
function startChartRefresh(canvasId, hostUuid, interval = 300000, timeRange = '24h') { // 5 minutes default
    createOrUpdateChart(canvasId, hostUuid, timeRange);
    return setInterval(() => createOrUpdateChart(canvasId, hostUuid, timeRange), interval);
}

// Function to stop chart refresh
function stopChartRefresh(intervalId) {
    clearInterval(intervalId);
}

// Function to set up graph modals for all hosts
function setupGraphModals() {
    // Get all graph buttons
    const graphButtons = document.querySelectorAll('.graph-btn');

    // Add click event listeners to each button
    graphButtons.forEach(button => {
        const hostUuid = button.getAttribute('data-host-uuid');
        const chartId = `metricsChart${hostUuid}`;
        let refreshIntervalId = null;

        button.addEventListener('click', function() {
            // Wait for the modal to be shown before creating the chart
            setTimeout(() => {
                // Get the modal elements
                const modal = document.getElementById(`graphModal${hostUuid}`);
                const timeRangeSelect = document.getElementById(`timeRange${hostUuid}`);
                const refreshIntervalSelect = document.getElementById(`refreshInterval${hostUuid}`);
                const autoRefreshToggle = document.getElementById(`autoRefresh${hostUuid}`);

                // Initial chart creation
                createOrUpdateChart(chartId, hostUuid, timeRangeSelect.value);

                // Set up event listeners for controls
                timeRangeSelect.addEventListener('change', function() {
                    createOrUpdateChart(chartId, hostUuid, this.value);

                    // If auto-refresh is enabled, restart it with the new time range
                    if (autoRefreshToggle.checked) {
                        if (refreshIntervalId) {
                            stopChartRefresh(refreshIntervalId);
                        }
                        const interval = parseInt(refreshIntervalSelect.value);
                        refreshIntervalId = startChartRefresh(chartId, hostUuid, interval, timeRangeSelect.value);
                    }
                });

                refreshIntervalSelect.addEventListener('change', function() {
                    // If auto-refresh is enabled, restart it with the new interval
                    if (autoRefreshToggle.checked) {
                        if (refreshIntervalId) {
                            stopChartRefresh(refreshIntervalId);
                        }
                        const interval = parseInt(this.value);
                        refreshIntervalId = startChartRefresh(chartId, hostUuid, interval, timeRangeSelect.value);
                    }
                });

                autoRefreshToggle.addEventListener('change', function() {
                    if (this.checked) {
                        // Start auto-refresh
                        const interval = parseInt(refreshIntervalSelect.value);
                        refreshIntervalId = startChartRefresh(chartId, hostUuid, interval, timeRangeSelect.value);
                        refreshIntervalSelect.disabled = false;
                    } else {
                        // Stop auto-refresh
                        if (refreshIntervalId) {
                            stopChartRefresh(refreshIntervalId);
                            refreshIntervalId = null;
                        }
                        refreshIntervalSelect.disabled = true;
                    }
                });

                // Clean up when modal is hidden
                modal.addEventListener('hidden.bs.modal', function() {
                    if (refreshIntervalId) {
                        stopChartRefresh(refreshIntervalId);
                        refreshIntervalId = null;
                    }

                    // Reset auto-refresh toggle
                    if (autoRefreshToggle) {
                        autoRefreshToggle.checked = false;
                    }

                    // Reset refresh interval select
                    if (refreshIntervalSelect) {
                        refreshIntervalSelect.disabled = true;
                    }
                });
            }, 100);
        });
    });
}

// Function to initialize the page with hosts data
function initializeHostsTable() {
    fetch('/api/hosts')
        .then(response => response.json())
        .then(data => {
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
            data.hosts_list.forEach(host => {
                // Create table row
                const row = document.createElement('tr');

                // Add host data to row
                row.innerHTML = `
                    <td>${host.host_name}</td>
                    <td>${host.host_ip_address}</td>
                    <td>${host.region}</td>
                    <td>
                        <span class="badge ${host.is_active ? 'bg-success' : 'bg-danger'}">
                            ${host.is_active ? 'UP' : 'DOWN'}
                        </span>
                    </td>
                    <td>${host.last_check || 'Never'}</td>
                    <td>
                        <button type="button" class="btn btn-sm btn-secondary" data-bs-toggle="modal" data-bs-target="#hostDetails${host.uuid}">
                            Details
                        </button>
                        <a href="/api/metrics/${host.uuid}" class="btn btn-sm btn-info">Metrics</a>
                        <button type="button" class="btn btn-sm btn-primary graph-btn" data-bs-toggle="modal" data-bs-target="#graphModal${host.uuid}" data-host-uuid="${host.uuid}">
                            Graph
                        </button>
                    </td>
                `;

                tableBody.appendChild(row);

                // Create details modal
                const detailsModal = document.createElement('div');
                detailsModal.className = 'modal fade';
                detailsModal.id = `hostDetails${host.uuid}`;
                detailsModal.setAttribute('tabindex', '-1');
                detailsModal.setAttribute('aria-labelledby', `hostDetailsLabel${host.uuid}`);
                detailsModal.setAttribute('aria-hidden', 'true');

                detailsModal.innerHTML = `
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="hostDetailsLabel${host.uuid}">Host Details: ${host.host_name}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <dl class="row">
                                    <dt class="col-sm-4">Account Label</dt>
                                    <dd class="col-sm-8">${host.account_label}</dd>

                                    <dt class="col-sm-4">Account ID</dt>
                                    <dd class="col-sm-8">${host.account_id}</dd>

                                    <dt class="col-sm-4">Region</dt>
                                    <dd class="col-sm-8">${host.region}</dd>

                                    <dt class="col-sm-4">Instance ID</dt>
                                    <dd class="col-sm-8">${host.host_id}</dd>

                                    <dt class="col-sm-4">Instance IP</dt>
                                    <dd class="col-sm-8">${host.host_ip_address}</dd>

                                    <dt class="col-sm-4">Instance Name</dt>
                                    <dd class="col-sm-8">${host.host_name}</dd>

                                    <dt class="col-sm-4">Downtime Allotment</dt>
                                    <dd class="col-sm-8">${host.downtime_allotment} / ${data.downtime_allotment}</dd>

                                    <dt class="col-sm-4">Status</dt>
                                    <dd class="col-sm-8">
                                        <span class="badge ${host.is_active ? 'bg-success' : 'bg-danger'}">
                                            ${host.is_active ? 'UP' : 'DOWN'}
                                        </span>
                                    </dd>

                                    <dt class="col-sm-4">Last Check</dt>
                                    <dd class="col-sm-8">${host.last_check || 'Never'}</dd>

                                    <dt class="col-sm-4">Created At</dt>
                                    <dd class="col-sm-8">${host.created_at}</dd>
                                </dl>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-danger" onclick="unmonitorHost('${host.uuid}', '${host.host_name}')">Unmonitor Host</button>
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                `;

                modalsContainer.appendChild(detailsModal);

                // Create graph modal
                const graphModal = document.createElement('div');
                graphModal.className = 'modal fade';
                graphModal.id = `graphModal${host.uuid}`;
                graphModal.setAttribute('tabindex', '-1');
                graphModal.setAttribute('aria-labelledby', `graphModalLabel${host.uuid}`);
                graphModal.setAttribute('aria-hidden', 'true');

                graphModal.innerHTML = `
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="graphModalLabel${host.uuid}">Metrics Graph: ${host.host_name}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="row mb-3">
                                    <div class="col-md-4">
                                        <label for="timeRange${host.uuid}" class="form-label">Time Range:</label>
                                        <select id="timeRange${host.uuid}" class="form-select">
                                            <option value="5m">5 Minutes</option>
                                            <option value="30m">30 Minutes</option>
                                            <option value="1h">1 Hour</option>
                                            <option value="6h">6 Hours</option>
                                            <option value="24h" selected>24 Hours</option>
                                            <option value="3d">3 Days</option>
                                            <option value="1w">1 Week</option>
                                            <option value="2w">2 Weeks</option>
                                            <option value="1mo">1 Month</option>
                                            <option value="3mo">3 Months</option>
                                            <option value="6mo">6 Months</option>
                                            <option value="1y">1 Year</option>
                                        </select>
                                    </div>
                                    <div class="col-md-4">
                                        <label for="refreshInterval${host.uuid}" class="form-label">Refresh Interval:</label>
                                        <select id="refreshInterval${host.uuid}" class="form-select" disabled>
                                            <option value="30000">30 Seconds</option>
                                            <option value="60000">1 Minute</option>
                                            <option value="300000" selected>5 Minutes</option>
                                            <option value="600000">10 Minutes</option>
                                            <option value="1800000">30 Minutes</option>
                                        </select>
                                    </div>
                                    <div class="col-md-4 d-flex align-items-end">
                                        <div class="form-check form-switch">
                                            <input class="form-check-input" type="checkbox" id="autoRefresh${host.uuid}">
                                            <label class="form-check-label" for="autoRefresh${host.uuid}">Auto Refresh</label>
                                        </div>
                                    </div>
                                </div>
                                <canvas id="metricsChart${host.uuid}"></canvas>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-primary" onclick="createOrUpdateChart('metricsChart${host.uuid}', '${host.uuid}', document.getElementById('timeRange${host.uuid}').value)">Refresh Now</button>
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                `;

                modalsContainer.appendChild(graphModal);
            });

            // Set up event listeners for the graph buttons
            setupGraphModals();
            utils.tableColumnSort();
        })
        .catch(error => {
            console.error('Error fetching hosts:', error);
        });
}

// Function to unmonitor a host
function unmonitorHost(hostUuid, hostName) {
    fetch(`/unmonitor_host/${hostUuid}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Store the unmonitored host UUID for potential undo
            window.lastUnmonitoredHostUuid = hostUuid;

            // Get the ID of the entry in the unmonitored_hosts table
            fetch('/api/unmonitored_hosts')
                .then(response => response.json())
                .then(unmonitoredHosts => {
                    // Find the most recently unmonitored host that matches our original host UUID
                    // We're looking for the host that was just unmonitored
                    const recentlyUnmonitoredHost = unmonitoredHosts.find(host =>
                        host.host_id === data.unmonitored_host_data.host_id &&
                        host.host_name === data.unmonitored_host_data.host_name
                    );

                    if (recentlyUnmonitoredHost) {
                        window.lastUnmonitoredHostUuid = recentlyUnmonitoredHost.uuid;

                        // Update the toast message with the host name
                        document.getElementById('unmonitoredHostName').textContent = hostName || 'Host';

                        // Show the undo toast
                        const undoToast = new bootstrap.Toast(document.getElementById('undoToast'));
                        undoToast.show();
                    }
                })
                .catch(error => {
                    console.error('Error fetching unmonitored hosts:', error);
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
            alert('Failed to unmonitor host: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to unmonitor host');
    });
}

// Function to restore host to a monitored state
function restoreHost(hostUuid) {
    if (window.lastUnmonitoredHostUuid) {
        fetch(`/restore_host/${window.lastUnmonitoredHostUuid}`, {
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
                console.log('Successfully restored host with UUID:', data.restored_host_uuid);

                // Hide the toast
                const undoToast = bootstrap.Toast.getInstance(document.getElementById('undoToast'));
                if (undoToast) {
                    undoToast.hide();
                }

                // Refresh the hosts table
                initializeHostsTable();
            } else {
                console.error('Failed to restore host:', data.error);
                alert('Failed to restore host: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to restore host: ' + error.message);
        });
    } else {
        console.error('No unmonitored host UUID found');
        alert('Cannot restore: No recently unmonitored host found');
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

// Function to show a toast notification
function showToast(message, type = 'success') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }

    // Create a unique ID for the toast
    const toastId = 'toast-' + Date.now();

    // Create toast HTML
    const toastHTML = `
    <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="toast-header bg-${type} text-white">
            <strong class="me-auto">Notification</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    </div>
    `;

    // Add toast to container
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);

    // Initialize and show the toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();

    // Remove toast from DOM after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
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
            restoreHost(window.lastUnmonitoredHostUuid);
        });
    }

    // Check for host_added parameter in URL
    const urlParams = new URLSearchParams(window.location.search);
    const hostAdded = urlParams.get('host_added');
    if (hostAdded) {
        showToast(`Host "${hostAdded}" added successfully!`, 'success');
        // Remove the parameter from the URL without reloading the page
        const newUrl = window.location.pathname;
        window.history.replaceState({}, document.title, newUrl);
    }

    // Check for hosts_imported parameter in URL
    const hostsImported = urlParams.get('hosts_imported');
    if (hostsImported) {
        showToast(`${hostsImported} hosts imported successfully!`, 'success');
        // Remove the parameter from the URL without reloading the page
        const newUrl = window.location.pathname;
        window.history.replaceState({}, document.title, newUrl);
    }

    document.querySelectorAll('form select').forEach((ele) => { ele.addEventListener('change', utils.tableColumnSort); });
});