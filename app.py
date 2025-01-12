import os
import json
import sqlite3
import logging
import threading
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import git
import sys
import signal
import psutil
import socket
import subprocess

# Chargement des variables d'environnement
load_dotenv()

# Configuration
VERSION = '3.2.0'
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

# Initialisation de Flask
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

def get_db():
    """Crée une connexion à la base de données"""
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialise la base de données"""
    try:
        with get_db() as db:
            db.execute('''
                CREATE TABLE IF NOT EXISTS wans (
                    client_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    ip TEXT NOT NULL,
                    subnet TEXT NOT NULL,
                    location TEXT NOT NULL,
                    hostname TEXT NOT NULL,
                    status TEXT DEFAULT 'offline',
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    latency REAL,
                    cpu_load REAL
                )
            ''')
            
            db.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wan_id TEXT NOT NULL,
                    mac TEXT NOT NULL,
                    ip TEXT NOT NULL,
                    hostname TEXT,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    open_ports TEXT,
                    FOREIGN KEY (wan_id) REFERENCES wans (client_id)
                )
            ''')
            db.commit()
            logger.info("Base de données initialisée avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de la base de données: {str(e)}")
        raise

def get_server_ip():
    """Récupère l'IP du serveur"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return 'localhost'

# Routes principales
@app.route('/')
def index():
    """Page d'accueil"""
    with get_db() as db:
        wans = db.execute('SELECT * FROM wans').fetchall()
        return render_template('index.html', wans=wans, server_ip=get_server_ip())

@app.route('/changelog')
def changelog():
    """Affiche les notes de version"""
    try:
        changelog_path = os.path.join(os.path.dirname(__file__), 'changelog.json')
        if not os.path.exists(changelog_path):
            return render_template('error.html', message='Notes de version introuvables')
        
        with open(changelog_path, 'r', encoding='utf-8') as f:
            changelog = json.load(f)
        return render_template('changelog.html', changelog=changelog)
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du changelog: {str(e)}")
        return render_template('error.html', message='Erreur lors de la lecture des notes de version')

@app.route('/wan/<client_id>')
def wan_devices(client_id):
    """Affiche les appareils d'un WAN"""
    with get_db() as db:
        wan = db.execute('SELECT * FROM wans WHERE client_id = ?', (client_id,)).fetchone()
        if not wan:
            return "WAN non trouvé", 404
            
        devices = db.execute('SELECT * FROM devices WHERE wan_id = ?', (client_id,)).fetchall()
        return render_template('devices.html', wan=wan, devices=devices)

# Routes API
@app.route('/api/wans')
def get_wans():
    """Récupère la liste des WANs"""
    try:
        with get_db() as db:
            wans = db.execute('SELECT * FROM wans').fetchall()
            return jsonify([dict(wan) for wan in wans])
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des WANs: {str(e)}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/wans/<client_id>')
def get_wan(client_id):
    """Récupère les détails d'un WAN"""
    try:
        with get_db() as db:
            wan = db.execute('SELECT * FROM wans WHERE client_id = ?', (client_id,)).fetchone()
            if not wan:
                return jsonify({'error': 'WAN non trouvé'}), 404
            return jsonify(dict(wan))
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du WAN: {str(e)}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/wans/<client_id>', methods=['DELETE'])
def delete_wan(client_id):
    """Supprime un WAN"""
    try:
        with get_db() as db:
            db.execute('DELETE FROM devices WHERE wan_id = ?', (client_id,))
            db.execute('DELETE FROM wans WHERE client_id = ?', (client_id,))
            db.commit()
            return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du WAN: {str(e)}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/register', methods=['POST'])
