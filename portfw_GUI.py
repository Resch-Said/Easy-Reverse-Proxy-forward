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
      .active { color: green; font-weight: bold; }
      .inactive { color: gray; font-style: italic; }
      .actions form { display: inline; margin: 0; }
      .actions button { margin: 0 0.2em; }
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
      <label>Internal WireGuard/OpenVPN Interface:
        <select name="intif">
          {% for iface in internals %}
            <option value="{{ iface }}">{{ iface }}</option>
          {% endfor %}
        </select>
      </label>
      <label>Protocol:
        <select name="protocol">
          <option value="both">TCP & UDP</option>
          <option value="tcp">TCP only</option>
          <option value="udp">UDP only</option>
        </select>
      </label>
      <label>External Port: <input type="number" name="ext_port" min="1" max="65535" required></label>
      <label>Internal Target IP: <input type="text" name="int_ip" placeholder="e.g. 192.168.178.84" required></label>
      <label>Internal Target Port: <input type="number" name="int_port" min="1" max="65535" required></label>
      <button type="submit">Add</button>
    </form>

    <h2>Current Rules</h2>
    <table>
      <tr><th>Type</th><th>External</th><th>Target</th><th>Status</th><th>Actions</th></tr>
      {% for r in rules %}
      <tr>
        <td>{{ r.get('protocol', 'both')|upper if r.get('protocol', 'both') != 'both' else 'TCP/UDP' }}</td>
        <td>{{ r['extif'] }}:{{ r['ext_port'] }}</td>
        <td>{{ r['int_ip'] }}:{{ r['int_port'] }}</td>
        <td class="{{ 'active' if r.get('enabled', True) else 'inactive' }}">
          {{ 'Active' if r.get('enabled', True) else 'Inactive' }}
        </td>
        <td class="actions">
          <form method="post" action="/del" style="display:inline;">
            <input type="hidden" name="extif" value="{{ r['extif'] }}">
            <input type="hidden" name="intif" value="{{ r['intif'] }}">
            <input type="hidden" name="ext_port" value="{{ r['ext_port'] }}">
            <input type="hidden" name="int_ip" value="{{ r['int_ip'] }}">
            <input type="hidden" name="int_port" value="{{ r['int_port'] }}">
            <input type="hidden" name="protocol" value="{{ r.get('protocol', 'both') }}">
            <button type="submit">Remove</button>
          </form>
          
          {% if r.get('enabled', True) %}
          <form method="post" action="/disable" style="display:inline;">
            <input type="hidden" name="extif" value="{{ r['extif'] }}">
            <input type="hidden" name="intif" value="{{ r['intif'] }}">
            <input type="hidden" name="ext_port" value="{{ r['ext_port'] }}">
            <input type="hidden" name="int_ip" value="{{ r['int_ip'] }}">
            <input type="hidden" name="int_port" value="{{ r['int_port'] }}">
            <input type="hidden" name="protocol" value="{{ r.get('protocol', 'both') }}">
            <button type="submit">Disable</button>
          </form>
          {% else %}
          <form method="post" action="/enable" style="display:inline;">
            <input type="hidden" name="extif" value="{{ r['extif'] }}">
            <input type="hidden" name="intif" value="{{ r['intif'] }}">
            <input type="hidden" name="ext_port" value="{{ r['ext_port'] }}">
            <input type="hidden" name="int_ip" value="{{ r['int_ip'] }}">
            <input type="hidden" name="int_port" value="{{ r['int_port'] }}">
            <input type="hidden" name="protocol" value="{{ r.get('protocol', 'both') }}">
            <button type="submit">Enable</button>
          </form>
          {% endif %}
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
    protocol = rule.get('protocol', 'both')  # Default to 'both' for backward compatibility
    
    # Enable IP forwarding
    run(['sysctl', '-w', 'net.ipv4.ip_forward=1'])
    
    # Determine which protocols to apply
    protocols = []
    if protocol == 'both':
        protocols = ['tcp', 'udp']
    else:
        protocols = [protocol]  # Only apply the selected protocol
    
    for proto in protocols:
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
def restore_persistent_rules_on_first_request():
    # This function is kept only for compatibility with older Flask versions
    pass

