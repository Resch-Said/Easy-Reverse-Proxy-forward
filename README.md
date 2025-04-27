# Easy Reverse Proxy forward

## Description
A lightweight reverse proxy that forwards incoming connections to a target server. Designed for users who have a VPS with an IPv4 address but lack a direct IPv4 address for their own server, or who simply want a convenient reverse-proxy setup for a local service.

![image](https://github.com/user-attachments/assets/d204502a-1ab1-4178-a9cf-2550b55fb520)

## Features
- Simple configuration: Manage forwarding rules via a minimal Flask web GUI.
- Persistent rules: Applies iptables rules when the Flask server starts.

## Prerequisites
- A VPS with an IPv4/IPv6 address and root (or sudo) access.
- A target server (local or remote) that you want to expose.
- A secure tunnel between the VPS and target server, for example WireGuard or OpenVPN.

## Getting Started
1. Clone the repository
```bash
git clone https://github.com/Resch-Said/Easy-Reverse-Proxy-forward.git
cd Easy-Reverse-Proxy-forward
```

2. Install dependencies
```bash
apt install -y python3-flask python3-netifaces
```

3. Run the proxy GUI (Background)
```bash
nohup python3 portfw_GUI.py &
```

4. Access the web interface
   Open your web browser and navigate to `http://<VPS_IP_or_VPN_IP>:5000`

## Security Considerations
**Limit exposure:** Do not open port 5000 on your VPS firewall. Instead, access the GUI over the secure VPN tunnel.

## WireGuard Setup
To ensure your WireGuard interface (wg0) starts on boot and is immediately active, enable and start the wg-quick service:
```bash
sudo systemctl start wg-quick@wg0
sudo systemctl enable wg-quick@wg0
```

In your WireGuard peer configuration, remove any `AllowedIPs = 0.0.0.0/0, ::/0` entries if you only want to route specific subnets. Leaving `0.0.0.0/0, ::/0` would send all traffic through the tunnel, causing loss of direct access to your VPS unless you configure appropriate routes.
