var remonitorHost = new function() {
    const self = this;
    
    self.init = function(element) {
        const host = utils.getHostData(element);
        const delay = new utils.actionDelay();
        delay.data = { "host_uuid": host.uuid };
        delay.callback = self.restore;
        delay.target = element;
        delay.initiateDelay();
    }
    
    self.restore = function(data) {
        window.location.href = `unmonitored_hosts/remonitor?host_uuid=${data.host_uuid}`;
    }
}

var deleteHost = new function() {
    const self = this;
    
    self.init = function(element) {
        const host = utils.getHostData(element);
        const delay = new utils.actionDelay();
        delay.data = { "host_uuid": host.uuid };
        delay.callback = self.delete;
        delay.target = element;
        delay.initiateDelay();
    }
    
    self.delete = function(data) {
        window.location.href = `unmonitored_hosts/delete?host_uuid=${data.host_uuid}`;
    }
}
