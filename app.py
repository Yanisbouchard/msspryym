from flask import Flask, render_template, jsonify, request
import threading
from updater import AutoUpdater
from network_scanner import NetworkScanner
from system_info import SystemInfo
from network_monitor import NetworkMonitor
import time
from datetime import datetime

app = Flask(__name__)

# Initialisation des classes
scanner = NetworkScanner()
system_info = SystemInfo()
network_monitor = NetworkMonitor()

# Cache pour les données
cache = {
    'devices': [],
    'system_info': {},
    'wan_latency': [],
    'last_update': 0,
    'cache_duration': 60  # Durée du cache en secondes
}

def update_cache():
    """Met à jour le cache en arrière-plan"""
    while True:
        try:
            current_time = time.time()
            if current_time - cache['last_update'] >= cache['cache_duration']:
                # Mise à jour des données
                cache['devices'] = scanner.scan_network()
                cache['system_info'] = system_info.get_system_info()
                cache['wan_latency'] = network_monitor.check_wan_connectivity()
                cache['last_update'] = current_time
        except Exception as e:
            print(f"Erreur lors de la mise à jour du cache: {str(e)}")
        time.sleep(10)  # Attente avant la prochaine vérification

@app.route('/')
def index():
    """Page principale du dashboard"""
    return render_template('index.html')

@app.route('/api/devices')
def get_devices():
    """API pour obtenir la liste des appareils"""
    return jsonify(cache['devices'])

@app.route('/api/system')
def get_system():
    """API pour obtenir les informations système"""
    return jsonify(cache['system_info'])

@app.route('/api/latency')
def get_latency():
    """API pour obtenir les informations de latence"""
    return jsonify(cache['wan_latency'])

@app.route('/api/ports/<ip>')
def get_ports(ip):
    """API pour scanner les ports d'une IP spécifique"""
    ports = scanner.scan_ports(ip)
    return jsonify(ports)

@app.route('/api/processes')
def get_processes():
    """API pour obtenir la liste des processus"""
    processes = system_info.get_process_info()
    return jsonify(processes)

@app.route('/api/system/realtime')
def get_realtime_system():
    """Récupère les informations système en temps réel"""
    system_info = SystemInfo()
    return jsonify({
        'cpu': {
            'usage': system_info.get_cpu_usage(),
            'per_core': system_info.get_per_core_usage()
        },
        'memory': {
            'total': system_info.get_memory_info()['total'],
            'used': system_info.get_memory_info()['used'],
            'percent': system_info.get_memory_info()['percent']
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/network/scan', methods=['POST'])
def force_network_scan():
    """Force un nouveau scan du réseau"""
    scanner = NetworkScanner()
    devices = scanner.scan_network()
    return jsonify(devices)

if __name__ == '__main__':
    # Démarrage de l'auto-updater dans un thread séparé
    updater = AutoUpdater()
    updater_thread = threading.Thread(target=updater.start, daemon=True)
    updater_thread.start()
    
    # Démarrage du thread de mise à jour du cache
    cache_thread = threading.Thread(target=update_cache, daemon=True)
    cache_thread.start()
    
    # Démarrage de l'application Flask
    app.run(host='0.0.0.0', port=5000, debug=True)
