const summary = new function() {
    const self = this;
    self.pieGraph = [];
    
    self.refreshGraph = function() {
        const card = document.getElementById('aggregateUptimeCard');
        const monitorType = card.querySelector('select[name="monitorType"]').value;
        const cardTitle = card.querySelector('.card-header [name="title"]');
        const cardBody = card.querySelector('.card-body [name="graph"]');
        
        switch (monitorType) {
            case 'icmp':
            rrdFile = 'monitors_aggregate_icmp';
            title = 'ICMP';
            break;
            default:
            rrdFile = 'monitors_aggregate_icmp';
        }
        
        cardTitle.textContent = title;
        const params = { "rrdFile": rrdFile, "container": cardBody };
        metricsChart.populate(params);
    }
    
    self.pieGraph = function(params) {
        const colors = utils.colors();
        // Create pie chart data
        const chartData = {
            labels: params.labels,
            datasets: [{
                data: params.data,
                backgroundColor: [colors.success, colors.danger],
                borderColor: colors.bodyBg,
                color: colors.bodyColor,
                hoverOffset: 4
            }]
        };
        
        // Clear previous chart if exists
        if (self.pieGraph[params.name]) {
            self.pieGraph[params.name].destroy();
        }
        
        // Create pie chart
        self.pieGraph[params.name] = new Chart(params.target, {
            type: 'pie',
            data: chartData,
            options: {
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: colors.bodyColor
                        }
                    },
                    tooltip: {
                        //titleColor: utils.colors.srcery.brightWhite,
                        //bodyColor: utils.colors.srcery.brightWhite,
                        callbacks: {
                            label: function(context) {
                                return '';
                            }
                        }
                    }
                }
            }
        });
    }
    
    self.refreshStatus = function() {
        const monitoredUpVsDown = document.querySelector('#monitoredHostsCard .card-body canvas[name="monitoredUpVsDown"]');
        const downtimeAllotment = document.querySelector('#monitoredHostsCard .card-body canvas[name="downtimeAllotment"]');
        
        fetch('/summary/host_info')
        .then(response => response.json())
        .then(data => {
            const totalMonitored = data.monitored_active_count + data.monitored_inactive_count;
            const percentageMonitoredUp = Math.floor((data.monitored_active_count / totalMonitored) * 100);
            const percentageMonitoredDown = Math.floor((data.monitored_inactive_count / totalMonitored) * 100);
            self.pieGraph({
                name: 'monitoredUpVsDown',
                labels: [`Up ${data.monitored_active_count} (${percentageMonitoredUp}%)`,
                    `Down ${data.monitored_inactive_count} (${percentageMonitoredDown}%)`],
                    data: [data.monitored_active_count, data.monitored_inactive_count],
                    target: monitoredUpVsDown
                });
                
                const totalAllotmentMonitored = data.monitored_has_allotment_count + data.monitored_has_no_allotment_count;
                const percentageAllotmentMonitoredUp = Math.floor((data.monitored_has_allotment_count / totalAllotmentMonitored) * 100);
                const percentageAllotmentMonitoredDown = Math.floor((data.monitored_has_no_allotment_count / totalAllotmentMonitored) * 100);
                self.pieGraph({
                    name: 'downtimeAllotment',
                    labels: [`Hosts With Allotment Available ${data.monitored_has_allotment_count} (${percentageAllotmentMonitoredUp}%)`,
                        `Hosts With Allotment Depleted ${data.monitored_has_no_allotment_count} (${percentageAllotmentMonitoredDown}%)`],
                        data: [data.monitored_has_allotment_count, data.monitored_has_no_allotment_count],
                        target: downtimeAllotment
                    });
                    
                });
            }
            
            self.refresh = function() {
                self.refreshGraph();
                self.refreshStatus();
            }
            
            self.themeObserver = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    if (mutation.attributeName === 'data-bs-theme') {
                        self.refresh();
                    }
                }
            });
            
            self.init = function() {
                self.themeObserver.observe(document.body, { attributes: true });
                self.refresh();
            }
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            summary.init();
        });