def restore_persistent_rules():
    print("Restoring persistent rules...")
    rules = load_persisted_rules()
    print(f"Found rules: {len(rules)}")
    for rule in rules:
        # Only restore active rules
        if rule.get('enabled', True):  # Default is active for backward compatibility
            try:
                # First delete any existing rules to avoid duplicates
                try:
                    for proto in ('tcp', 'udp'):
                        # Delete NAT rule
                        run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', rule['extif'],
                            '-p', proto, '--dport', rule['ext_port'],
                            '-j', 'DNAT', '--to-destination', f"{rule['int_ip']}:{rule['int_port']}"])
                        # Delete Forward rule
                        run(['iptables', '-D', 'FORWARD', '-i', rule['extif'], '-o', rule['intif'],
                            '-p', proto, '--dport', rule['int_port'], '-d', rule['int_ip'],
                            '-j', 'ACCEPT'])
                except RuntimeError:
                    # Ignore if the rules do not exist
                    pass

                # Then add new rules
                apply_rule(rule)
                print(f"Rule restored: {rule['extif']}:{rule['ext_port']} → {rule['int_ip']}:{rule['int_port']}")
            except RuntimeError as e:
                print(f"Error restoring rule: {str(e)}")
        else:
            print(f"Rule skipped (disabled): {rule['extif']}:{rule['ext_port']} → {rule['int_ip']}:{rule['int_port']}")

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
    extif    = request.form['extif']
    intif    = request.form['intif']
    ext_port = request.form['ext_port']
    int_ip   = request.form['int_ip']
    int_port = request.form['int_port']
    protocol = request.form['protocol']  # 'both', 'tcp', or 'udp'
    
    new_rule = {
        'extif': extif, 
        'intif': intif, 
        'ext_port': ext_port,
        'int_ip': int_ip, 
        'int_port': int_port,
        'protocol': protocol
    }
    
    try:
        apply_rule(new_rule)
    except RuntimeError as e:
        flash(str(e))
        return redirect(url_for('index'))
    # Update persistence
    rules = load_persisted_rules()
    
    # Check if the rule already exists (without considering the new protocol field)
    existing_rule = None
    for rule in rules:
        if (rule['extif'] == extif and rule['intif'] == intif and 
            rule['ext_port'] == ext_port and rule['int_ip'] == int_ip and 
            rule['int_port'] == int_port):
            existing_rule = rule
            break
    
    if existing_rule:
        # Update existing rule with the new protocol
        existing_rule['protocol'] = protocol
    else:
        # Add new rule
        rules.append(new_rule)
    
    save_persisted_rules(rules)
    
    # User-friendly protocol name for the message
    proto_name = "TCP/UDP" if protocol == "both" else protocol.upper()
    flash(f"Rule {proto_name} {extif}:{ext_port} → {int_ip}:{int_port} added.")
    
    return redirect(url_for('index'))

@app.route('/del', methods=['POST'])
def delete():
    extif    = request.form['extif']
    intif    = request.form['intif']
    ext_port = request.form['ext_port']
    int_ip   = request.form['int_ip']
    int_port = request.form['int_port']
    protocol = request.form.get('protocol', 'both')  # Default is 'both' for backward compatibility
    
    # Update persistence first - always remove the rule from the JSON
    rules = load_persisted_rules()
    old_rules_count = len(rules)
    rules = [r for r in rules if not (r['extif']==extif and r['intif']==intif \
              and r['ext_port']==ext_port and r['int_ip']==int_ip and r['int_port']==int_port)]
    save_persisted_rules(rules)
    
    # Determine which protocols to remove
    protocols = []
    if protocol == 'both':
        protocols = ['tcp', 'udp']
    else:
        protocols = [protocol]  # Only remove the selected protocol
    
    # Now try to remove the iptables rules
    errors = []
    for proto in protocols:
        try:
            # Check if the rule exists before we delete it
            run(['iptables', '-t', 'nat', '-C', 'PREROUTING', '-i', extif,
                '-p', proto, '--dport', ext_port,
                '-j', 'DNAT', '--to-destination', f"{int_ip}:{int_port}"])
            # If yes, remove
            run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', extif,
                '-p', proto, '--dport', ext_port,
                '-j', 'DNAT', '--to-destination', f"{int_ip}:{int_port}"])
        except RuntimeError:
            errors.append(f"{proto.upper()}-NAT rule not found")
            
        try:
            # Check if the Forward rule exists
            run(['iptables', '-C', 'FORWARD', '-i', extif, '-o', intif,
                '-p', proto, '--dport', int_port, '-d', int_ip,
                '-j', 'ACCEPT'])
            # If yes, remove
            run(['iptables', '-D', 'FORWARD', '-i', extif, '-o', intif,
                '-p', proto, '--dport', int_port, '-d', int_ip,
                '-j', 'ACCEPT'])
        except RuntimeError:
            errors.append(f"{proto.upper()}-FORWARD rule not found")

    # User-friendly protocol name for the message
    proto_name = "TCP/UDP" if protocol == "both" else protocol.upper()
    
    # Inform the user
    if old_rules_count > len(rules):
        if errors:
            flash(f"Rule {proto_name} {extif}:{ext_port} → {int_ip}:{int_port} removed from configuration, but: {', '.join(errors)}")
        else:
            flash(f"Rule {proto_name} {extif}:{ext_port} → {int_ip}:{int_port} completely removed.")
    else:
        flash(f"Rule {proto_name} {extif}:{ext_port} → {int_ip}:{int_port} not found.")
        
    return redirect(url_for('index'))

