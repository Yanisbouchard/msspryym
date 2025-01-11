class WANDetailsManager {
    constructor(wanId) {
        this.wanId = wanId;
        this.updateInterval = 60000; // 1 minute
        this.initEventListeners();
        this.startUpdates();
    }

    initEventListeners() {
        const scanButton = document.getElementById('forceNetworkScan');
        if (scanButton) {
            scanButton.addEventListener('click', () => {
                // Désactiver le bouton pendant le scan
                scanButton.disabled = true;
                scanButton.innerHTML = '<i class="fa fa-refresh fa-spin"></i> Scan en cours...';
                
                // Lancer le scan
                this.updateDevices().finally(() => {
                    // Réactiver le bouton après le scan
                    scanButton.disabled = false;
                    scanButton.innerHTML = '<i class="fa fa-refresh"></i> Scanner';
                });
            });
        }
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
            // Forcer un scan réseau
            const scanResponse = await fetch(`/api/wans/${this.wanId}/scan`, {
                method: 'POST'
            });
            if (!scanResponse.ok) {
                console.error('Erreur lors du scan réseau');
            }
            
            // Attendre un peu pour laisser le temps au scan de se terminer
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // Récupérer les appareils
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
            const button = document.querySelector(`button[data-ip="${ip}"]`);
            button.disabled = true;
            button.innerHTML = '<i class="fa fa-search fa-spin"></i> Scan en cours...';
            
            const response = await fetch(`/api/wans/${this.wanId}/scan_ports`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ ip })
            });
            
            if (!response.ok) throw new Error('Erreur réseau');
            const data = await response.json();
            
            // Créer et afficher le modal
            const modal = document.getElementById('portScanModal');
            const modalBody = modal.querySelector('.modal-body');
            const tbody = modal.querySelector('#ports-table tbody');
            tbody.innerHTML = '';
            
            if (data.ports && data.ports.length > 0) {
                data.ports.forEach(port => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${port.port}</td>
                        <td>${port.protocol}</td>
                        <td>${port.state}</td>
                        <td>${port.service}</td>
                    `;
                    tbody.appendChild(tr);
                });
            } else {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center">Aucun port trouvé</td></tr>';
            }
            
            // Afficher le modal
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        } catch (error) {
            console.error('Erreur lors du scan des ports:', error);
            alert('Erreur lors du scan des ports');
        } finally {
            // Réactiver le bouton
            const button = document.querySelector(`button[data-ip="${ip}"]`);
            button.disabled = false;
            button.innerHTML = '<i class="fa fa-search"></i> Scanner';
        }
    }

    startUpdates() {
        // Mise à jour initiale
        this.updateWANInfo();
        this.updateDevices();
        
        // Mises à jour périodiques
        setInterval(() => {
            this.updateWANInfo();
            this.updateDevices();
        }, this.updateInterval);
    }
}

// Création et démarrage du gestionnaire
const wanDetailsManager = new WANDetailsManager(WAN_ID);
