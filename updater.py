import os
import sys
import gitlab
import json
import hashlib
import logging
from datetime import datetime
import time
import shutil

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('updater.log'),
        logging.StreamHandler()
    ]
)

class AutoUpdater:
    def __init__(self):
        self.config_file = 'config.json'
        self.load_config()
        self.gl = gitlab.Gitlab(
            url=self.config['gitlab_url'],
            private_token=self.config['gitlab_token']
        )
        self.project = self.gl.projects.get(self.config['project_id'])
        self.current_version_file = 'current_version.json'

    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            logging.error("Fichier de configuration non trouvé")
            sys.exit(1)

    def get_current_version(self):
        try:
            with open(self.current_version_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"commit_id": None}

    def save_current_version(self, commit_id):
        with open(self.current_version_file, 'w') as f:
            json.dump({"commit_id": commit_id}, f)

    def backup_current_version(self):
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"backup_{timestamp}")
        
        # Liste des fichiers à exclure de la sauvegarde
        exclude = {
            'venv', 'backups', '__pycache__', 
            'updater.log', 'config.json', 
            'current_version.json'
        }
        
        os.makedirs(backup_path)
        for item in os.listdir('.'):
            if item not in exclude and not item.startswith('.'):
                src = os.path.join('.', item)
                dst = os.path.join(backup_path, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
        
        return backup_path

    def check_for_updates(self):
        try:
            current_version = self.get_current_version()
            latest_commit = self.project.commits.list()[0]
            
            if current_version["commit_id"] != latest_commit.id:
                logging.info(f"Nouvelle version disponible: {latest_commit.id}")
                return latest_commit
            return None
        except Exception as e:
            logging.error(f"Erreur lors de la vérification des mises à jour: {str(e)}")
            return None

    def download_and_apply_update(self, commit):
        try:
            # Sauvegarde de la version actuelle
            backup_path = self.backup_current_version()
            logging.info(f"Sauvegarde créée dans: {backup_path}")

            # Téléchargement des fichiers
            items = self.project.repository_tree(recursive=True)
            for item in items:
                if item['type'] == 'blob':
                    file_path = item['path']
                    # Exclusion des fichiers de configuration et des dossiers spéciaux
                    if not any(excluded in file_path for excluded in ['venv/', 'config.json', '__pycache__']):
                        file_content = self.project.files.get(
                            file_path=file_path, 
                            ref=commit.id
                        ).decode()
                        
                        # Création des dossiers si nécessaire
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        
                        with open(file_path, 'wb') as f:
                            f.write(file_content)
                        
                        logging.info(f"Fichier mis à jour: {file_path}")

            # Mise à jour de la version actuelle
            self.save_current_version(commit.id)
            logging.info("Mise à jour terminée avec succès")
            return True
            
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour: {str(e)}")
            return False

    def run(self):
        while True:
            logging.info("Vérification des mises à jour...")
            update = self.check_for_updates()
            
            if update:
                logging.info("Installation de la mise à jour...")
                if self.download_and_apply_update(update):
                    logging.info("Redémarrage de l'application...")
                    os.execv(sys.executable, ['python'] + sys.argv)
            
            # Attente avant la prochaine vérification
            time.sleep(self.config['check_interval'])

if __name__ == "__main__":
    updater = AutoUpdater()
    updater.run()
