import time
from collections import deque
from statistics import mean
from ping3 import ping
from datetime import datetime, timedelta

class NetworkMonitor:
    def __init__(self):
        self.ping_history = {}  # Historique des pings par WAN
        self.last_ping_time = {}  # Dernier temps de ping par WAN
        self.ping_interval = 60  # 1 minute
        self.history_size = 5  # Garder 5 minutes d'historique

    def ping_host(self, host="8.8.8.8"):
        """Ping un hôte et retourne la latence en ms."""
        try:
            latency = ping(host, timeout=2)
            if latency is not None:
                return round(latency * 1000)  # Conversion en ms
            return None
        except Exception:
            return None

    def check_latency(self, wan_id):
        """Vérifie la latence pour un WAN spécifique et met à jour l'historique."""
        current_time = time.time()
        
        # Initialiser l'historique si nécessaire
        if wan_id not in self.ping_history:
            self.ping_history[wan_id] = deque(maxlen=self.history_size)
            self.last_ping_time[wan_id] = 0

        # Vérifier si c'est le moment de faire un nouveau ping
        if current_time - self.last_ping_time.get(wan_id, 0) >= self.ping_interval:
            latency = self.ping_host()
            if latency is not None:
                self.ping_history[wan_id].append(latency)
                self.last_ping_time[wan_id] = current_time

        # Calculer la moyenne sur les 5 dernières minutes
        if self.ping_history[wan_id]:
            avg_latency = mean(self.ping_history[wan_id])
            status = self.get_latency_status(avg_latency)
            return {
                'current': list(self.ping_history[wan_id])[-1] if self.ping_history[wan_id] else None,
                'average': round(avg_latency, 2),
                'status': status,
                'history': list(self.ping_history[wan_id])
            }
        return {
            'current': None,
            'average': None,
            'status': 'error',
            'history': []
        }

    def get_latency_status(self, latency):
        """Détermine le statut basé sur la latence."""
        if latency >= 200:
            return 'danger'
        elif latency >= 100:
            return 'warning'
        return 'success'

    def get_all_latencies(self):
        """Retourne toutes les latences pour tous les WANs."""
        return {wan_id: self.check_latency(wan_id) for wan_id in self.ping_history.keys()}
