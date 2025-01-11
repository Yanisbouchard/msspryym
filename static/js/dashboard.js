// Configuration des intervalles de rafraîchissement
const REFRESH_INTERVAL = 300000; // 5 minutes (300000 ms)
let latencyChart = null;
let cpuChart = null;
let ramChart = null;
let portScanModal = null;

// Configuration des graphiques
const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    scales: {
        y: {
            beginAtZero: true,
            max: 100,
            ticks: {
                callback: value => value + '%'
            }
        },
        x: {
            ticks: {
                maxTicksLimit: 10
            }
        }
    }
};

// Fonction pour formater les octets en format lisible
function formatBytes(bytes) {
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 B';
    const i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
    return Math.round(bytes / Math.pow(1024, i), 2) + ' ' + sizes[i];
}

// Initialisation des graphiques
function initCharts() {
    const cpuCtx = document.getElementById('cpuChart').getContext('2d');
    const ramCtx = document.getElementById('ramChart').getContext('2d');

    cpuChart = new Chart(cpuCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'CPU Usage',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1,
                fill: true
            }]
        },
        options: chartOptions
    });

    ramChart = new Chart(ramCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'RAM Usage',
                data: [],
                borderColor: 'rgb(153, 102, 255)',
                tension: 0.1,
                fill: true
            }]
        },
        options: chartOptions
    });
}

// Fonction pour mettre à jour les graphiques
function updateCharts() {
    const button = document.getElementById('refreshButton');
    button.disabled = true;
    button.innerHTML = '<i class="fa fa-refresh fa-spin"></i> Actualisation...';

    fetch('/api/system/realtime')
        .then(response => response.json())
        .then(data => {
            const time = new Date(data.timestamp).toLocaleTimeString();
            
            // Mise à jour CPU
            cpuChart.data.labels.push(time);
            cpuChart.data.datasets[0].data.push(data.cpu.usage);
            if (cpuChart.data.labels.length > 30) {
                cpuChart.data.labels.shift();
                cpuChart.data.datasets[0].data.shift();
            }
            cpuChart.update();

            // Mise à jour RAM
            ramChart.data.labels.push(time);
            ramChart.data.datasets[0].data.push(data.memory.percent);
            if (ramChart.data.labels.length > 30) {
                ramChart.data.labels.shift();
                ramChart.data.datasets[0].data.shift();
            }
            ramChart.update();

            // Réactiver le bouton
            button.disabled = false;
            button.innerHTML = '<i class="fa fa-refresh"></i> Actualiser';
        });
}

// Fonction pour forcer un scan réseau
function forceNetworkScan() {
    const button = document.getElementById('forceNetworkScan');
    button.disabled = true;
    button.innerHTML = '<i class="fa fa-refresh fa-spin"></i> Scan en cours...';

    fetch('/api/network/scan', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            updateDevices();
            button.disabled = false;
            button.innerHTML = '<i class="fa fa-refresh"></i> Scanner';
        });
}

// Fonction pour mettre à jour les informations système
function updateSystemInfo() {
    fetch('/api/system')
        .then(response => response.json())
        .then(data => {
            const systemInfoHtml = `
                <div class="system-info-item">
                    <div class="system-info-label">Hostname</div>
                    <div>${data.hostname}</div>
                </div>
                <div class="system-info-item">
                    <div class="system-info-label">Système d'exploitation</div>
                    <div>${data.os.name} ${data.os.version}</div>
                </div>
                <div class="system-info-item">
                    <div class="system-info-label">CPU</div>
                    <div class="progress mb-2">
                        <div class="progress-bar" role="progressbar" style="width: ${data.cpu.usage}%">
                            ${data.cpu.usage}%
                        </div>
                    </div>
                    <small>${data.cpu.cores} cœurs @ ${data.cpu.frequency} MHz</small>
                </div>
                <div class="system-info-item">
                    <div class="system-info-label">Mémoire</div>
                    <div class="progress mb-2">
                        <div class="progress-bar" role="progressbar" style="width: ${data.memory.percent}%">
                            ${data.memory.percent}%
                        </div>
                    </div>
                    <small>${formatBytes(data.memory.used)} / ${formatBytes(data.memory.total)}</small>
                </div>
                <div class="system-info-item">
                    <div class="system-info-label">Uptime</div>
                    <div>${data.boot_time.uptime}</div>
                </div>
            `;
            document.getElementById('system-info').innerHTML = systemInfoHtml;
        });
}

