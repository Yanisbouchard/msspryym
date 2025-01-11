// Configuration des intervalles de rafraîchissement
const REFRESH_INTERVAL = 300000; // 5 minutes

// Configuration des graphiques
const chartConfig = {
    type: 'line',
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        scales: {
            y: {
                beginAtZero: true,
                max: 100
            }
        },
        plugins: {
            legend: {
                display: false
            }
        }
    }
};

// Gestionnaire du tableau de bord
class DashboardManager {
    constructor() {
        this.updateInterval = 5000; // 5 secondes
        this.startUpdates();
        this.initEventListeners();
    }

    // Démarrage des mises à jour
    startUpdates() {
        this.updateDevices();
        setInterval(() => this.updateDevices(), this.updateInterval * 2);
    }

    // Initialisation des écouteurs d'événements
    initEventListeners() {
        document.getElementById('forceNetworkScan').addEventListener('click', () => {
            this.updateDevices();
        });
    }

    // Mise à jour de la liste des appareils
    async updateDevices() {
        try {
            const response = await fetch('/api/devices');
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

    // Scan des ports d'un appareil
    async scanPorts(ip) {
        try {
            const response = await fetch(`/api/ports/${ip}`);
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
}

// Création et démarrage du gestionnaire
const dashboardManager = new DashboardManager();

// Rafraîchissement des appareils
function refreshDevices() {
    fetch('/api/devices')
        .then(response => response.json())
        .then(data => {
            const tbody = document.querySelector('#devices-table tbody');
            tbody.innerHTML = '';
            
            data.forEach(device => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${device.ip}</td>
                    <td>${device.hostname}</td>
                    <td>${device.mac}</td>
                    <td>${device.vendor}</td>
                    <td>
                        <span class="badge bg-${device.status === 'up' ? 'success' : 'danger'}">
                            ${device.status}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="scanPorts('${device.ip}')">
                            <i class="fa fa-search"></i> Scan
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            
            document.getElementById('devices-count').textContent = data.length;
        })
        .catch(error => {
            console.error('Erreur lors de la mise à jour des appareils:', error);
        });
}

// Scan des ports d'un appareil
function scanPorts(ip) {
    const modal = new bootstrap.Modal(document.getElementById('portScanModal'));
    const tbody = document.querySelector('#ports-table tbody');
    
    tbody.innerHTML = '<tr><td colspan="4" class="text-center"><i class="fa fa-spinner fa-spin"></i> Scan en cours...</td></tr>';
    modal.show();
    
    fetch(`/api/ports/${ip}`)
        .then(response => response.json())
        .then(data => {
            tbody.innerHTML = '';
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center">Aucun port ouvert trouvé</td></tr>';
                return;
            }
            
            data.forEach(port => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${port.port}</td>
                    <td>${port.service || 'Inconnu'}</td>
                    <td>${port.version || 'Inconnu'}</td>
                    <td>${port.protocol || 'tcp'}</td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(error => {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">Erreur: ${error.message}</td></tr>`;
        });
}

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    // Chargement initial des données
    refreshDevices();
    
    // Rafraîchissement périodique
    setInterval(refreshDevices, REFRESH_INTERVAL);
    
    // Event listeners
    document.getElementById('refreshButton').addEventListener('click', refreshDevices);
    document.getElementById('forceNetworkScan').addEventListener('click', () => {
        const button = document.getElementById('forceNetworkScan');
        button.disabled = true;
        button.innerHTML = '<i class="fa fa-refresh fa-spin"></i> Scan en cours...';
        
        fetch('/api/network/scan', { method: 'POST' })
            .then(response => response.json())
            .then(() => refreshDevices())
            .finally(() => {
                button.disabled = false;
                button.innerHTML = '<i class="fa fa-refresh"></i> Scanner';
            });
    });
    
    // Chargement de la version
    fetch('/api/version')
        .then(response => response.json())
        .then(data => {
            document.getElementById('version').textContent = data.version;
        });
    
    // Chargement du hostname
    fetch('/api/system')
        .then(response => response.json())
        .then(data => {
            document.getElementById('hostname').textContent = data.hostname;
        });
});
