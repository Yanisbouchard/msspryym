"""
Script de déploiement du client Seahawks
"""
import argparse
import os
import shutil
import json
import subprocess
import sys
import uuid

def create_config(server_url, location):
    """Crée le fichier de configuration pour le client"""
    config = {
        "server_url": server_url,
        "update_interval": 300,  # 5 minutes
        "wan_id": str(uuid.uuid4()),  # Génère un ID unique pour ce WAN
        "location": location,
        "log_level": "INFO",
        "network_scan_interval": 300,
        "latency_check_targets": [
            "8.8.8.8",  # Google DNS
            "1.1.1.1"   # Cloudflare DNS
        ]
    }
    
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)
    
    return config

def setup_virtual_env():
    """Configure l'environnement virtuel Python"""
    if not os.path.exists('venv'):
        subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
    
    # Détermine le chemin du pip selon l'OS
    if os.name == 'nt':  # Windows
        pip_path = os.path.join('venv', 'Scripts', 'pip')
    else:  # Linux/Mac
        pip_path = os.path.join('venv', 'bin', 'pip')
    
    # Installation des dépendances
    subprocess.run([pip_path, 'install', '-r', 'requirements.txt'], check=True)

def create_service_file(location):
    """Crée les fichiers de service selon l'OS"""
    if os.name == 'nt':  # Windows
        service_content = f"""@echo off
call venv\\Scripts\\activate
python seahawks_client.py
"""
        with open('start_seahawks.bat', 'w') as f:
            f.write(service_content)
    else:  # Linux
        service_content = f"""[Unit]
Description=Seahawks Client Service - {location}
After=network.target

[Service]
Type=simple
User=seahawks
WorkingDirectory={os.getcwd()}
Environment=PATH={os.getcwd()}/venv/bin
ExecStart={os.getcwd()}/venv/bin/python seahawks_client.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
"""
        with open('seahawks.service', 'w') as f:
            f.write(service_content)

def create_requirements():
    """Crée le fichier requirements.txt"""
    requirements = """requests==2.31.0
psutil==5.9.5
python-nmap==0.7.1
flask==2.3.3
"""
    with open('requirements.txt', 'w') as f:
        f.write(requirements)

def main():
    parser = argparse.ArgumentParser(description='Déploie le client Seahawks sur une VM')
    parser.add_argument('--server', required=True, help='URL du serveur central (ex: http://serveur:5000)')
    parser.add_argument('--location', required=True, help='Localisation de la franchise')
    parser.add_argument('--install-dir', default='seahawks_client', help='Répertoire d\'installation')
    
    args = parser.parse_args()
    
    # Création du répertoire d'installation
    os.makedirs(args.install_dir, exist_ok=True)
    os.chdir(args.install_dir)
    
    print(f"Déploiement du client Seahawks pour {args.location}...")
    
    # Copie des fichiers nécessaires
    files_to_copy = ['seahawks_client.py', 'network_scanner.py', 'network_monitor.py']
    for file in files_to_copy:
        src = os.path.join('..', file)
        if os.path.exists(src):
            shutil.copy2(src, '.')
    
    # Création des fichiers de configuration
    print("Création de la configuration...")
    config = create_config(args.server, args.location)
    
    # Création du fichier requirements.txt
    print("Création du fichier requirements.txt...")
    create_requirements()
    
    # Configuration de l'environnement virtuel
    print("Configuration de l'environnement virtuel Python...")
    setup_virtual_env()
    
    # Création du service
    print("Création du service...")
    create_service_file(args.location)
    
    print("\nDéploiement terminé!")
    print(f"ID WAN: {config['wan_id']}")
    print("\nPour démarrer le service:")
    if os.name == 'nt':
        print("1. Double-cliquez sur start_seahawks.bat")
        print("2. Ou ajoutez-le au planificateur de tâches Windows")
    else:
        print("1. sudo cp seahawks.service /etc/systemd/system/")
        print("2. sudo systemctl daemon-reload")
        print("3. sudo systemctl enable seahawks")
        print("4. sudo systemctl start seahawks")

if __name__ == "__main__":
    main()
