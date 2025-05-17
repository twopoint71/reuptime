function populateHostDetailsModal(self) {
    const host = utils.getHostData(self);
    const title = document.querySelector('#hostDetailsCard .card-title [name="hostName"]');
    const body = document.querySelector('#hostDetailsCard .card-body');
    
    // reset the details card
    title.textContent = '';
    body.querySelectorAll('[name]').forEach(e => e.innerHTML = '');

    title.textContent = host.host_name;
    Object.keys(host).forEach(field => {
        const element = body.querySelector(`[name="${field}"]`);
        if (element) {
            switch (field) {
                case 'is_active':
                    element.append(utils.statusBadge(host[field]));
                    break;
                case 'last_check':
                case 'created_at':
                    element.textContent = utils.milspecDate(host[field]);
                    break;
                default:
                    element.textContent = host[field];
            }
        }
    });

    // populate the settings card
    const settings = document.querySelector('#hostSettingsCard .card-body');
    Object.keys(host).forEach(field => {
        const element = settings.querySelector(`[name="${field}"]`);
        if (element) {
            element.value = host[field];
        }
    });
}

function populateHostGraphModal(self) {
    const host = utils.getHostData(self);
    const modal = document.querySelector('#hostGraphModal');
    const params = { "rrdFile": host.uuid, "container": modal.querySelector('.modal-body') };
    metricsChart.populate(params);
    modal.querySelector('.modal-title [name="host_name"]').textContent = host.host_name;
}

function unmonitorHost(element) {
    window.location.href = `/monitored_hosts/unmonitor?host_uuid=${element.dataset.hostUuid}`;
}

function updateHost(element) {
    window.location.href = `/monitored_hosts/update?host_uuid=${element.dataset.hostUuid}`;
}
