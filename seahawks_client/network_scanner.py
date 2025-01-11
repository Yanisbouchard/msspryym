import nmap
import socket
import ipaddress
from typing import List, Dict

class NetworkScanner:
    def __init__(self):
        self.scanner = nmap.PortScanner()
        
    def get_local_ip(self) -> str:
        """Récupère l'adresse IP locale de la machine"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 1))  # Connexion à Google DNS
            local_ip = s.getsockname()[0]
        except Exception:
            local_ip = '127.0.0.1'
        finally:
            s.close()
        return local_ip
        
    def get_network_range(self) -> str:
        """Détermine la plage réseau à scanner"""
        ip = self.get_local_ip()
        network = ipaddress.IPv4Network(f'{ip}/24', strict=False)
        return str(network)
        
    def scan_network(self) -> List[Dict]:
        """Scanne le réseau et retourne la liste des appareils trouvés"""
        network_range = self.get_network_range()
        self.scanner.scan(hosts=network_range, arguments='-sn')
        
        devices = []
        for host in self.scanner.all_hosts():
            try:
                hostname = socket.gethostbyaddr(host)[0]
            except:
                hostname = 'Unknown'
                
            device_info = {
                'ip': host,
                'hostname': hostname,
                'status': self.scanner[host].state(),
                'mac': self.scanner[host].get('addresses', {}).get('mac', 'Unknown'),
                'vendor': self.scanner[host].get('vendor', {}).get(self.scanner[host].get('addresses', {}).get('mac', ''), 'Unknown')
            }
            devices.append(device_info)
            
        return devices

    def scan_ports(self, target_ip: str, port_range: str = '1-1024') -> List[Dict]:
        """Scanne les ports d'une adresse IP spécifique"""
        self.scanner.scan(hosts=target_ip, arguments=f'-p{port_range}')
        
        open_ports = []
        if target_ip in self.scanner.all_hosts():
            for proto in self.scanner[target_ip].all_protocols():
                ports = self.scanner[target_ip][proto].keys()
                for port in ports:
                    port_info = self.scanner[target_ip][proto][port]
                    if port_info['state'] == 'open':
                        open_ports.append({
                            'port': port,
                            'service': port_info['name'],
                            'version': port_info.get('version', 'Unknown'),
                            'protocol': proto
                        })
                        
        return open_ports
