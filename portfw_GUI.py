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
import os
import sys
import json
import subprocess
import netifaces
from flask import Flask, request, redirect, url_for, render_template_string, flash

app = Flask(__name__)
app.secret_key = 'replace-with-secure-key'

# Path to persistence file
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
RULES_FILE = os.path.join(SCRIPT_DIR, 'rules.json')

# HTML-Template
TEMPLATE = '''
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>PortFW GUI</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2em; }
      table { border-collapse: collapse; width: 100%; margin-top: 1em; }
      th, td { border: 1px solid #ccc; padding: 0.5em; text-align: left; }
      form { margin-bottom: 2em; }
      label { display: block; margin-top: 1em; }
      input, select { padding: 0.5em; width: 100%; max-width: 300px; }
      button { padding: 0.5em 1em; margin-top: 1em; }
      .msg { color: red; }
    </style>
  </head>
  <body>
    <h1>PortFW Reverse-Proxy GUI</h1>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul class="msg">
        {% for msg in messages %}
          <li>{{ msg }}</li>
        {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}
    <form method="post" action="/add">
      <h2>Add New Rule</h2>
      <label>External Interface:
        <select name="extif">
          {% for iface in externals %}
            <option value="{{ iface }}">{{ iface }}</option>
          {% endfor %}
        </select>
      </label>
      <label>Internal WireGuard Interface:
        <select name="intif">
          {% for iface in internals %}
            <option value="{{ iface }}">{{ iface }}</option>
          {% endfor %}
        </select>
      </label>
      <label>External Port: <input type="number" name="ext_port" min="1" max="65535" required></label>
      <label>Internal Target IP: <input type="text" name="int_ip" placeholder="e.g. 192.168.178.84" required></label>
      <label>Internal Target Port: <input type="number" name="int_port" min="1" max="65535" required></label>
      <button type="submit">Add</button>
    </form>

    <h2>Current Rules</h2>
    <table>
      <tr><th>Type</th><th>External</th><th>Target</th><th>Action</th></tr>
      {% for r in rules %}
      <tr>
        <td>TCP/UDP</td>
        <td>{{ r['extif'] }}:{{ r['ext_port'] }}</td>
        <td>{{ r['int_ip'] }}:{{ r['int_port'] }}</td>
        <td>
          <form method="post" action="/del" style="display:inline;">
            <input type="hidden" name="extif" value="{{ r['extif'] }}">
            <input type="hidden" name="intif" value="{{ r['intif'] }}">
            <input type="hidden" name="ext_port" value="{{ r['ext_port'] }}">
            <input type="hidden" name="int_ip" value="{{ r['int_ip'] }}">
            <input type="hidden" name="int_port" value="{{ r['int_port'] }}">
            <button type="submit">Remove</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </table>
  </body>
</html>
'''

def run(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{e.output}")

# Persistence functions
def load_persisted_rules():
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, 'r') as f:
            return json.load(f)
    return []

def save_persisted_rules(rules):
    with open(RULES_FILE, 'w') as f:
        json.dump(rules, f, indent=2)

