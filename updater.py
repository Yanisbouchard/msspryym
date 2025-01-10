import os
import json
import time
import shutil
import requests
from datetime import datetime
import logging
import sys

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
        self.config = self._load_config()
        self.github_repo = self.config['github_repo']
        self.api_url = f"https://api.github.com/repos/{self.github_repo}"
        self.headers = {
            'Authorization': f"token {self.config.get('github_token')}",
            'Accept': 'application/vnd.github.v3+json'
        }

    def _load_config(self):
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error("Fichier de configuration non trouvé")
            sys.exit(1)

    def _create_backup(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backup_{timestamp}"
        shutil.copytree('.', backup_dir, ignore=shutil.ignore_patterns('backup_*', '__pycache__', '*.pyc'))
        return backup_dir

    def _get_latest_commit(self):
        response = requests.get(f"{self.api_url}/commits/main", headers=self.headers)
        if response.status_code == 200:
            return response.json()['sha']
        return None

    def _download_latest_code(self):
        response = requests.get(f"{self.api_url}/zipball/main", headers=self.headers)
        if response.status_code == 200:
            with open('update.zip', 'wb') as f:
                f.write(response.content)
            return True
        return False

    def check_for_updates(self):
        try:
            latest_commit = self._get_latest_commit()
            if not latest_commit:
                logging.error("Impossible de vérifier les mises à jour")
                return

            last_update_file = 'last_update.txt'
            current_commit = None
            if os.path.exists(last_update_file):
                with open(last_update_file, 'r') as f:
                    current_commit = f.read().strip()

            if current_commit != latest_commit:
                logging.info("Nouvelle mise à jour disponible!")
                backup_dir = self._create_backup()
                logging.info(f"Backup créé dans: {backup_dir}")

                if self._download_latest_code():
                    logging.info("Code mis à jour avec succès")
                    with open(last_update_file, 'w') as f:
                        f.write(latest_commit)
                else:
                    logging.error("Échec de la mise à jour")
            else:
                logging.info("Le code est à jour")

        except Exception as e:
            logging.error(f"Erreur lors de la vérification des mises à jour: {str(e)}")

    def start(self):
        while True:
            logging.info("\nVérification des mises à jour...")
            self.check_for_updates()
            time.sleep(self.config['check_interval'])

if __name__ == "__main__":
    updater = AutoUpdater()
    updater.start()
