# Docker Setup for Easy Reverse Proxy Forward

## Quick Start with Docker Compose

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Resch-Said/Easy-Reverse-Proxy-forward.git
   cd Easy-Reverse-Proxy-forward
   ```

2. **Start the container:**
   ```bash
   docker-compose up -d
   ```

3. **Open the web interface:**
   Open your browser and navigate to `http://<VPS_IP>:5000`

## Management

- **Stop the container:**
  ```bash
  docker-compose down
  ```

- **View logs:**
  ```bash
  docker-compose logs -f
  ```

- **Restart the container:**
  ```bash
  docker-compose restart
  ```

## Important Notes

### Network Mode
The container runs in `host` network mode to allow direct access to the host's network interfaces (e.g., WireGuard, OpenVPN).

### Permissions
The container requires privileged access (`privileged: true`) and the `NET_ADMIN` and `NET_RAW` capabilities to manage iptables rules.

### Data Persistence
Forwarding rules are stored in the `./data` directory and survive container restarts.

### Security
⚠️ **Important:** Do not open port 5000 in your VPS firewall. Only access the GUI over the secure VPN tunnel.

## Docker Commands

### Manually Build and Start the Container
```bash
docker build -t easy-reverse-proxy .
docker run -d \
  --name easy-reverse-proxy \
  --privileged \
  --network host \
  --restart unless-stopped \
  -v ./data:/app/data \
  easy-reverse-proxy
```

### Check Container Status
```bash
docker ps
```

### Enter the Container
```bash
docker exec -it easy-reverse-proxy /bin/bash
```

## Prerequisites

- Docker Engine (20.10+)
- Docker Compose (1.29+)
- Linux host with iptables
- Configured VPN (WireGuard/OpenVPN)

## Troubleshooting

If the container does not start or does not apply rules:

1. Check the logs:
   ```bash
   docker-compose logs
   ```

2. Ensure the host is running Linux (iptables is required)

3. Check whether WireGuard/OpenVPN is running:
   ```bash
   ip addr show
   ```
