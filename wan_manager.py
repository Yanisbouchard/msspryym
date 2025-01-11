"""
Gestion des WANs (VMs clientes)
"""
import json
import time
import threading
from datetime import datetime, timedelta
import sqlite3
import os

class WANManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.db_path = 'wans.db'
        self._init_db()
        
    def _init_db(self):
        """Initialise la base de données SQLite"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            
            # Table des WANs
            c.execute('''
                CREATE TABLE IF NOT EXISTS wans (
                    client_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    location TEXT NOT NULL,
                    hostname TEXT NOT NULL,
                    ip TEXT NOT NULL,
                    subnet TEXT NOT NULL,
                    last_seen TIMESTAMP,
                    status TEXT DEFAULT 'offline'
                )
            ''')
            
            # Table des mesures de latence
            c.execute('''
                CREATE TABLE IF NOT EXISTS latency_history (
                    client_id TEXT,
                    timestamp TIMESTAMP,
                    latency REAL,
                    PRIMARY KEY (client_id, timestamp),
                    FOREIGN KEY (client_id) REFERENCES wans (client_id)
                )
            ''')
            
            # Table des appareils connectés
            c.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    client_id TEXT,
                    ip TEXT,
                    hostname TEXT,
                    mac TEXT,
                    vendor TEXT,
                    status TEXT,
                    last_seen TIMESTAMP,
                    PRIMARY KEY (client_id, ip),
                    FOREIGN KEY (client_id) REFERENCES wans (client_id)
                )
            ''')
            
            conn.commit()
    
    def register_wan(self, data):
        """Enregistre un nouveau WAN ou met à jour ses informations"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            
            c.execute('''
                INSERT OR REPLACE INTO wans 
                (client_id, name, location, hostname, ip, subnet, last_seen, status)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'), 'online')
            ''', (
                data['client_id'],
                data['name'],
                data['location'],
                data['hostname'],
                data['ip'],
                data['subnet']
            ))
            
            conn.commit()
            return True
    
    def update_wan_status(self, data):
        """Met à jour le statut d'un WAN"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            
            # Mise à jour du timestamp
            c.execute('''
                UPDATE wans 
                SET last_seen = datetime('now'), status = 'online'
                WHERE client_id = ?
            ''', (data['client_id'],))
            
            # Ajout de la mesure de latence
            if data['latency'] is not None:
                c.execute('''
                    INSERT INTO latency_history (client_id, timestamp, latency)
                    VALUES (?, datetime('now'), ?)
                ''', (data['client_id'], data['latency']))
            
            # Mise à jour des appareils
            c.execute('DELETE FROM devices WHERE client_id = ?', (data['client_id'],))
            for device in data['devices']:
                c.execute('''
                    INSERT INTO devices 
                    (client_id, ip, hostname, mac, vendor, status, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (
                    data['client_id'],
                    device['ip'],
                    device['hostname'],
                    device['mac'],
                    device['vendor'],
                    device['status']
                ))
            
            conn.commit()
            return True
    
    def get_all_wans(self):
        """Retourne tous les WANs avec leurs données de latence"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Marquer les WANs inactifs (pas de mise à jour depuis 5 minutes)
            c.execute('''
                UPDATE wans
                SET status = 'offline'
                WHERE last_seen < datetime('now', '-5 minutes')
            ''')
            
            # Récupérer tous les WANs
            c.execute('''
                SELECT w.*,
                       (SELECT latency 
                        FROM latency_history 
                        WHERE client_id = w.client_id 
                        ORDER BY timestamp DESC 
                        LIMIT 1) as current_latency,
                       (SELECT AVG(latency) 
                        FROM latency_history 
                        WHERE client_id = w.client_id 
                        AND timestamp > datetime('now', '-5 minutes')) as avg_latency
                FROM wans w
            ''')
            
            wans = []
            for row in c.fetchall():
                wan = dict(row)
                
                # Déterminer le statut de latence
                current_latency = wan['current_latency']
                if current_latency is not None:
                    if current_latency < 100:
                        latency_status = 'success'
                    elif current_latency < 200:
                        latency_status = 'warning'
                    else:
                        latency_status = 'danger'
                else:
                    latency_status = 'danger'
                
                wan['latency_status'] = latency_status
                wans.append(wan)
            
            return wans
    
    def get_wan(self, client_id):
        """Retourne les informations d'un WAN spécifique"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute('''
                SELECT w.*,
                       (SELECT latency 
                        FROM latency_history 
                        WHERE client_id = w.client_id 
                        ORDER BY timestamp DESC 
                        LIMIT 1) as current_latency,
                       (SELECT AVG(latency) 
                        FROM latency_history 
                        WHERE client_id = w.client_id 
                        AND timestamp > datetime('now', '-5 minutes')) as avg_latency
                FROM wans w
                WHERE client_id = ?
            ''', (client_id,))
            
            row = c.fetchone()
            if row:
                wan = dict(row)
                
                # Déterminer le statut de latence
                current_latency = wan['current_latency']
                if current_latency is not None:
                    if current_latency < 100:
                        latency_status = 'success'
                    elif current_latency < 200:
                        latency_status = 'warning'
                    else:
                        latency_status = 'danger'
                else:
                    latency_status = 'danger'
                
                wan['latency_status'] = latency_status
                return wan
            
            return None
    
    def get_wan_devices(self, client_id):
        """Retourne les appareils connectés à un WAN"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute('''
                SELECT * FROM devices
                WHERE client_id = ?
                ORDER BY ip
            ''', (client_id,))
            
            return [dict(row) for row in c.fetchall()]
    
    def cleanup_old_data(self):
        """Nettoie les anciennes données"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            
            # Supprimer les mesures de latence de plus de 24h
            c.execute('''
                DELETE FROM latency_history
                WHERE timestamp < datetime('now', '-1 day')
            ''')
            
            # Supprimer les appareils non vus depuis plus de 24h
            c.execute('''
                DELETE FROM devices
                WHERE last_seen < datetime('now', '-1 day')
            ''')
            
            conn.commit()
