const log_monitor = new function() {
    const self = this;
    
    self.fetchLogData = async function() {
        try {
            const response = await fetch(`/log_monitor/fetch?log_type=${self.logType.value}&log_tail=${self.logTailSelect.value}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            
            const data = await response.json();
            self.logContent.textContent = data.log_content;
            
            // Scroll to bottom
            self.logContent.parentElement.scrollTop = self.logContent.parentElement.scrollHeight;
        } catch (error) {
            console.error('Error fetching log data:', error);
            self.logContent.textContent = 'Error loading log data. Please try again.';
        }
    }
    
    self.init = function() {
        self.logType = document.getElementById('logTypeForm');
        self.logContent = document.getElementById('logContent');
        self.refreshLogBtn = document.getElementById('refreshLogBtn');
        self.autoRefreshSelect = document.getElementById('autoRefreshForm');
        self.logTailSelect = document.getElementById('logTailForm');
        
        self.refreshLogBtn.addEventListener('click', self.fetchLogData);
        
        self.logTailSelect.addEventListener('change', self.fetchLogData);
        self.logType.addEventListener('change', self.fetchLogData);
        
        self.autoRefreshSelect.addEventListener('change', function() {
            if (self.autoRefreshSelect.value == -1) {
                clearInterval(self.autoRefreshInterval);
            } else {
                self.fetchLogData();
                self.autoRefreshInterval = setInterval(self.fetchLogData, self.autoRefreshSelect.value * 1000);
            }
        });
        
        self.fetchLogData();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    log_monitor.init(); 
});