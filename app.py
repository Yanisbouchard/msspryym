from flask import Flask, render_template, jsonify
import nmap
import psutil
import socket
from ping3 import ping
import platform
import json
import threading
from updater import AutoUpdater

app = Flask(__name__)

VERSION = "1.0.0"

def get_system_info():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return {
        "hostname": hostname,
        "ip_address": ip_address,
        "os": platform.system() + " " + platform.release()
    }

def scan_network():
    nm = nmap.PortScanner()
    network = "192.168.1.0/24"  # À adapter selon votre réseau
    nm.scan(hosts=network, arguments='-sn')
    
    hosts_list = []
    for host in nm.all_hosts():
        host_info = {
            "ip": host,
            "status": nm[host].state()
        }
        hosts_list.append(host_info)
    
    return hosts_list

def measure_wan_latency():
    target = "8.8.8.8"  # Google DNS comme cible
    latencies = []
    for _ in range(5):
        response_time = ping(target)
        if response_time:
            latencies.append(response_time * 1000)  # Conversion en ms
    
    return sum(latencies) / len(latencies) if latencies else -1

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/dashboard')
def get_dashboard():
    system_info = get_system_info()
    connected_devices = scan_network()
    wan_latency = measure_wan_latency()
    
    return jsonify({
        "system_info": system_info,
        "connected_devices": connected_devices,
        "connected_devices_count": len(connected_devices),
        "wan_latency": wan_latency,
        "version": VERSION
    })

if __name__ == '__main__':
    # Démarrage de l'auto-updater dans un thread séparé
    updater = AutoUpdater()
    updater_thread = threading.Thread(target=updater.run, daemon=True)
    updater_thread.start()
    
    # Démarrage de l'application Flask
    app.run(host='0.0.0.0', port=5000, debug=True)
