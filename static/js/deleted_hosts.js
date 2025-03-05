// Function to fetch deleted hosts from the API
async function fetchDeletedHosts() {
    try {
        const response = await fetch('/api/deleted_hosts');
        if (!response.ok) {
            throw new Error('Failed to fetch deleted hosts');
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching deleted hosts:', error);
        return [];
    }
}

// Function to show a toast notification
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        // Create toast container if it doesn't exist
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
    }
    
    const toastId = 'toast-' + Date.now();
    const toastHTML = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header bg-${type} text-white">
                <strong class="me-auto">ReUptime</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    document.getElementById('toastContainer').insertAdjacentHTML('beforeend', toastHTML);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();
    
    // Remove toast from DOM after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// Function to restore a deleted host
async function restoreHost(hostId) {
    try {
        const response = await fetch('/api/restore_host', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ host_id: hostId }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to restore host');
        }
        
        // Refresh the deleted hosts table
        initializeDeletedHostsTable();
        
        // Show success message with toast
        showToast('Host restored successfully!', 'success');
        
        // Redirect to main page after a short delay
        setTimeout(() => {
            window.location.href = '/';
        }, 1500);
    } catch (error) {
        console.error('Error restoring host:', error);
        showToast('Failed to restore host: ' + error.message, 'danger');
    }
}

// Function to permanently delete a host
async function permanentlyDeleteHost(hostId) {
    try {
        const response = await fetch('/api/permanently_delete_host', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ host_id: hostId }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to permanently delete host');
        }
        
        // Refresh the deleted hosts table
        initializeDeletedHostsTable();
        
        // Show success message with toast
        showToast('Host permanently deleted!', 'success');
    } catch (error) {
        console.error('Error permanently deleting host:', error);
        showToast('Failed to permanently delete host: ' + error.message, 'danger');
    }
}

// Function to initialize the deleted hosts table
async function initializeDeletedHostsTable() {
    const deletedHosts = await fetchDeletedHosts();
    const tableBody = document.querySelector('#deletedHostsTable tbody');
    
    // Clear existing rows
    tableBody.innerHTML = '';
    
    if (deletedHosts.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="6" class="text-center">No deleted hosts found</td>';
        tableBody.appendChild(row);
        return;
    }
    
    // Add rows for each deleted host
    deletedHosts.forEach(host => {
        const row = document.createElement('tr');
        
        // Format the deleted_at date
        const deletedAt = new Date(host.deleted_at);
        const formattedDate = deletedAt.toLocaleString();
        
        // Determine status text and class
        const statusText = host.is_active ? 'Active' : 'Inactive';
        const statusClass = host.is_active ? 'bg-success' : 'bg-danger';
        
        row.innerHTML = `
            <td>${host.aws_instance_name || 'Unknown'}</td>
            <td>${host.aws_instance_ip || 'Unknown'}</td>
            <td>${host.aws_region || 'Unknown'}</td>
            <td><span class="badge ${statusClass}">${statusText}</span></td>
            <td>${formattedDate}</td>
            <td>
                <button class="btn btn-sm btn-success restore-btn" data-host-id="${host.id}">Restore</button>
                <button class="btn btn-sm btn-danger delete-btn" data-host-id="${host.id}">Delete Permanently</button>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Add event listeners to the restore and delete buttons
    document.querySelectorAll('.restore-btn').forEach(button => {
        button.addEventListener('click', (event) => {
            const hostId = event.target.getAttribute('data-host-id');
            restoreHost(hostId);
        });
    });
    
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', (event) => {
            const hostId = event.target.getAttribute('data-host-id');
            permanentlyDeleteHost(hostId);
        });
    });
}

// Function to toggle dark mode
function toggleDarkMode() {
    const body = document.body;
    const html = document.documentElement;
    const icon = document.querySelector('#darkModeToggle i');
    const text = document.querySelector('#darkModeToggle span');
    const navbar = document.querySelector('.navbar');
    const darkModeToggle = document.getElementById('darkModeToggle');
    
    // Toggle dark mode class on body and html
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

// Initialize the deleted hosts table when the page loads
document.addEventListener('DOMContentLoaded', () => {
    initializeDeletedHostsTable();
    initializeDarkMode();
    
    // Create toast container if it doesn't exist
    if (!document.getElementById('toastContainer')) {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
    }
}); 