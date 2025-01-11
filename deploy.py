import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_python_version():
    """Vérifie la version de Python"""
    if sys.version_info < (3, 8):
        print("Python 3.8 ou supérieur est requis")
        sys.exit(1)

def create_venv():
    """Crée l'environnement virtuel"""
    if not os.path.exists('venv'):
        subprocess.run([sys.executable, '-m', 'venv', 'venv'])
    
    # Activation du venv
    if os.name == 'nt':  # Windows
        pip = 'venv\\Scripts\\pip.exe'
    else:  # Linux/Mac
        pip = 'venv/bin/pip'
    
    # Installation des dépendances
    subprocess.run([pip, 'install', '-r', 'requirements.txt'])

def setup_env():
    """Configure le fichier .env s'il n'existe pas"""
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write('''# Configuration du serveur
SERVER_URL=http://localhost:5000

# Configuration du client
LOCATION=Bureau Principal

# Configuration de la base de données
DATABASE_PATH=wans.db

# Configuration du logging
LOG_LEVEL=INFO
LOG_FILE=seahawks.log
''')

def setup_database():
    """Configure la base de données"""
    if os.path.exists('wans.db'):
        backup_path = 'wans.db.backup'
        shutil.copy2('wans.db', backup_path)
        print(f"Base de données sauvegardée dans {backup_path}")

def main():
    """Script principal de déploiement"""
    print("Déploiement de Seahawks Network Monitor...")
    
    # Vérification de Python
    check_python_version()
    print("✓ Version de Python OK")
    
    # Création du venv et installation des dépendances
    create_venv()
    print("✓ Environnement virtuel créé et dépendances installées")
    
    # Configuration
    setup_env()
    print("✓ Fichier .env configuré")
    
    # Base de données
    setup_database()
    print("✓ Base de données configurée")
    
    print("\nDéploiement terminé avec succès!")
    print("\nPour démarrer le serveur:")
    if os.name == 'nt':  # Windows
        print("venv\\Scripts\\python.exe app.py")
    else:  # Linux/Mac
        print("./venv/bin/python app.py")

if __name__ == '__main__':
    main()
