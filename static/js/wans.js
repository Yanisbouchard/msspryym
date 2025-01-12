class WANManager {
    constructor() {
        this.refreshInterval = 20000; // 20 secondes
        this.initEventListeners();
        this.startAutoRefresh();
    }

    initEventListeners() {
        // Bouton de rafraîchissement
        document.getElementById('refreshWANs').addEventListener('click', () => {
            this.refreshWANs();
        });

        // Délégation d'événements pour les boutons de suppression
        document.addEventListener('click', (e) => {
            if (e.target.closest('.delete-wan')) {
                const button = e.target.closest('.delete-wan');
                const wanId = button.dataset.wanId;
                const deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
                
                // Stocker l'ID du WAN à supprimer
                document.getElementById('confirmDelete').dataset.wanId = wanId;
                
                // Afficher la modal
                deleteModal.show();
            }
        });

        // Confirmation de suppression
        document.getElementById('confirmDelete').addEventListener('click', (e) => {
            const wanId = e.target.dataset.wanId;
            this.deleteWAN(wanId);
            
            // Fermer la modal
            const deleteModal = bootstrap.Modal.getInstance(document.getElementById('deleteModal'));
            deleteModal.hide();
        });

        // Mise à jour de la commande quand on tape
        document.getElementById('wanName').addEventListener('input', updateCommand);
        document.getElementById('wanLocation').addEventListener('input', updateCommand);
    }

    async deleteWAN(wanId) {
        try {
            const response = await fetch(`/api/wans/${wanId}`, {
                method: 'DELETE'
            });

            if (!response.ok) throw new Error('Erreur réseau');

            // Rafraîchir la liste des WANs
            this.refreshWANs();
        } catch (error) {
            console.error('Erreur lors de la suppression du WAN:', error);
            alert('Erreur lors de la suppression du WAN');
        }
    }

    async refreshWANs() {
        try {
            const response = await fetch('/api/wans');
            if (!response.ok) throw new Error('Erreur réseau');
            
            const wans = await response.json();
            const container = document.getElementById('wans-container');
            container.innerHTML = '';
            
            wans.forEach(wan => {
                const col = document.createElement('div');
                col.className = 'col-md-6 mb-4';
                col.innerHTML = `
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5 class="card-title mb-0">${wan.name}</h5>
                            <span class="badge bg-${wan.status === 'online' ? 'success' : 'danger'}">
                                ${wan.status === 'online' ? 'ON' : 'OFF'}
                            </span>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <p><strong>Location:</strong> ${wan.location}</p>
                                </div>
                                <div class="col-md-6">
                                    <p><strong>IP:</strong> ${wan.ip}</p>
                                </div>
                            </div>
                            <div class="mt-3">
                                <a href="/wan/${wan.client_id}" class="btn btn-primary">
                                    <i class="fas fa-desktop"></i> Voir les appareils
                                </a>
                                <button class="btn btn-danger delete-wan" data-wan-id="${wan.client_id}">
                                    <i class="fas fa-trash"></i> Supprimer
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(col);
            });
        } catch (error) {
            console.error('Erreur lors du rafraîchissement des WANs:', error);
        }
    }

    startAutoRefresh() {
        // Rafraîchissement initial
        this.refreshWANs();
        
        // Rafraîchissement automatique
        setInterval(() => {
            this.refreshWANs();
        }, this.refreshInterval);
        
        // Actualisation automatique des statuts
        setInterval(() => {
            document.querySelectorAll('[id^="status-"]').forEach(statusBadge => {
                const clientId = statusBadge.id.replace('status-', '');
                fetch(`/api/wans/${clientId}`)
                    .then(response => response.json())
                    .then(data => {
                        // Met à jour le badge de statut
                        statusBadge.className = `badge ${data.status === 'online' ? 'bg-success' : 'bg-danger'}`;
                        statusBadge.textContent = data.status.toUpperCase();
                        
                        // Met à jour la latence
                        const latencyBadge = document.getElementById(`latency-${clientId}`);
                        if (latencyBadge) {
                            const latency = data.latency;
                            let color = 'gray';
                            if (latency !== null) {
                                if (latency <= 100) color = '#28a745';
                                else if (latency <= 200) color = '#ffc107';
                                else color = '#dc3545';
                                latencyBadge.textContent = `${Math.round(latency)} ms`;
                            } else {
                                latencyBadge.textContent = 'N/A';
                            }
                            latencyBadge.style.backgroundColor = color;
                        }
                        
                        // Met à jour la charge CPU
                        const cpuBadge = document.getElementById(`cpu-${clientId}`);
                        if (cpuBadge) {
                            const cpu = data.cpu_load;
                            let color = 'gray';
                            if (cpu !== null) {
                                if (cpu <= 40) color = '#28a745';
                                else if (cpu <= 70) color = '#ffc107';
                                else color = '#dc3545';
                                cpuBadge.textContent = `${Math.round(cpu)}%`;
                            } else {
                                cpuBadge.textContent = 'N/A';
                            }
                            cpuBadge.style.backgroundColor = color;
                        }
                    })
                    .catch(error => console.error('Erreur:', error));
            });
        }, 5000);
    }
}

// Mise à jour de la commande de déploiement
function updateCommand() {
    const name = document.getElementById('wanName').value || '[nom]';
    const location = document.getElementById('wanLocation').value || '[localisation]';
    const command = `python seahawks_client.py --server http://${serverIP}:5000 --name "${name}" --location "${location}"`;
    document.getElementById('deployCommand').textContent = command;
}

// Copie de la commande dans le presse-papier
function copyCommand() {
    const command = document.getElementById('deployCommand').textContent;
    navigator.clipboard.writeText(command).then(() => {
        alert('Commande copiée !');
    });
}

// Rafraîchissement de la liste des appareils
function refreshDevices(clientId) {
    fetch(`/api/wans/${clientId}/devices`)
        .then(response => response.text())
        .then(html => {
            document.getElementById(`devices-${clientId}`).innerHTML = html;
        })
        .catch(error => {
            console.error('Erreur:', error);
        });
}

// Suppression d'un WAN
function deleteWAN(clientId) {
    if (confirm('Êtes-vous sûr de vouloir supprimer ce WAN ?')) {
        fetch(`/api/wans/${clientId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Erreur lors de la suppression');
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            alert('Erreur lors de la suppression');
        });
    }
}

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    new WANManager();
});
