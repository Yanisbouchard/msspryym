from ping3 import ping
from typing import Dict, List
import time
from statistics import mean, median

class NetworkMonitor:
    def __init__(self):
        self.default_targets = [
            '8.8.8.8',        # Google DNS
            '1.1.1.1',        # Cloudflare DNS
            '208.67.222.222'  # OpenDNS
        ]
        
    def measure_latency(self, target: str, count: int = 4) -> Dict:
        """Mesure la latence vers une cible spécifique"""
        latencies = []
        packet_loss = 0
        
        for _ in range(count):
            try:
                start_time = time.time()
                response_time = ping(target, timeout=2)
                if response_time is not None:
                    latencies.append(response_time * 1000)  # Conversion en ms
                else:
                    packet_loss += 1
            except Exception:
                packet_loss += 1
            time.sleep(0.2)  # Petit délai entre les pings
            
        return {
            'target': target,
            'min': min(latencies) if latencies else None,
            'max': max(latencies) if latencies else None,
            'avg': mean(latencies) if latencies else None,
            'median': median(latencies) if latencies else None,
            'packet_loss': (packet_loss / count) * 100,
            'samples': len(latencies)
        }
        
    def check_wan_connectivity(self) -> List[Dict]:
        """Vérifie la connectivité WAN vers plusieurs cibles"""
        results = []
        for target in self.default_targets:
            results.append(self.measure_latency(target))
        return results
