#!/usr/bin/env bash

# Ein Setup-Skript, um WireGuard zu installieren und das Interface wg0 automatisch zu aktivieren und zu starten
# inklusive Installation aller erforderlichen Pakete.

set -e

# Update Paketlisten
sudo apt update

# Installation der benötigten Pakete: WireGuard, Flask und netifaces
sudo apt install -y wireguard python3-flask python3-netifaces

# WireGuard wg-quick Service aktivieren und starten
sudo systemctl start wg-quick@wg0.service
sudo systemctl enable wg-quick@wg0.service

echo "Setup erfolgreich: WireGuard installiert, Pakete installiert und Interface wg0 aktiviert sowie gestartet."