// Fonction pour mettre à jour la latence réseau
function updateNetworkLatency() {
    fetch('/api/latency')
        .then(response => response.json())
        .then(data => {
            const labels = data.map(item => item.target);
            const values = data.map(item => item.avg);
            
            if (!latencyChart) {
                const ctx = document.createElement('canvas');
                document.getElementById('network-latency').innerHTML = '';
                document.getElementById('network-latency').appendChild(ctx);
                
                latencyChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Latence (ms)',
                            data: values,
                            borderColor: 'rgb(75, 192, 192)',
                            tension: 0.1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false
                    }
                });
            } else {
                latencyChart.data.labels = labels;
                latencyChart.data.datasets[0].data = values;
                latencyChart.update();
            }
        });
}

// Fonction pour mettre à jour la liste des appareils
function updateDevices() {
    fetch('/api/devices')
        .then(response => response.json())
        .then(devices => {
            const tbody = document.querySelector('#devices-table tbody');
            document.getElementById('devices-count').textContent = devices.length;
            
            tbody.innerHTML = devices.map(device => `
                <tr>
                    <td>${device.ip}</td>
                    <td>${device.hostname}</td>
                    <td>${device.mac}</td>
                    <td>${device.vendor}</td>
                    <td><span class="badge bg-success">${device.status}</span></td>
                    <td>
                        <button class="btn btn-primary btn-sm" onclick="scanPorts('${device.ip}')">
                            <i class="fa fa-search"></i> Scan Ports
                        </button>
                    </td>
                </tr>
            `).join('');
        });
}

// Fonction pour mettre à jour la liste des processus
function updateProcesses() {
    fetch('/api/processes')
        .then(response => response.json())
        .then(data => {
            const tbody = document.querySelector('#processes-table tbody');
            tbody.innerHTML = data.map(process => `
                <tr>
                    <td class="text-nowrap">${process.name}</td>
                    <td class="text-end">${process.cpu_percent.toFixed(1)}%</td>
                    <td class="text-end">${process.memory_percent.toFixed(1)}%</td>
                </tr>
            `).join('');
        });
}

// Fonction pour scanner les ports d'un appareil
function scanPorts(ip) {
    if (!portScanModal) {
        portScanModal = new bootstrap.Modal(document.getElementById('portScanModal'));
    }
    
    // Réinitialiser le contenu de la modal
    document.querySelector('#ports-table tbody').innerHTML = '<tr><td colspan="4" class="text-center">Scan en cours...</td></tr>';
    
    // Afficher la modal
    portScanModal.show();
    
    // Lancer le scan
    fetch(`/api/ports/${ip}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const tbody = document.querySelector('#ports-table tbody');
            if (!data || data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center">Aucun port ouvert trouvé</td></tr>';
            } else {
                tbody.innerHTML = data.map(port => `
                    <tr>
                        <td>${port.port}</td>
                        <td>${port.service || 'Inconnu'}</td>
                        <td>${port.version || 'Inconnu'}</td>
                        <td>${port.protocol || 'Inconnu'}</td>
                    </tr>
                `).join('');
            }
        })
        .catch(error => {
            document.querySelector('#ports-table tbody').innerHTML = 
                `<tr><td colspan="4" class="text-center text-danger">Erreur: ${error.message}</td></tr>`;
        });
}

// Initialisation et rafraîchissement périodique
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    updateCharts();
    updateSystemInfo();
    updateDevices();
    updateNetworkLatency();
    
    // Initialiser la modal
    portScanModal = new bootstrap.Modal(document.getElementById('portScanModal'));
    
    // Gestionnaires d'événements
    document.getElementById('refreshButton').addEventListener('click', updateCharts);
    document.getElementById('forceNetworkScan').addEventListener('click', forceNetworkScan);
    
    // Rafraîchissement périodique
    setInterval(() => {
        updateCharts();
        updateSystemInfo();
        updateDevices();
        updateNetworkLatency();
    }, REFRESH_INTERVAL);
});
