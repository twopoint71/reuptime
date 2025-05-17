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
    
    "milspecDate": function(inputDate) {
        const date = new Date(inputDate);
        const year = date.getFullYear();
        const month = ('0' + date.getMonth()).slice(-2);
        const day = ('0' + date.getDate()).slice(-2);
        const hours = ('0' + date.getHours()).slice(-2);
        const minutes = ('0' + date.getMinutes()).slice(-2);
        return `${year}-${month}-${day} ${hours}:${minutes} UTC`
    },
    
    "statusBadge": function(value) {
        const text = value == 1 ? 'UP' : 'DOWN';
        const style = value == 1 ? 'bg-success' : 'bg-danger';
        const span = utils.html.span(text);
        span.setAttribute('class', 'badge ' + style);
        return span;
    },
    
    "html": {
        "a": function(content="") {
            var ele = document.createElement("a");
            ele.append(content);
            return ele;
        },
        "button": function(content="") {
            var ele = document.createElement("button");
            ele.append(content);
            return ele;
        },
        "canvas": function(content="") {
            var ele = document.createElement("canvas");
            ele.append(content);
            return ele;
        },
        "div": function(content="") {
            var ele = document.createElement("div");
            ele.append(content);
            return ele;
        },
        "i": function(content="") {
            var ele = document.createElement("i");
            ele.append(content);
            return ele;
        },
        "label": function(content="") {
            var ele = document.createElement("label");
            ele.append(content);
            return ele;
        },
        "select": function(content="") {
            var ele = document.createElement("select");
            ele.append(content);
            return ele;
        },
        "option": function(content="", value="") {
            var ele = document.createElement("option");
            ele.append(content);
            ele.setAttribute("value", value);
            return ele;
        },
        "span": function(content="") {
            var ele = document.createElement("span");
            ele.append(content);
            return ele;
        },
        "tr": function(content="") {
            var ele = document.createElement("tr");
            ele.append(content);
            return ele;
        },
        "td": function(content="") {
            var ele = document.createElement("td");
            ele.append(content);
            return ele;
        }
        
    },
    
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
    },
    
    "getHostData": function(element) {
        return JSON.parse(element.closest('tr').dataset.host);
    },
    
    "getTimeDifference": function(newerTimestamp, olderTimstamp) {
        const start = new Date(olderTimstamp);
        const end = new Date(newerTimestamp);
        let diffMs = end - start;
        
        const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        diffMs -= days * 1000 * 60 * 60 * 24;
        
        const hours = Math.floor(diffMs / (1000 * 60 * 60));
        diffMs -= hours * 1000 * 60 * 60;
        
        const minutes = Math.floor(diffMs / (1000 * 60));
        
        return { days, hours, minutes };
    },      
    
    "secondsToUptime": function(secondStamp) {
        const hours = Math.floor(secondStamp / 3600);
        const minutes = Math.floor((secondStamp % 3600) / 60);
        const seconds = Math.floor(secondStamp % 60);
        return `${hours}h ${minutes}m ${seconds}s`;
    },
    
    "colors": function() {
        return {
            danger: getComputedStyle(document.body).getPropertyValue('--bs-danger'),
            success: getComputedStyle(document.body).getPropertyValue('--bs-success'),
            bodyBg: getComputedStyle(document.body).getPropertyValue('--bs-body-bg'),
            bodyColor: getComputedStyle(document.body).getPropertyValue('--bs-body-color')
        }
    }   
}

