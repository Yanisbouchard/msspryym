function refreshDashboard() {
    fetch('/api/dashboard')
        .then(response => response.json())
        .then(data => {
            // Mise à jour des informations système
            document.getElementById('hostname').textContent = data.system_info.hostname;
            document.getElementById('ip_address').textContent = data.system_info.ip_address;
            document.getElementById('os').textContent = data.system_info.os;
            
            // Mise à jour des statistiques réseau
            document.getElementById('connected_devices_count').textContent = data.connected_devices_count;
            document.getElementById('wan_latency').textContent = data.wan_latency.toFixed(2);
            document.getElementById('version').textContent = 'v' + data.version;
            
            // Mise à jour de la table des résultats du scan
            const tableBody = document.getElementById('network_scan_results');
            tableBody.innerHTML = '';
            
            data.connected_devices.forEach(device => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${device.ip}</td>
                    <td><span class="badge bg-${device.status === 'up' ? 'success' : 'danger'}">${device.status}</span></td>
                `;
                tableBody.appendChild(row);
            });
        })
        .catch(error => console.error('Erreur lors de la récupération des données:', error));
}

// Rafraîchir le tableau de bord au chargement de la page
document.addEventListener('DOMContentLoaded', refreshDashboard);

// Rafraîchir automatiquement toutes les 30 secondes
setInterval(refreshDashboard, 30000);