def register_wan():
    """Enregistre un nouveau WAN"""
    try:
        data = request.json
        if not data:
            logger.error("Aucune donnée JSON reçue")
            return jsonify({'error': 'Données JSON manquantes'}), 400

        required_fields = ['client_id', 'name', 'ip', 'subnet', 'location', 'hostname']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.error(f"Champs manquants : {', '.join(missing_fields)}")
            return jsonify({'error': f'Champs manquants : {", ".join(missing_fields)}'}), 400
            
        try:
            with get_db() as db:
                # Vérifie si le WAN existe déjà
                existing = db.execute('SELECT client_id FROM wans WHERE client_id = ?', 
                                   (data['client_id'],)).fetchone()
                
                if existing:
                    logger.info(f"Mise à jour du WAN existant : {data['client_id']}")
                else:
                    logger.info(f"Création d'un nouveau WAN : {data['client_id']}")
                
                # Mise à jour ou insertion du WAN
                db.execute('''
                    INSERT OR REPLACE INTO wans 
                    (client_id, name, ip, subnet, location, hostname, status, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, 'online', datetime('now'))
                ''', (data['client_id'], data['name'], data['ip'], 
                      data['subnet'], data['location'], data['hostname']))
                db.commit()
                
            return jsonify({'success': True})
        except sqlite3.Error as e:
            logger.error(f"Erreur SQLite lors de l'enregistrement du WAN: {str(e)}")
            return jsonify({'error': 'Erreur de base de données'}), 500
            
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement du WAN: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/devices/update', methods=['POST'])
def update_devices():
    """Met à jour les appareils d'un WAN"""
    try:
        data = request.json
        if not data or 'client_id' not in data:
            return jsonify({'error': 'Données manquantes'}), 400
            
        with get_db() as db:
            # Met à jour les statistiques du WAN
            if 'network_stats' in data:
                stats = data['network_stats']
                db.execute('''
                    UPDATE wans 
                    SET latency = ?, cpu_load = ?, last_seen = datetime('now')
                    WHERE client_id = ?
                ''', (stats.get('latency'), stats.get('cpu_load'), data['client_id']))
            
            # Supprime les anciens appareils
            db.execute('DELETE FROM devices WHERE wan_id = ?', (data['client_id'],))
            
            # Ajoute les nouveaux appareils
            for device in data.get('devices', []):
                db.execute('''
                    INSERT INTO devices (wan_id, mac, ip, hostname, open_ports)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    data['client_id'],
                    device['mac'],
                    device['ip'],
                    device['hostname'],
                    json.dumps(device.get('open_ports', []))
                ))
            
            db.commit()
            return jsonify({'success': True})
            
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des appareils: {str(e)}")
        return jsonify({'error': str(e)}), 500

def get_devices(client_id):
    """Récupère les appareils d'un WAN"""
    with get_db() as db:
        devices = db.execute('''
            SELECT * FROM devices 
            WHERE client_id = ?
            ORDER BY ip
        ''', (client_id,)).fetchall()
        return [dict(device) for device in devices]

@app.context_processor
def utility_processor():
    return dict(get_devices=get_devices)

def update_wan_status():
    """Met à jour le statut des WANs"""
    while True:
        try:
            with get_db() as db:
                # Marquer comme hors ligne les WANs qui n'ont pas été vus depuis 10 secondes
                db.execute('''
                    UPDATE wans 
                    SET status = 'offline' 
                    WHERE datetime('now', '-10 seconds') > last_seen
                ''')
                db.commit()
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des statuts: {str(e)}")
        time.sleep(5)  # Vérification toutes les 5 secondes

def kill_process_on_port(port):
    """Tue le processus qui utilise un port spécifique"""
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            # Vérifie les connexions de chaque processus
            for conn in proc.connections():
                if conn.laddr.port == port:
                    logging.info(f"Processus trouvé sur le port {port}: {proc.pid}")
                    try:
                        # Tue le processus avec SIGTERM
                        os.kill(proc.pid, signal.SIGTERM)
                        # Attend que le processus se termine
                        time.sleep(2)
                        # Vérifie si le processus est toujours en vie
                        if psutil.pid_exists(proc.pid):
                            # Force la fermeture avec SIGKILL si nécessaire
                            logging.info(f"Le processus {proc.pid} ne répond pas, utilisation de SIGKILL")
                            os.kill(proc.pid, signal.SIGKILL)
                        return True
                    except Exception as e:
                        logging.error(f"Erreur lors de la tentative de kill du processus {proc.pid}: {str(e)}")
                        return False
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def restart_server():
    """Redémarre le serveur Flask"""
    logging.info("Redémarrage du serveur...")
    if kill_process_on_port(5000):
        logging.info("Ancien processus terminé, redémarrage...")
        subprocess.Popen([sys.executable, __file__])
        sys.exit(0)
    else:
        logging.error("Impossible de tuer l'ancien processus")

def check_for_updates():
    """Vérifie les mises à jour GitHub toutes les 5 minutes"""
    try:
        repo = git.Repo('.')
        while True:
            try:
                # Fetch les dernières modifications
                repo.remotes.origin.fetch()
                
                # Récupère le dernier commit distant
                remote_commit = repo.refs['origin/main'].commit.hexsha
                current_commit = repo.head.commit.hexsha
                
                # Compare avec le commit local
                if remote_commit != current_commit:
                    logging.info("Nouvelles modifications détectées!")
                    
                    # Pull les changements
                    repo.remotes.origin.pull()
                    logging.info("Modifications téléchargées avec succès")
                    
                    # Redémarre le serveur
                    restart_server()
                else:
                    logging.info("Aucune nouvelle modification")
                    
            except Exception as e:
                logging.error(f"Erreur lors de la vérification des mises à jour: {str(e)}")
                
            time.sleep(300)  # Attend 5 minutes
            
    except Exception as e:
        logging.error(f"Erreur dans la boucle d'auto-update: {str(e)}")

@app.context_processor
def inject_version():
    """Injecte la version dans tous les templates"""
    return {'version': VERSION}

if __name__ == '__main__':
    # Initialisation
    init_db()
    
    # Démarre le thread de mise à jour des statuts
    status_thread = threading.Thread(target=update_wan_status, daemon=True)
    status_thread.start()
    
    # Démarre le thread d'auto-update
    update_thread = threading.Thread(target=check_for_updates)
    update_thread.daemon = True
    update_thread.start()
    
    # Démarre l'application Flask
    app.run(host='0.0.0.0', port=5000, debug=False)
