# Seahawks Harvester

Application de surveillance réseau pour les franchises NFL IT.

## Fonctionnalités

- Scan du réseau (machines connectées, ports ouverts)
- Tableau de bord avec informations système
- Mise à jour automatique via GitLab
- Surveillance de la latence WAN
- Interface web moderne et intuitive

## Installation

1. Cloner le dépôt
2. Installer les dépendances : `pip install -r requirements.txt`
3. Configurer `config.json` avec vos identifiants GitLab
4. Lancer l'application : `python app.py`

## Configuration requise

- Python 3.8+
- Nmap
- Accès réseau pour le scan
- Compte GitLab pour les mises à jour
