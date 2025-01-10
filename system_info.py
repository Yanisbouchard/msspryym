import psutil
import platform
import socket
from datetime import datetime
from typing import Dict, List
import time

class SystemInfo:
    _process_cache = {}
    _last_process_update = 0
    _cache_duration = 5  # secondes

    @staticmethod
    def get_system_info() -> Dict:
        """Récupère les informations système"""
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        
        return {
            'hostname': socket.gethostname(),
            'os': {
                'name': platform.system(),
                'version': platform.version(),
                'architecture': platform.machine()
            },
            'cpu': {
                'cores': psutil.cpu_count(),
                'usage': psutil.cpu_percent(interval=0.5),
                'frequency': psutil.cpu_freq().current if psutil.cpu_freq() else 'Unknown'
            },
            'memory': SystemInfo.get_memory_info(),
            'disk': {
                'total': psutil.disk_usage('/').total,
                'used': psutil.disk_usage('/').used,
                'free': psutil.disk_usage('/').free,
                'percent': psutil.disk_usage('/').percent
            },
            'network': {
                'interfaces': [iface for iface in psutil.net_if_addrs().keys()],
                'bytes_sent': psutil.net_io_counters().bytes_sent,
                'bytes_recv': psutil.net_io_counters().bytes_recv
            },
            'boot_time': {
                'timestamp': boot_time.strftime("%Y-%m-%d %H:%M:%S"),
                'uptime': str(datetime.now() - boot_time)
            }
        }

    @classmethod
    def get_process_info(cls) -> List[Dict]:
        """Récupère les informations sur les processus en cours avec mise en cache"""
        current_time = time.time()
        
        # Retourner le cache s'il est encore valide
        if current_time - cls._last_process_update < cls._cache_duration:
            return list(cls._process_cache.values())

        # Mettre à jour le cache
        new_processes = {}
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                # Initialiser le CPU à 0 pour les nouveaux processus
                if proc.info['pid'] not in cls._process_cache:
                    proc.cpu_percent()
                    new_processes[proc.info['pid']] = {
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu_percent': 0,
                        'memory_percent': proc.memory_percent()
                    }
                else:
                    # Utiliser les valeurs existantes pour les processus connus
                    new_processes[proc.info['pid']] = {
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu_percent': proc.cpu_percent(),
                        'memory_percent': proc.memory_percent()
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        cls._process_cache = new_processes
        cls._last_process_update = current_time
        
        # Retourner les 10 processus les plus consommateurs
        sorted_processes = sorted(
            cls._process_cache.values(),
            key=lambda x: x['cpu_percent'],
            reverse=True
        )[:10]
        
        return sorted_processes

    @staticmethod
    def get_cpu_usage() -> float:
        """Récupère l'utilisation CPU globale"""
        return psutil.cpu_percent(interval=0.5)

    @staticmethod
    def get_per_core_usage() -> List[float]:
        """Récupère l'utilisation CPU par cœur"""
        return psutil.cpu_percent(interval=0.5, percpu=True)

    @staticmethod
    def get_memory_info() -> Dict:
        """Récupère les informations mémoire"""
        mem = psutil.virtual_memory()
        return {
            'total': mem.total,
            'used': mem.used,
            'free': mem.available,
            'percent': mem.percent
        }
