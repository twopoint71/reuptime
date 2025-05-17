const monitor = new function() {
    const self = this;
    self.fields = ['monitor_type', 'status', 'pid', 'uptime', 'last_active']
    self.monitor_type = document.querySelector('#monitorCard select[name="monitor_type"]');

    self.status = function() {
        const pad = (n) => n.toString().padStart(2, '0');
        fetch(`/admin_tools/monitor_status?monitor_type=${self.monitor_type.value}`)
            .then(response => response.json())
            .then(data => {
                console.log(data);
                
                self.fields.forEach(element => {
                    switch(element) {
                        case 'monitor_type':
                            value = data.monitor_type.toUpperCase();
                            break;
                        case 'status':
                            value = data.status.charAt(0).toUpperCase() + data.status.slice(1);
                            break;
                        case 'uptime':
                            value = utils.secondsToUptime(data.uptime);
                            break;
                        case 'last_active':
                            const d = new Date(data.last_active);
                            value = `${d.getUTCFullYear()}-${pad(d.getUTCMonth())}-${pad(d.getDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())} UTC`;
                            break;
                        default:
                            value = data[element];
                    }
                    document.querySelector(`#monitorCard .card-body span[name="${element}"]`).textContent = value;
                });
            });
    }

    self.stop = function(element) {
        window.location.href = `/admin_tools/monitor_control?action=stop&monitor_type=${self.monitor_type.value}`;
    }

    self.start = function(element) {
        window.location.href = `/admin_tools/monitor_control?action=start&monitor_type=${self.monitor_type.value}`;
    }

    self.refresh = function(element) {
        window.location.href = `/admin_tools/monitor_control?action=refresh&monitor_type=${self.monitor_type.value}`;
    }

    self.init = function() {
        self.status();
    }
}

const systemInfo = new function() {
    const self = this;
    self.fields = ['monitored_hosts', 'unmonitored_hosts', 'server_time', 'server_uptime',];

    self.refresh = function() {
        fetch('/admin_tools/system_info')
        .then(response => response.json())
        .then(data => {
            let percent = 0.00;

                self.fields.forEach(element => {
                    switch(element) {
                        case 'monitored_hosts':
                            percent = ((data.monitored_hosts / data.total_hosts) * 100).toFixed(2);
                            value = `${data.monitored_hosts} / ${data.total_hosts} - ${percent}%`;
                            break;
                        case 'unmonitored_hosts':
                            percent = ((data.unmonitored_hosts / data.total_hosts) * 100).toFixed(2);
                            value = `${data.unmonitored_hosts} / ${data.total_hosts} - ${percent}%`;
                            break;
                        case 'server_time':
                            value = `${data.server_time} UTC`;
                            break;
                        case 'server_uptime':
                            value = utils.secondsToUptime(data.server_uptime);
                            break;
                        default:
                            value = data[element];
                    }

                    document.querySelector(`#systemInfoCard .card-body span[name="${element}"]`).textContent = value;
                });
            });
    }

    self.init = function() {
        self.refresh();
    }
}

function saveDowntimeAllotment() {
    const allotment = document.getElementById('downtimeAllotment').value;

    fetch('/api/downtime_allotment', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            downtime_allotment: parseInt(allotment)
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showToast('Error saving downtime allotment: ' + data.error, 'danger');
        } else {
            showToast('Downtime allotment saved successfully', 'success');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error saving downtime allotment: ' + error.message, 'danger');
    });
}

 document.addEventListener('DOMContentLoaded', function() {
    monitor.init();
    systemInfo.init();
});