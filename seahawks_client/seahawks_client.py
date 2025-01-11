"""
Client Seahawks pour les VMs déployées chez les franchises
"""
import requests
import time
import socket
import psutil
from network_scanner import NetworkScanner
from network_monitor import NetworkMonitor
import json
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('seahawks_client.log'),
        logging.StreamHandler()
    ]
)

class SeahawksClient:
    def __init__(self, wan_id, server_url, location):
        self.wan_id = wan_id
        self.server_url = server_url
        self.location = location
        self.scanner = NetworkScanner()
        self.network_monitor = NetworkMonitor()
        
        # Charger la configuration
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            logging.error("Fichier de configuration non trouvé")
            raise
    
    def get_system_info(self):
        """Récupère les informations système"""
        return {
            'cpu_usage': psutil.cpu_percent(),
            'ram_usage': psutil.virtual_memory().percent,
            'hostname': socket.gethostname(),
            'ip': self.scanner.get_local_ip()
        }
    
    def get_network_info(self):
        """Récupère les informations réseau"""
        devices = self.scanner.scan_network()
        latency = self.network_monitor.check_wan_latency()
        return {
            'devices': devices,
            'devices_count': len(devices),
            'latency': latency['average'] if latency else 0
        }
    
    def update_status(self):
        """Envoie une mise à jour au serveur"""
        try:
            data = {
                'name': f'Franchise {self.location}',
                'ip': self.scanner.get_local_ip(),
                'location': self.location,
                'status': 'online',
                'last_update': datetime.now().isoformat(),
                'system_info': self.get_system_info(),
                'network_info': self.get_network_info()
            }
            
            response = requests.post(
                f'{self.server_url}/api/wans/{self.wan_id}/update',
                json=data
            )
            
            if response.status_code == 200:
                logging.info("Mise à jour envoyée avec succès")
            else:
                logging.error(f"Erreur lors de la mise à jour: {response.status_code}")
                
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour: {str(e)}")
    
    def start(self):
        """Démarre le client"""
        logging.info(f"Démarrage du client Seahawks pour {self.location}")
        
        while True:
            self.update_status()
            time.sleep(self.config.get('update_interval', 300))  # 5 minutes par défaut

if __name__ == "__main__":
    # Configuration du client
    WAN_ID = "WAN_001"  # À configurer pour chaque franchise
    SERVER_URL = "http://serveur-central:5000"  # URL du serveur central
    LOCATION = "Paris"  # Localisation de la franchise
    
    client = SeahawksClient(WAN_ID, SERVER_URL, LOCATION)
    client.start()
