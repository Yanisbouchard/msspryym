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
                                <a href="/wans/${wan.client_id}" class="btn btn-primary">
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
    }
}

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    new WANManager();
});
