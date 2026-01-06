# Docker Setup für Easy Reverse Proxy Forward

## Schnellstart mit Docker Compose

1. **Repository klonen:**
   ```bash
   git clone https://github.com/Resch-Said/Easy-Reverse-Proxy-forward.git
   cd Easy-Reverse-Proxy-forward
   ```

2. **Container starten:**
   ```bash
   docker-compose up -d
   ```

3. **Web-Interface öffnen:**
   Öffne deinen Browser und navigiere zu `http://<VPS_IP>:5000`

## Verwaltung

- **Container stoppen:**
  ```bash
  docker-compose down
  ```

- **Logs anzeigen:**
  ```bash
  docker-compose logs -f
  ```

- **Container neu starten:**
  ```bash
  docker-compose restart
  ```

## Wichtige Hinweise

### Netzwerkmodus
Der Container läuft im `host` Netzwerkmodus, um direkten Zugriff auf die Netzwerkinterfaces des Hosts zu haben (z.B. WireGuard, OpenVPN).

### Berechtigungen
Der Container benötigt privilegierten Zugriff (`privileged: true`) und die Capabilities `NET_ADMIN` und `NET_RAW`, um iptables-Regeln zu verwalten.

### Datenpersistenz
Die Forwarding-Regeln werden im `./data` Verzeichnis gespeichert und überstehen Container-Neustarts.

### Sicherheit
⚠️ **Wichtig:** Öffne Port 5000 nicht in deiner VPS-Firewall! Greife auf die GUI nur über den sicheren VPN-Tunnel zu.

## Docker-Befehle

### Container manuell bauen und starten
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

### Container-Status überprüfen
```bash
docker ps
```

### In den Container einloggen
```bash
docker exec -it easy-reverse-proxy /bin/bash
```

## Voraussetzungen

- Docker Engine (20.10+)
- Docker Compose (1.29+)
- Linux Host mit iptables
- Konfiguriertes VPN (WireGuard/OpenVPN)

## Fehlerbehebung

Wenn der Container nicht startet oder keine Regeln anwendet:

1. Überprüfe die Logs:
   ```bash
   docker-compose logs
   ```

2. Stelle sicher, dass der Host Linux verwendet (iptables wird benötigt)

3. Prüfe, ob WireGuard/OpenVPN läuft:
   ```bash
   ip addr show
   ```
