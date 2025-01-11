class WANDetailsManager {
    constructor(wanId) {
        this.wanId = wanId;
        this.updateInterval = 60000; // 1 minute
        this.initEventListeners();
        this.startUpdates();
    }

    initEventListeners() {
        document.getElementById('forceNetworkScan').addEventListener('click', () => {
            this.updateDevices();
        });
    }

    getStatusClass(status) {
        switch (status) {
            case 'danger':
                return 'bg-danger';
            case 'warning':
                return 'bg-warning text-dark';
            case 'success':
                return 'bg-success';
            default:
                return 'bg-secondary';
        }
    }

    async updateWANInfo() {
        try {
            const response = await fetch(`/api/wans/${this.wanId}`);
            if (!response.ok) throw new Error('Erreur réseau');
            
            const wan = await response.json();
            
            // Mise à jour du badge de latence
            const latencyBadge = document.getElementById('latency-badge');
            const statusClass = this.getStatusClass(wan.latency_status);
            latencyBadge.className = `badge ${statusClass} float-end`;
            latencyBadge.textContent = wan.latency ? `${wan.latency} ms` : 'N/A';
            
            // Mise à jour de la latence moyenne
            const avgLatency = document.getElementById('avg-latency');
            avgLatency.className = statusClass;
            avgLatency.textContent = wan.avg_latency ? `${wan.avg_latency} ms` : 'N/A';
            
        } catch (error) {
            console.error('Erreur lors de la mise à jour des informations WAN:', error);
        }
    }

    async updateDevices() {
        try {
            const response = await fetch(`/api/wans/${this.wanId}/devices`);
            if (!response.ok) throw new Error('Erreur réseau');
            
            const devices = await response.json();
            const tbody = document.querySelector('#devices-table tbody');
            const devicesCount = document.getElementById('devices-count');
            
            tbody.innerHTML = '';
            devicesCount.textContent = devices.length;

            devices.forEach(device => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${device.ip}</td>
                    <td>${device.hostname || 'N/A'}</td>
                    <td>${device.mac || 'N/A'}</td>
                    <td>${device.vendor || 'N/A'}</td>
                    <td>
                        <span class="badge bg-${device.status === 'up' ? 'success' : 'danger'}">
                            ${device.status === 'up' ? 'En ligne' : 'Hors ligne'}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-primary scan-ports" data-ip="${device.ip}">
                            <i class="fa fa-search"></i> Scanner
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // Ajout des événements pour le scan des ports
            document.querySelectorAll('.scan-ports').forEach(button => {
                button.addEventListener('click', () => this.scanPorts(button.dataset.ip));
            });

        } catch (error) {
            console.error('Erreur lors de la mise à jour des appareils:', error);
        }
    }

    async scanPorts(ip) {
        try {
            const response = await fetch(`/api/wans/${this.wanId}/ports/${ip}`);
            if (!response.ok) throw new Error('Erreur réseau');
            
            const ports = await response.json();
            const tbody = document.querySelector('#ports-table tbody');
            tbody.innerHTML = '';

            ports.forEach(port => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${port.port}</td>
                    <td>${port.service || 'N/A'}</td>
                    <td>
                        <span class="badge bg-${port.state === 'open' ? 'success' : 'danger'}">
                            ${port.state}
                        </span>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // Affichage du modal
            const modal = new bootstrap.Modal(document.getElementById('portScanModal'));
            modal.show();

        } catch (error) {
            console.error('Erreur lors du scan des ports:', error);
        }
    }

    startUpdates() {
        this.updateWANInfo();
        this.updateDevices();
        setInterval(() => {
            this.updateWANInfo();
            this.updateDevices();
        }, this.updateInterval);
    }
}

// Création et démarrage du gestionnaire
const wanDetailsManager = new WANDetailsManager(WAN_ID);
