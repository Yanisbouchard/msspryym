from flask import Flask, render_template, jsonify, request
import threading
from updater import AutoUpdater
from network_scanner import NetworkScanner
from system_info import SystemInfo
from network_monitor import NetworkMonitor
from version import get_version
from wan_manager import WANManager
import time
from datetime import datetime
import socket
import json
import os

app = Flask(__name__)

# Initialisation des classes
scanner = NetworkScanner()
system_info = SystemInfo()
network_monitor = NetworkMonitor()
wan_manager = WANManager()

# Cache pour les données
cache = {
    'devices': [],
    'system_info': {},
    'wan_latency': [],
    'version': get_version(),
    'last_update': 0,
    'cache_duration': 60  # Durée du cache en secondes
}

def get_local_ip():
    """Récupère l'IP locale du serveur"""
    try:
        # Crée une connexion temporaire pour obtenir l'IP locale
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '0.0.0.0'

def get_changelog():
    """Charge le changelog depuis le fichier"""
    try:
        with open('changelog.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur lors du chargement du changelog: {str(e)}")
        return {
            "current_version": "0.0.0",
            "versions": []
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

def cleanup_thread():
    """Thread pour nettoyer les anciennes données"""
    while True:
        wan_manager.cleanup_old_data()
        time.sleep(3600)  # Nettoyage toutes les heures

@app.route('/')
def index():
    """Page principale du dashboard"""
    server_ip = get_local_ip()
    changelog = get_changelog()
    return render_template('index.html', 
                         server_ip=server_ip,
                         current_version=changelog['current_version'])

@app.route('/changelog')
def changelog():
    return render_template('changelog.html', changelog=get_changelog())

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
    return jsonify({
        'cpu': {
            'usage': system_info.get_cpu_usage(),
            'per_core': system_info.get_per_core_usage()
        },
        'memory': system_info.get_memory_info(),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/network/scan', methods=['POST'])
def force_network_scan():
    """Force un nouveau scan du réseau"""
    try:
        devices = scanner.scan_network()
        # Mise à jour du cache
        cache['devices'] = devices
        cache['last_update'] = time.time()
        return jsonify(devices)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/version')
def get_version_info():
    """Retourne la version actuelle"""
    changelog = get_changelog()
    return jsonify({
        'version': changelog['current_version'],
        'changelog': changelog['versions']
    })

@app.route('/api/wans')
def get_wans():
    """Retourne la liste des WANs"""
    return jsonify(wan_manager.get_all_wans())

@app.route('/api/wans/<client_id>')
def get_wan(client_id):
    """Retourne les données d'un WAN spécifique"""
    wan = wan_manager.get_wan(client_id)
    if wan is None:
        return jsonify({'error': 'WAN non trouvé'}), 404
    return jsonify(wan)

@app.route('/api/wans/<client_id>/devices')
def get_wan_devices(client_id):
    """Retourne la liste des appareils connectés à un WAN"""
    wan = wan_manager.get_wan(client_id)
    if wan is None:
        return jsonify({'error': 'WAN non trouvé'}), 404
    return jsonify(wan_manager.get_wan_devices(client_id))

@app.route('/api/register', methods=['POST'])
def register_wan():
    """Enregistre un nouveau WAN"""
    data = request.get_json()
    if not data or not all(k in data for k in ('client_id', 'name', 'location', 'hostname', 'ip', 'subnet')):
        return jsonify({'error': 'Données manquantes'}), 400
        
    if wan_manager.register_wan(data):
        return jsonify({'success': True})
    return jsonify({'error': 'Erreur lors de l\'enregistrement'}), 500

@app.route('/api/update', methods=['POST'])
def update_wan():
    """Met à jour les données d'un WAN"""
    data = request.get_json()
    if not data or not all(k in data for k in ('client_id', 'timestamp', 'latency', 'devices')):
        return jsonify({'error': 'Données manquantes'}), 400
        
    if wan_manager.update_wan_status(data):
        return jsonify({'success': True})
    return jsonify({'error': 'Erreur lors de la mise à jour'}), 500

@app.route('/wan/<client_id>')
def wan_details(client_id):
    """Affiche les détails d'un WAN"""
    wan = wan_manager.get_wan(client_id)
    if wan is None:
        return "WAN non trouvé", 404
    changelog = get_changelog()
    return render_template('wan_details.html', 
                         wan=wan,
                         current_version=changelog['current_version'])

if __name__ == '__main__':
    # Démarrage du thread de mise à jour du cache
    cache_thread = threading.Thread(target=update_cache, daemon=True)
    cache_thread.start()
    
    # Démarrage du thread de nettoyage
    cleanup_thread = threading.Thread(target=cleanup_thread, daemon=True)
    cleanup_thread.start()
    
    # Démarrage de l'auto-updater
    updater = AutoUpdater()
    updater_thread = threading.Thread(target=updater.start, daemon=True)
    updater_thread.start()
    
    # Affichage de l'IP du serveur et de la version
    server_ip = get_local_ip()
    changelog = get_changelog()
    print(f"\nServeur démarré sur : http://{server_ip}:5000\n")
    print(f"Version actuelle : {changelog['current_version']}\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