var metricsChart = new function() {
    const self = this;
    self.params = null;
    self.colors = utils.colors();
    
    self.rrdToChartData = function(rrdData) {
        const [epochStart, epochEnd, epochStep] = rrdData[0];
        const metricNames = rrdData[1];
        const values = rrdData[2];
        
        const metricToColorMap = {
            "uptime": self.colors.success,
            "latency": self.colors.danger
        }
        
        // Generate timestamps for each data point
        const timestamps = [];
        for (let t = epochStart; t <= epochEnd; t += epochStep) {
            timestamps.push(t);
        }
        
        // Create datasets for each metric
        const datasets = metricNames.map((metricName, metricIndex) => {
            return {
                label: metricName.charAt(0).toUpperCase() + metricName.slice(1),
                data: values.map((point, pointIndex) => ({
                    x: timestamps[pointIndex],
                    y: point[metricIndex]
                })).filter(point => point.y !== null),
                borderColor: metricToColorMap[metricName],
                backgroundColor: metricToColorMap[metricName],
                tension: 0.1
            };
        });
        
        return {
            datasets: datasets
        };
    }
    
    self.suggestedMax = function(chartData) {
        // Get the maximum y value from all datasets
        const maxValue = Math.max(...chartData.datasets.map(dataset => 
            Math.max(...dataset.data.map(point => point.y))
        ));
        
        // Add 20% to the max value and round to the nearest 50th then subtract 10%
        const buffedMaxValue =(Math.ceil((maxValue * 1.2) / 50) * 50);
        return buffedMaxValue - (buffedMaxValue * 0.1);
    }
    
    self.renderChart = function(chartData) {
        chart = new Chart(
            self.params.container.querySelector('canvas').getContext('2d'),
            {
                type: 'line',
                data: chartData,
                options: {
                    responsive: true,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    scales: {
                        y: {
                            type: 'linear',
                            position: 'left',
                            beginAtZero: true,
                            ticks: {
                                color: self.colors.bodyColor,
                                font: { size: 14}
                            },
                            title: {
                                display: true,
                                text: 'Uptime (%)',
                                color: self.colors.success,
                                font: { size: 14}
                            },
                            suggestedMax: self.suggestedMax(chartData),
                        },
                        y1: {
                            type: 'linear',
                            position: 'right',
                            beginAtZero: true,
                            ticks: {
                                color: self.colors.bodyColor,
                                font: { size: 14}
                            },
                            title: {
                                display: true,
                                text: 'Latency (ms)',
                                color: self.colors.danger,
                                font: { size: 14}
                            },
                            suggestedMax: self.suggestedMax(chartData),
                        },
                        x: {
                            type: 'linear', // Use linear scale instead of time
                            title: {
                                display: true,
                                text: 'Time',
                                color: self.colors.bodyColor,
                                font: { size: 14}
                            },
                            ticks: {
                                color: self.colors.bodyColor,
                                font: { size: 14},
                                callback: function(value) {
                                    // Convert Unix timestamp to readable time
                                    const date = new Date(value * 1000);
                                    const datesString = date.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' });
                                    const timesString = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
                                    return [timesString, datesString];
                                }
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: self.colors.bodyColor
                            }
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    const label = context.dataset.label || '';
                                    const value = (context.parsed.y).toFixed(3);
                                    // Format latency with ms unit, leave uptime as is
                                    return `${label}: ${label === 'Latency' ? value + ' ms' : value + ' %'}`;
                                },
                                title: function(context) {
                                    const timestamp = context[0].parsed.x;
                                    const date = new Date(timestamp * 1000);
                                    return date.toLocaleString();
                                }
                            }
                        }
                    }
                }
            });
        }
        
        self.startChartRefresh = function(interval) {
            self.intervalId = setInterval(self.refresh, (interval * 1000));
        }
        
        self.stopChartRefresh = function() {
            clearInterval(self.intervalId);
        }
        
        self.renderHTML = function() {
            const html = utils.html.div();
            let col = null;
            let label = null;
            let option = null;
            
            const TEXT = 1;
            const VALUE = 0;
            
            const toolbar = utils.html.div();
            toolbar.setAttribute('class', 'row');
            
            /*
            * time range resolution code
            */
            const trrc = utils.html.select();
            self.trrc = trrc;
            trrc.setAttribute('class', 'form-select form-select-sm');
            [
                [0, "Last 15 minutes @ 30 second resolution"],
                [1, "Last hour @ 1 minute resolution"],
                [2, "Last 3 hours @ 5 minute resolution"],
                [3, "Last day @ hourly resolution"],
                [4, "Last 3 days @ hourly resolution"],
                [5, "Last month @ daily resolution"],
                [6, "Last year @ weekly resolution "]
            ].forEach(option => {
                option = utils.html.option(option[TEXT], option[VALUE]);
                if (option[VALUE] == "1") {
                    option.setAttribute('selected', 'selected');
                }
                trrc.append(option);
            });
            trrc.addEventListener('change', self.refresh);
            label = utils.html.label('Time Range & Resolution');
            col = utils.html.div();
            col.setAttribute('class', 'col-md-4');
            col.append(label);
            col.append(trrc);
            toolbar.append(col);
            
            /*
            * Average uptime
            */
            col = utils.html.div();
            col.setAttribute('class', 'col-md-2');
            const aveUptimeLabel = utils.html.label('Average Uptime');
            aveUptimeLabel.setAttribute('class', 'w-100 text-center');
            const avgUptime = utils.html.div();
            avgUptime.setAttribute('name', 'avgUptime');
            avgUptime.setAttribute('class', 'text-center');
            col.append(aveUptimeLabel);
            col.append(avgUptime);
            toolbar.append(col);
            
            /*
            * Average latency
            */
            col = utils.html.div();
            col.setAttribute('class', 'col-md-2');
            const aveLatencyLabel = utils.html.label('Average Latency');
            aveLatencyLabel.setAttribute('class', 'w-100 text-center');
            const avgLatency = utils.html.div();
            avgLatency.setAttribute('name', 'avgLatency');
            avgLatency.setAttribute('class', 'text-center');
            col.append(aveLatencyLabel);
            col.append(avgLatency);
            toolbar.append(col);
            
            /*
            * refresh button
            */
            const refreshIcon = utils.html.i();
            refreshIcon.setAttribute('class', 'fa fa-refresh');
            const refreshBtn = utils.html.button(refreshIcon);
            refreshBtn.append(' Refresh');
            refreshBtn.setAttribute('class', 'btn btn-sm btn-primary');
            refreshBtn.addEventListener('click', function() {
                self.refresh();
            });
            
            /*
            * auto refresh
            */
            const autoRefresh = utils.html.select();
            autoRefresh.setAttribute('class', 'form-select form-select-sm w-auto flex-grow-0');
            [
                ["-1", "Off"],
                ["60", "1 Minute"],
                ["300", "5 Minutes"],
                ["1800", "30 Minutes"],
                ["3600", "1 hour"]
            ].forEach(option => {
                option = utils.html.option(option[TEXT], option[VALUE]);
                if (option[VALUE] == "300") {
                    option.setAttribute('selected', 'selected');
                }
                autoRefresh.append(option);
            });
            autoRefresh.addEventListener('change', function() {
                if (autoRefresh.value == -1) {
                    self.stopChartRefresh();
                } else {
                    self.refresh();
                    self.startChartRefresh(interval=autoRefresh.value);
                }
            });
            label = utils.html.label('Auto Refresh');
            label.setAttribute('class', 'w-100 text-end');
            col = utils.html.div();
            col.setAttribute('class', 'col-md-4');
            col.append(label);
            const refreshActions = utils.html.div();
            refreshActions.setAttribute('class', 'd-flex gap-2 justify-content-end');
            refreshActions.append(refreshBtn);
            refreshActions.append(autoRefresh);
            col.append(refreshActions);
            toolbar.append(col); 
            
            html.append(toolbar);
            
            /*
            * canvas
            */
            const canvas = utils.html.canvas();
            canvas.setAttribute('name', 'metricsChart');
            html.append(canvas);
            
            self.params.container.innerHTML = '';
            self.params.container.append(html);
            
            return true;
        }
        
        self.renderAverages = function(chartData) {
            const avgUptime = chartData.datasets[0].data.reduce((acc, point) => acc + point.y, 0) / chartData.datasets[0].data.length;
            const avgLatency = chartData.datasets[1].data.reduce((acc, point) => acc + point.y, 0) / chartData.datasets[1].data.length;
            self.params.container.querySelector('[name="avgUptime"]').textContent = avgUptime.toFixed(2) + '%';
            self.params.container.querySelector('[name="avgLatency"]').textContent = avgLatency.toFixed(2) + 'ms';
        }
        
        self.refresh = function() {
            const chart = Chart.getChart(self.params.container.querySelector('canvas'));
            if (chart) {
                chart.destroy();
            }
            self.colors = utils.colors();
            
            fetch(`/monitored_hosts/metrics?host_uuid=${self.params.rrdFile}&time_range_resolution_code=${self.trrc.value}`)
            .then(response => response.json())
            .then(data => {
                const chartData = self.rrdToChartData(data.rrd_data);
                self.renderChart(chartData);
                self.renderAverages(chartData);
            })
            .catch(error => {
                console.error('Error fetching metrics:', error);
            });
        }
        
        self.populate = function(params) {
            if (self.params == null || self.params.rrdFile != params.rrdFile) {
                self.params = params;
            }
            
            if (self.renderHTML()) {
                self.refresh();
            }
        }
    }

document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el);
});
      