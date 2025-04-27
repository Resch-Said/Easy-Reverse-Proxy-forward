#!/usr/bin/env bash

# A setup script to install WireGuard and automatically activate and start the wg0 interface
# including installation of all required packages.

set -e

# Update package lists
sudo apt update

# Installation of required packages: WireGuard, Flask and netifaces
sudo apt install -y wireguard python3-flask python3-netifaces

# Enable and start WireGuard wg-quick service
sudo systemctl start wg-quick@wg0.service
sudo systemctl enable wg-quick@wg0.service

echo "Setup successful: WireGuard installed, packages installed and interface wg0 activated and started."
