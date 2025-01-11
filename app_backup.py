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
import requests
import logging
from functools import lru_cache, wraps
import sqlite3
from dotenv import load_dotenv
load_dotenv()

VERSION = '3.1.1'
DATABASE_PATH = os.getenv('DATABASE_PATH', 'wans.db')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'seahawks.log')

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

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

# Cache pour les WANs
@lru_cache(maxsize=128)
def get_cached_wan(client_id, timestamp=None):
    """Récupère un WAN du cache. Le timestamp permet d'invalider le cache toutes les 20 secondes."""
    return wan_manager.get_wan(client_id)

def get_wan_with_cache(client_id):
    """Wrapper pour récupérer un WAN avec cache de 20 secondes"""
    timestamp = datetime.now().replace(microsecond=0, second=datetime.now().second // 20 * 20)
    return get_cached_wan(client_id, timestamp)

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

def update_wans_status():
    """Met à jour le statut des WANs périodiquement"""
    while True:
        try:
            wan_manager.check_wans_status()
        except Exception as e:
            print(f"Erreur lors de la mise à jour des statuts: {str(e)}")
        time.sleep(10)  # Vérifier toutes les 10 secondes

def init_db():
    """Initialise la base de données"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        
        # Table des WANs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wans (
                client_id TEXT PRIMARY KEY,
                name TEXT,
                ip TEXT,
                subnet TEXT,
                location TEXT,
                status TEXT DEFAULT 'offline',
                last_seen TIMESTAMP,
                latency REAL
            )
        ''')
        
        # Table des appareils
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wan_id TEXT,
                ip TEXT,
                hostname TEXT,
                mac TEXT,
                vendor TEXT,
                status TEXT DEFAULT 'down',
                last_seen TIMESTAMP,
                FOREIGN KEY (wan_id) REFERENCES wans(client_id)
            )
        ''')
        
        conn.commit()

def get_db():
    """Crée une connexion à la base de données"""
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    return db

def db_operation(f):
    """Décorateur pour gérer les opérations de base de données"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            with get_db() as db:
                return f(db, *args, **kwargs)
        except Exception as e:
            print(f"Erreur de base de données: {str(e)}")
            return jsonify({'error': 'Erreur serveur'}), 500
    return decorated_function

@app.context_processor
def inject_version():
    """Injecte la version dans tous les templates"""
    return {'version': VERSION}

@app.route('/')
def index():
    """Page principale du dashboard"""
    server_ip = get_local_ip()
    changelog = get_changelog()
    return render_template('index.html', 
                         server_ip=server_ip,
                         current_version=changelog['current_version'])

@app.route('/wans/<client_id>')
def wan_devices(client_id):
    """Affiche les appareils d'un WAN"""
    try:
        with get_db() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Récupérer les informations du WAN
            cursor.execute('SELECT * FROM wans WHERE client_id = ?', (client_id,))
            wan = cursor.fetchone()
            
            if not wan:
                return render_template('error.html', message='WAN non trouvé')
            
            # Récupérer les appareils du WAN
            cursor.execute('SELECT * FROM devices WHERE wan_id = ?', (client_id,))
            devices = cursor.fetchall()
            
            return render_template('devices.html', 
                                 wan=dict(wan),
                                 devices=[dict(d) for d in devices])
                                 
    except Exception as e:
        print(f"Erreur lors de la récupération des appareils: {str(e)}")
        return render_template('error.html', message='Erreur lors de la récupération des appareils')

@app.route('/changelog')
def changelog():
    """Affiche les notes de version"""
    try:
        changelog_path = os.path.join(os.path.dirname(__file__), 'changelog.json')
        if not os.path.exists(changelog_path):
            return render_template('error.html', 
                                 message='Le fichier des notes de version est introuvable')
        
        with open(changelog_path, 'r', encoding='utf-8') as f:
            changelog = json.load(f)
            
        return render_template('changelog.html', changelog=changelog, version=VERSION)
    except Exception as e:
        print(f"Erreur lors de la lecture du changelog: {str(e)}")
        return render_template('error.html', 
                             message='Erreur lors de la lecture des notes de version')

@app.route('/api/devices')
def get_devices():
    """Récupère la liste des appareils d'un WAN"""
    try:
        wan_id = request.args.get('wan_id')
        if not wan_id:
            return jsonify({'error': 'WAN ID manquant'}), 400

        with get_db() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM devices 
                WHERE wan_id = ?
                ORDER BY hostname
            ''', (wan_id,))
            
            devices = [dict(row) for row in cursor.fetchall()]
            return jsonify(devices)
            
    except Exception as e:
        print(f"Erreur lors de la récupération des appareils: {str(e)}")
        return jsonify({'error': 'Erreur serveur'}), 500

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

@app.route('/api/wans', methods=['GET'])
@db_operation
def get_wans(db):
    """Récupère la liste des WANs"""
    cursor = db.execute('''
        SELECT client_id, name, location, ip, subnet, status, last_seen, latency
        FROM wans ORDER BY name
    ''')
    return jsonify([dict(row) for row in cursor.fetchall()])

@app.route('/api/wans/<client_id>', methods=['GET'])
@db_operation
def get_wan(db, client_id):
    """Récupère les détails d'un WAN"""
    cursor = db.execute('SELECT * FROM wans WHERE client_id = ?', (client_id,))
    wan = cursor.fetchone()
    if not wan:
        return jsonify({'error': 'WAN non trouvé'}), 404
    return jsonify(dict(wan))

@app.route('/api/wans/<client_id>', methods=['DELETE'])
@db_operation
def delete_wan(db, client_id):
    """Supprime un WAN"""
    db.execute('DELETE FROM devices WHERE wan_id = ?', (client_id,))
    db.execute('DELETE FROM wans WHERE client_id = ?', (client_id,))
    return jsonify({'success': True})

@app.route('/api/wans/<client_id>/devices', methods=['GET'])
@db_operation
def get_wan_devices(db, client_id):
    """Récupère les appareils d'un WAN"""
    cursor = db.execute('''
        SELECT * FROM devices 
        WHERE wan_id = ? 
        ORDER BY hostname
    ''', (client_id,))
    return jsonify([dict(row) for row in cursor.fetchall()])

@app.route('/api/register', methods=['POST'])
@db_operation
def register_wan(db):
    """Enregistre un nouveau WAN"""
    data = request.json
    required_fields = ['client_id', 'name', 'ip', 'subnet', 'location']
    
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Données manquantes'}), 400
        
    db.execute('''
        INSERT OR REPLACE INTO wans 
        (client_id, name, ip, subnet, location, status, last_seen)
        VALUES (?, ?, ?, ?, ?, 'online', datetime('now'))
    ''', (data['client_id'], data['name'], data['ip'], data['subnet'], data['location']))
    
    return jsonify({'success': True})

@app.route('/api/devices/update', methods=['POST'])
@db_operation
def update_devices(db):
    """Met à jour les appareils d'un WAN"""
    data = request.json
    if not data or 'wan_id' not in data or 'devices' not in data:
        return jsonify({'error': 'Données manquantes'}), 400
        
    # Supprimer les anciens appareils
    db.execute('DELETE FROM devices WHERE wan_id = ?', (data['wan_id'],))
    
    # Ajouter les nouveaux appareils
    for device in data['devices']:
        db.execute('''
            INSERT INTO devices 
            (wan_id, ip, hostname, mac, vendor, status, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ''', (data['wan_id'], device['ip'], device['hostname'], 
              device.get('mac'), device.get('vendor'), device.get('status', 'unknown')))
    
    return jsonify({'success': True})

def update_wan_status():
    """Met à jour le statut des WANs"""
    while True:
        try:
            with get_db() as db:
                # Marquer comme hors ligne les WANs qui n'ont pas été vus depuis 30 secondes
                db.execute('''
                    UPDATE wans 
                    SET status = 'offline' 
                    WHERE datetime('now', '-30 seconds') > last_seen
                ''')
        except Exception as e:
            print(f"Erreur lors de la mise à jour des statuts: {str(e)}")
        time.sleep(10)

if __name__ == '__main__':
    # Initialisation de la base de données
    init_db()
    
    # Démarrage du thread de mise à jour du cache
    cache_thread = threading.Thread(target=update_cache, daemon=True)
    cache_thread.start()
    
    # Démarrage du thread de nettoyage
    cleanup_thread = threading.Thread(target=cleanup_thread, daemon=True)
    cleanup_thread.start()
    
    # Démarrage du thread de mise à jour des statuts
    status_thread = threading.Thread(target=update_wans_status, daemon=True)
    status_thread.start()
    
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
