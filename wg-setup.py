#!/usr/bin/python3


import os
import sys
import subprocess
import platform
import socket
import netifaces
import requests
import re
import getpass



USER = getpass.getuser()
HOME_DIR_USER = os.path.expanduser("~")


WG_DIR = '/etc/wireguard'
WG_DIR_CONFIG_PEER = '/etc/wireguard/config_peer'
WG_DIR_KEY_PEER = '/etc/wireguard/peer_key'
WG_DIR_SERVER_KEY = '/etc/wireguard/server_key'




def get_public_ip():
    try:
        ip = requests.get('https://ifconfig.me').text
        return ip
    except requests.RequestException:
        raise Exception("Unable to get public IP address")


SERVER_PUBLIC_IP = get_public_ip()


def check_superuser():
    if os.geteuid() != 0:
        print("This script must be run as root!")
        sys.exit(1)



def install_wireguard():
    # Check if WireGuard is already installed
    if os.path.exists(WG_DIR):
        print("WireGuard is already installed.")
        return

    # Install WireGuard based on the package manager
    package_managers = {
        "debian": "apt install wireguard -y",
        "ubuntu": "apt install wireguard -y",
        "centos": "yum install epel-release -y && yum install wireguard-tools -y",
        "fedora": "yum install epel-release -y && yum install wireguard-tools -y",
        "arch": "pacman -S wireguard-tools --noconfirm"
    }

    distro = platform.node().lower()
    if distro in package_managers:
        install_command = package_managers[distro]
        os.system(f"sudo {install_command}")
    else:
        raise Exception(f"Unsupported Linux distribution: {distro}")

    print("WireGuard installation complete.")


def get_default_interface():
    gateways = netifaces.gateways()
    default_gateways = gateways['default'][netifaces.AF_INET][1]
    return default_gateways


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', int(port))) == 0


def open_firewall_port(port):
    # Check if ufw is active and open the port
    ufw_status = subprocess.run(["sudo", "ufw", "status"], capture_output=True, text=True).stdout
    if "inactive" not in ufw_status:
        os.system(f"sudo ufw allow {port}/udp")
        print(f"Opened UDP port {port} in ufw firewall")

    # Check if firewalld is active and open the port
    firewalld_status = subprocess.run(["sudo", "systemctl", "is-active", "firewalld"], capture_output=True, text=True).stdout
    if "active" in firewalld_status:
        os.system(f"sudo firewall-cmd --add-port={port}/udp --permanent")
        os.system("sudo firewall-cmd --reload")
        print(f"Opened UDP port {port} in firewalld")


def create_server_config():
    if not os.path.exists(WG_DIR):
        os.makedirs(WG_DIR)
    if not os.path.exists(WG_DIR_SERVER_KEY):
        os.makedirs(WG_DIR_SERVER_KEY)
    if not os.path.exists(WG_DIR_KEY_PEER):
        os.makedirs(WG_DIR_KEY_PEER)
    if not os.path.exists(WG_DIR_CONFIG_PEER):
        os.makedirs(WG_DIR_CONFIG_PEER)

    while True:
        listen_port = input("Enter the port number to use for WireGuard (default 51820): ") or "51820"
        if not listen_port.isdigit() or is_port_in_use(listen_port):
            print(f"Port {port} is either invalid or already in use. Please try another port.")
        else:
            break

    os.makedirs(WG_DIR, exist_ok=True)
    os.system(f"wg genkey | tee {WG_DIR_SERVER_KEY}/server_privatekey | wg pubkey | tee {WG_DIR_SERVER_KEY}/server_publickey")
    os.system(f"sudo chmod 600 {WG_DIR_SERVER_KEY}/server_privatekey {WG_DIR_SERVER_KEY}/server_publickey")


    with open(f"{WG_DIR_SERVER_KEY}/server_privatekey", 'r') as f:
        private_key_server = f.read().strip()

    interface_server = get_default_interface()

    config = f"""
[Interface]
PrivateKey = {private_key_server}
Address = 10.0.0.1/24
ListenPort = {listen_port}

SaveConfig = true
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o {interface_server} -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o {interface_server} -j MASQUERADE

    """

    with open(f"{WG_DIR}/wg0.conf", 'w') as f:
        f.write(config)


    open_firewall_port(listen_port)
    print(f"Created main file configuration '/etc/wireguard/wg0.conf' and subdirectories 'conf_peer', 'peer_key'!")



def enable_ip_forwarding():
    with open('/etc/sysctl.conf', 'r') as f:
        lines = f.readlines()
        for line in lines:
            if line.strip() == "net.ipv4.ip_forward=1":
                print("IP forwarding is already enabled")
                return

    with open('/etc/sysctl.conf', 'a') as f:
        f.write("\nnet.ipv4.ip_forward=1\n")
        f.close()
    os.system("sudo sysctl -p")
    print("Enabled IP forwarding")


