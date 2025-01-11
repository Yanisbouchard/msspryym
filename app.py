import os
import json
import sqlite3
import logging
import threading
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Configuration
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
    with get_db() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS wans (
                client_id TEXT PRIMARY KEY,
                name TEXT,
                ip TEXT,
                subnet TEXT,
                location TEXT,
                status TEXT DEFAULT 'offline',
                last_seen TIMESTAMP,
                latency REAL
            );

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
            );
        ''')

# Routes principales
@app.route('/')
def index():
    """Page d'accueil"""
    try:
        server_ip = request.host.split(':')[0]
        return render_template('index.html', server_ip=server_ip)
    except Exception as e:
        logger.error(f"Erreur lors du chargement de l'index: {str(e)}")
        return render_template('error.html', message='Erreur serveur')

@app.route('/changelog')
def changelog():
    """Affiche les notes de version"""
    try:
        changelog_path = os.path.join(os.path.dirname(__file__), 'changelog.json')
        if not os.path.exists(changelog_path):
            return render_template('error.html', message='Notes de version introuvables')
        
        with open(changelog_path, 'r', encoding='utf-8') as f:
            changelog = json.load(f)
        return render_template('changelog.html', changelog=changelog, version=VERSION)
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du changelog: {str(e)}")
        return render_template('error.html', message='Erreur lors de la lecture des notes de version')

@app.route('/wan/<client_id>')
def wan_devices(client_id):
    """Affiche les appareils d'un WAN"""
    try:
        with get_db() as db:
            cursor = db.execute('SELECT * FROM wans WHERE client_id = ?', (client_id,))
            wan = cursor.fetchone()
            if not wan:
                return render_template('error.html', message='WAN non trouvé')
            
            cursor = db.execute('SELECT * FROM devices WHERE wan_id = ?', (client_id,))
            devices = cursor.fetchall()
            
            return render_template('devices.html', wan=dict(wan), devices=[dict(d) for d in devices])
    except Exception as e:
        logger.error(f"Erreur lors de l'affichage des appareils: {str(e)}")
        return render_template('error.html', message='Erreur lors de la récupération des appareils')

# Routes API
@app.route('/api/wans', methods=['GET'])
def get_wans():
    """Récupère la liste des WANs"""
    try:
        with get_db() as db:
            cursor = db.execute('''
                SELECT client_id, name, location, ip, subnet, status, last_seen, latency
                FROM wans ORDER BY name
            ''')
            return jsonify([dict(row) for row in cursor.fetchall()])
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des WANs: {str(e)}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/wans/<client_id>', methods=['GET'])
def get_wan(client_id):
    """Récupère les détails d'un WAN"""
    try:
        with get_db() as db:
            cursor = db.execute('SELECT * FROM wans WHERE client_id = ?', (client_id,))
            wan = cursor.fetchone()
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
        required_fields = ['client_id', 'name', 'ip', 'subnet', 'location']
        
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Données manquantes'}), 400
            
        with get_db() as db:
            db.execute('''
                INSERT OR REPLACE INTO wans 
                (client_id, name, ip, subnet, location, status, last_seen)
                VALUES (?, ?, ?, ?, ?, 'online', datetime('now'))
            ''', (data['client_id'], data['name'], data['ip'], 
                  data['subnet'], data['location']))
            db.commit()
            
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement du WAN: {str(e)}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/devices/update', methods=['POST'])
def update_devices():
    """Met à jour les appareils d'un WAN"""
    try:
        data = request.json
        if not data or 'wan_id' not in data or 'devices' not in data:
            return jsonify({'error': 'Données manquantes'}), 400
            
        with get_db() as db:
            # Mettre à jour le statut du WAN
            db.execute('''
                UPDATE wans 
                SET status = 'online', last_seen = datetime('now')
                WHERE client_id = ?
            ''', (data['wan_id'],))
            
            # Supprimer les anciens appareils
            db.execute('DELETE FROM devices WHERE wan_id = ?', (data['wan_id'],))
            
            # Ajouter les nouveaux appareils
            for device in data['devices']:
                db.execute('''
                    INSERT INTO devices 
                    (wan_id, ip, hostname, mac, vendor, status, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (data['wan_id'], device['ip'], device.get('hostname', 'Unknown'), 
                      device.get('mac', 'Unknown'), device.get('vendor', 'Unknown'), 
                      device.get('status', 'unknown')))
            db.commit()
            
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des appareils: {str(e)}")
        return jsonify({'error': 'Erreur serveur'}), 500

def update_wan_status():
    """Met à jour le statut des WANs"""
    while True:
        try:
            with get_db() as db:
                # Marquer comme hors ligne les WANs qui n'ont pas été vus depuis 2 minutes
                db.execute('''
                    UPDATE wans 
                    SET status = 'offline' 
                    WHERE datetime('now', '-120 seconds') > last_seen
                ''')
                db.commit()
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des statuts: {str(e)}")
        time.sleep(10)

@app.context_processor
def inject_version():
    """Injecte la version dans tous les templates"""
    return {'version': VERSION}

if __name__ == '__main__':
    # Initialisation
    init_db()
    
    # Démarrage du thread de mise à jour des statuts
    status_thread = threading.Thread(target=update_wan_status, daemon=True)
    status_thread.start()
    
    # Démarrage du serveur
    app.run(host='0.0.0.0', port=5000, debug=True)
