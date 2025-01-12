import os
import json
import time
import subprocess
import logging
import git
import signal
import sys
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_update.log'),
        logging.StreamHandler()
    ]
)

class AutoUpdater:
    def __init__(self):
        self.app_process = None
        self.repo = git.Repo('.')
        self.last_commit = self.repo.head.commit.hexsha

    def _restart_app(self):
        """Redémarre l'application Flask"""
        try:
            # Arrêt du processus existant s'il existe
            if self.app_process:
                logging.info("Arrêt de l'application...")
                os.killpg(os.getpgid(self.app_process.pid), signal.SIGTERM)
                self.app_process.wait()

            # Démarrage de l'application
            logging.info("Démarrage de l'application...")
            self.app_process = subprocess.Popen(
                ['python3', 'app.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Crée un nouveau groupe de processus
            )
            logging.info("Application redémarrée avec succès")
        except Exception as e:
            logging.error(f"Erreur lors du redémarrage de l'application: {str(e)}")

    def check_for_updates(self):
        """Vérifie et applique les mises à jour depuis GitHub"""
        try:
            # Fetch les dernières modifications
            self.repo.remotes.origin.fetch()
            
            # Récupère le dernier commit distant
            remote_commit = self.repo.refs['origin/main'].commit.hexsha
            
            # Compare avec le commit local
            if remote_commit != self.last_commit:
                logging.info("Nouvelles modifications détectées!")
                
                # Pull les changements
                self.repo.remotes.origin.pull()
                logging.info("Modifications téléchargées avec succès")
                
                # Met à jour le dernier commit connu
                self.last_commit = remote_commit
                
                # Redémarre l'application
                self._restart_app()
                
                return True
            else:
                logging.info("Aucune nouvelle modification")
                return False
                
        except Exception as e:
            logging.error(f"Erreur lors de la vérification des mises à jour: {str(e)}")
            return False

    def start(self):
        """Démarre la boucle principale"""
        logging.info("Démarrage du service d'auto-update...")
        
        # Premier démarrage de l'application
        self._restart_app()
        
        try:
            while True:
                self.check_for_updates()
                time.sleep(300)  # Attend 5 minutes
        except KeyboardInterrupt:
            logging.info("Arrêt du service...")
            if self.app_process:
                os.killpg(os.getpgid(self.app_process.pid), signal.SIGTERM)
            sys.exit(0)

if __name__ == "__main__":
    updater = AutoUpdater()
    updater.start()
