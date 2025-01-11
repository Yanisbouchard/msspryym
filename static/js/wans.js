// Gestionnaire des WANs
class WANManager {
    constructor() {
        this.updateInterval = 60000; // 1 minute
        this.startUpdates();
    }

    createWANCard(wan) {
        const statusClass = this.getStatusClass(wan.latency_status);
        const card = document.createElement('div');
        card.className = 'col-md-4 mb-4';
        card.innerHTML = `
            <div class="card wan-card">
                <div class="card-header bg-primary text-white">
                    <h5 class="card-title mb-0">
                        ${wan.name}
                        <span class="badge ${statusClass} float-end">
                            ${wan.latency ? wan.latency + ' ms' : 'N/A'}
                        </span>
                    </h5>
                </div>
                <div class="card-body">
                    <p class="card-text">
                        <strong>Location:</strong> ${wan.location}<br>
                        <strong>IP:</strong> ${wan.ip}<br>
                        <strong>Latence moyenne:</strong> 
                        <span class="${statusClass}">
                            ${wan.avg_latency ? wan.avg_latency + ' ms' : 'N/A'}
                        </span>
                    </p>
                    <a href="/wan/${wan.id}" class="btn btn-primary w-100">
                        <i class="fa fa-network-wired"></i> Voir les appareils connectés
                    </a>
                </div>
            </div>
        `;
        return card;
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

    updateWANCard(wan) {
        const card = document.querySelector(`[data-wan-id="${wan.id}"]`);
        if (!card) return;

        const statusBadge = card.querySelector('.badge');
        const avgLatencySpan = card.querySelector('.card-text span');
        
        statusBadge.className = `badge ${this.getStatusClass(wan.latency_status)} float-end`;
        statusBadge.textContent = wan.latency ? `${wan.latency} ms` : 'N/A';
        
        avgLatencySpan.className = this.getStatusClass(wan.latency_status);
        avgLatencySpan.textContent = wan.avg_latency ? `${wan.avg_latency} ms` : 'N/A';
    }

    async updateWANs() {
        try {
            const response = await fetch('/api/wans');
            if (!response.ok) throw new Error('Erreur réseau');
            
            const wans = await response.json();
            const container = document.getElementById('wans-container');
            
            // Première mise à jour
            if (container.children.length === 0) {
                wans.forEach(wan => {
                    const card = this.createWANCard(wan);
                    card.querySelector('.wan-card').setAttribute('data-wan-id', wan.id);
                    container.appendChild(card);
                });
            }
            // Mises à jour suivantes
            else {
                wans.forEach(wan => this.updateWANCard(wan));
            }
        } catch (error) {
            console.error('Erreur lors de la mise à jour des WANs:', error);
        }
    }

    startUpdates() {
        this.updateWANs();
        setInterval(() => this.updateWANs(), this.updateInterval);
    }
}

// Création et démarrage du gestionnaire
const wanManager = new WANManager();
document.addEventListener('DOMContentLoaded', () => {
    wanManager.startUpdates();
});
