#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
portfw_gui.py (persistent)

A simple Web GUI for adding/removing TCP/UDP port forwarding rules via iptables,
with persistence across reboots.
Requirements: flask, netifaces
Installation:
    pip3 install flask netifaces

Usage:
    sudo python3 portfw_gui_persistent.py

Then open in browser at http://<VPS_IP>:5000
"""
from main import main


if __name__ == "__main__":
    main()