def is_valid_dns(dns):
    return bool(re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', dns))


def get_server_port():
    with open(f"{WG_DIR}/wg0.conf", 'r') as f:
        for line in f:
            if line.strip().startswith("ListenPort"):
                print(line.strip().split('=')[1].strip())
                return line.strip().split('=')[1].strip()
    return None


def get_used_ip_addresses():
    used_ips = []
    with open(f"{WG_DIR}/wg0.conf", 'r') as f:
        for line in f:
            match = re.search(r'AllowedIPs\s*=\s*([0-9.]+)/[0-9]+', line)
            if match:
                used_ips.append(match.group(1))
    return used_ips



def find_next_available_ip(base_ip, used_ips):
    base_parts = base_ip.split('.')
    for i in range(2, 255):
        next_ip = f"{base_parts[0]}.{base_parts[1]}.{base_parts[2]}.{i}"
        if next_ip not in used_ips:
            return next_ip
    raise Exception("No available IP addresses in the subnet")



def load_peer_config(filename, name):

    wireguard_dir_conf = f"{HOME_DIR_USER}/wireguard_conf"
    if not os.path.exists(wireguard_dir_conf):
        os.makedirs(wireguard_dir_conf)

    os.system(f"sudo cp {filename} {wireguard_dir_conf}/{name}")
    os.system(f"sudo chown -R {USER}:{USER} {wireguard_dir_conf}/")

    while True:
        download = input("Do you want to download the peer configuration file from the server? (yes/no): ").lower()
        if download == "yes":
            print(f"Downloading {filename} from the server...")
            local_path = input("Enter the local path to save the file: ")
            os.system(f"scp {USER}@{SERVER_PUBLIC_IP}:{wireguard_dir_conf}/{name} {local_path}")
            print(f"{filename} downloaded to {local_path}")
            break
        elif download == "no":
            print(f"{filename} not downloaded.")
            break
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")




def create_peer_config():
    while True:
        prefix_name = input("Enter the name for the peer (only letters): ")
        if not prefix_name.isalpha():
            print("Both peer name and key prefix must contain only letters. Please try again.")
        else:
            break


    while True:
        dns = input("Enter the DNS for the peer (default 8.8.8.8): ") or "8.8.8.8"
        if is_valid_dns(dns):
            break
        else:
            print("Invalid DNS format. Please enter a valid DNS address (e.g., 8.8.8.8).")



    os.system(f"wg genkey | tee {WG_DIR_KEY_PEER}/{prefix_name}_peer_privatekey | wg pubkey | tee {WG_DIR_KEY_PEER}/{prefix_name}_peer_publickey")
    os.system(f"sudo chmod 600 {WG_DIR_KEY_PEER}/{prefix_name}_peer_privatekey {WG_DIR_KEY_PEER}/{prefix_name}_peer_publickey")

    with open(f"{WG_DIR_KEY_PEER}/{prefix_name}_peer_privatekey", 'r') as f:
        peer_private_key = f.read().strip()

    with open(f"{WG_DIR_KEY_PEER}/{prefix_name}_peer_publickey", 'r') as f:
        peer_public_key = f.read().strip()

    with open(f"{WG_DIR_SERVER_KEY}/server_publickey", 'r') as f:
        server_public_key = f.read().strip()


    server_ip = get_public_ip()
    server_port = get_server_port()

    used_ips = get_used_ip_addresses()
    next_ip = find_next_available_ip("10.0.0.1", used_ips)

    peer_config = f"""
[Interface]
PrivateKey = {peer_private_key}
Address = {next_ip}/24
DNS = {dns}

[Peer]
PublicKey = {server_public_key}
Endpoint = {server_ip}:{server_port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 20
    """

    with open(f"{WG_DIR_CONFIG_PEER}/{prefix_name}_peer.conf", 'w') as f:
        f.write(peer_config)

    with open(f"{WG_DIR}/wg0.conf", 'a') as f:
        peer_entry = f"""

[Peer]
PublicKey = {peer_public_key}
AllowedIPs = {next_ip}/32

        """
        f.write(peer_entry)

    load_peer_config(f"{WG_DIR_CONFIG_PEER}/{prefix_name}_peer.conf", f"{prefix_name}_peer.conf")





def start_wireguard():
    os.system("sudo systemctl enable wg-quick@wg0")
    os.system("sudo systemctl start wg-quick@wg0")

def restart_wireguard():
    os.system("sudo systemctl restart wg-quick@wg0")

def main():

    check_superuser()

    # Check if WireGuard is installed and running
    wg_installed = subprocess.run(["which", "wg"], capture_output=True, text=True).stdout.strip()
    wg_running = subprocess.run(["sudo", "systemctl", "is-active", "wg-quick@wg0"], capture_output=True, text=True).stdout.strip()

    if not wg_installed:
        print("WireGuard is not installed. Installing WireGuard...")
        install_wireguard()
        create_server_config()
        enable_ip_forwarding()
    elif wg_running == "inactive":
        print("WireGuard is installed but not running. Starting WireGuard...")
        start_wireguard()
    else:
        print("WireGuard is installed and running.")

    create_peer_config()
    restart_wireguard()

if __name__ == '__main__':
    main()