# Rule application logic (used for both adding and restoring rules)
def apply_rule(rule):
    extif = rule['extif']
    intif = rule['intif']
    ext_port = rule['ext_port']
    int_ip = rule['int_ip']
    int_port = rule['int_port']
    # Enable IP forwarding
    run(['sysctl', '-w', 'net.ipv4.ip_forward=1'])
    for proto in ('tcp', 'udp'):
        # NAT PREROUTING
        try:
            run(['iptables', '-t', 'nat', '-C', 'PREROUTING', '-i', extif,
                 '-p', proto, '--dport', ext_port,
                 '-j', 'DNAT', '--to-destination', f"{int_ip}:{int_port}"])
        except RuntimeError:
            run(['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', extif,
                 '-p', proto, '--dport', ext_port,
                 '-j', 'DNAT', '--to-destination', f"{int_ip}:{int_port}"])
            # FORWARD
            run(['iptables', '-A', 'FORWARD', '-i', extif, '-o', intif,
                 '-p', proto, '--dport', int_port, '-d', int_ip,
                 '-j', 'ACCEPT'])
    # MASQUERADE on internal interface
    try:
        run(['iptables', '-t', 'nat', '-C', 'POSTROUTING', '-o', intif, '-j', 'MASQUERADE'])
    except RuntimeError:
        run(['iptables', '-t', 'nat', '-A', 'POSTROUTING', '-o', intif, '-j', 'MASQUERADE'])
    # Return route (ESTABLISHED)
    try:
        run(['iptables', '-C', 'FORWARD', '-i', intif, '-o', extif,
             '-m', 'conntrack', '--ctstate', 'ESTABLISHED,RELATED',
             '-j', 'ACCEPT'])
    except RuntimeError:
        run(['iptables', '-A', 'FORWARD', '-i', intif, '-o', extif,
             '-m', 'conntrack', '--ctstate', 'ESTABLISHED,RELATED',
             '-j', 'ACCEPT'])

@app.before_first_request
def restore_persistent_rules():
    rules = load_persisted_rules()
    for rule in rules:
        try:
            # Check if rule already exists
            run(['iptables', '-t', 'nat', '-C', 'PREROUTING', '-i', rule['extif'],
                 '-p', 'tcp', '--dport', rule['ext_port'],
                 '-j', 'DNAT', '--to-destination', f"{rule['int_ip']}:{rule['int_port']}"])
        except RuntimeError:
            apply_rule(rule)

@app.route('/')
def index():
    # Network interfaces
    all_if = netifaces.interfaces()
    externals = [i for i in all_if if i != 'lo']
    internals = [i for i in all_if if i.startswith('wg') or i.startswith('tun') or i.startswith('tap')]
    # Display persistent rules
    rules = load_persisted_rules()
    return render_template_string(TEMPLATE, externals=externals, internals=internals, rules=rules)

@app.route('/add', methods=['POST'])
def add():
    extif   = request.form['extif']
    intif   = request.form['intif']
    ext_port= request.form['ext_port']
    int_ip  = request.form['int_ip']
    int_port= request.form['int_port']
    new_rule = {'extif': extif, 'intif': intif, 'ext_port': ext_port,
                'int_ip': int_ip, 'int_port': int_port}
    try:
        apply_rule(new_rule)
    except RuntimeError as e:
        flash(str(e))
        return redirect(url_for('index'))
    # Update persistence
    rules = load_persisted_rules()
    if new_rule not in rules:
        rules.append(new_rule)
        save_persisted_rules(rules)
    flash(f"Rule TCP/UDP {extif}:{ext_port} → {int_ip}:{int_port} added.")
    return redirect(url_for('index'))

@app.route('/del', methods=['POST'])
def delete():
    extif    = request.form['extif']
    intif    = request.form['intif']
    ext_port = request.form['ext_port']
    int_ip   = request.form['int_ip']
    int_port = request.form['int_port']
    try:
        # Remove NAT and FORWARD rules
        for proto in ('tcp', 'udp'):
            run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', extif,
                 '-p', proto, '--dport', ext_port,
                 '-j', 'DNAT', '--to-destination', f"{int_ip}:{int_port}"])
            run(['iptables', '-D', 'FORWARD', '-i', extif, '-o', intif,
                 '-p', proto, '--dport', int_port, '-d', int_ip,
                 '-j', 'ACCEPT'])
    except RuntimeError as e:
        flash(str(e))
        return redirect(url_for('index'))
    # Update persistence
    rules = load_persisted_rules()
    rules = [r for r in rules if not (r['extif']==extif and r['intif']==intif \
              and r['ext_port']==ext_port and r['int_ip']==int_ip and r['int_port']==int_port)]
    save_persisted_rules(rules)
    flash(f"Rule {extif}:{ext_port} removed.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    if not sys.platform.startswith('linux'):
        print("Only runs on Linux.")
        sys.exit(1)
    app.run(host='0.0.0.0', port=5000)