@app.route('/enable', methods=['POST'])
def enable_rule():
    extif    = request.form['extif']
    intif    = request.form['intif']
    ext_port = request.form['ext_port']
    int_ip   = request.form['int_ip']
    int_port = request.form['int_port']
    protocol = request.form.get('protocol', 'both')  # Default is 'both' for backward compatibility
    
    # Update the rule in persistent storage
    rules = load_persisted_rules()
    for rule in rules:
        if (rule['extif'] == extif and rule['intif'] == intif and 
            rule['ext_port'] == ext_port and rule['int_ip'] == int_ip and 
            rule['int_port'] == int_port):
            # Enable the rule and set status to "enabled"
            rule['enabled'] = True
            try:
                apply_rule(rule)
                # User-friendly protocol name for the message
                proto_name = "TCP/UDP" if protocol == "both" else protocol.upper()
                flash(f"Rule {proto_name} {extif}:{ext_port} → {int_ip}:{int_port} enabled.")
            except RuntimeError as e:
                flash(f"Error enabling rule: {str(e)}")
            break
    
    save_persisted_rules(rules)
    return redirect(url_for('index'))

@app.route('/disable', methods=['POST'])
def disable_rule():
    extif    = request.form['extif']
    intif    = request.form['intif']
    ext_port = request.form['ext_port']
    int_ip   = request.form['int_ip']
    int_port = request.form['int_port']
    protocol = request.form.get('protocol', 'both')  # Default is 'both' for backward compatibility
    
    # Mark the rule as disabled in persistent storage
    rules = load_persisted_rules()
    for rule in rules:
        if (rule['extif'] == extif and rule['intif'] == intif and 
            rule['ext_port'] == ext_port and rule['int_ip'] == int_ip and 
            rule['int_port'] == int_port):
            # Set status to "disabled"
            rule['enabled'] = False
            
            # Determine which protocols to remove
            protocols = []
            if protocol == 'both':
                protocols = ['tcp', 'udp']
            else:
                protocols = [protocol]  # Only remove the selected protocol
                
            # Remove iptables rules
            errors = []
            for proto in protocols:
                try:
                    # Remove NAT rule
                    run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', extif,
                        '-p', proto, '--dport', ext_port,
                        '-j', 'DNAT', '--to-destination', f"{int_ip}:{int_port}"])
                except RuntimeError:
                    errors.append(f"{proto.upper()}-NAT rule not found")
                
                try:
                    # Remove Forward rule
                    run(['iptables', '-D', 'FORWARD', '-i', extif, '-o', intif,
                        '-p', proto, '--dport', int_port, '-d', int_ip,
                        '-j', 'ACCEPT'])
                except RuntimeError:
                    errors.append(f"{proto.upper()}-FORWARD rule not found")
            
            # User-friendly protocol name for the message
            proto_name = "TCP/UDP" if protocol == "both" else protocol.upper()
            
            if errors:
                flash(f"Rule {proto_name} {extif}:{ext_port} → {int_ip}:{int_port} disabled, but: {', '.join(errors)}")
            else:
                flash(f"Rule {proto_name} {extif}:{ext_port} → {int_ip}:{int_port} disabled.")
            break
    
    save_persisted_rules(rules)
    return redirect(url_for('index'))

if __name__ == '__main__':
    if not sys.platform.startswith('linux'):
        print("Only runs on Linux.")
        sys.exit(1)
        
    # Restore rules at startup, not just at the first request
    restore_persistent_rules()
    
    app.run(host='0.0.0.0', port=5000)
