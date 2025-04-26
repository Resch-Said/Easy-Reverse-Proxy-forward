#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
portfw_gui.py

Ein einfaches Web-GUI für das Hinzufügen/Entfernen von TCP/UDP-Port-Forwarding-Regeln via iptables.
Benötigt: flask, netifaces
Installation:
    pip3 install flask netifaces

Aufruf:
    sudo python3 portfw_gui.py

Danach im Browser öffnen unter http://<VPS_IP>:5000
"""
from flask import Flask, request, redirect, url_for, render_template_string, flash
import subprocess
import netifaces
import sys

app = Flask(__name__)
app.secret_key = 'replace-with-secure-key'

# HTML-Template
TEMPLATE = '''
<!doctype html>
<html lang="de">
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
      <h2>Neue Regel hinzufügen</h2>
      <label>Externes Interface:
        <select name="extif">
          {% for iface in externals %}
            <option value="{{ iface }}">{{ iface }}</option>
          {% endfor %}
        </select>
      </label>
      <label>Internes WireGuard-Interface:
        <select name="intif">
          {% for iface in internals %}
            <option value="{{ iface }}">{{ iface }}</option>
          {% endfor %}
        </select>
      </label>
      <label>Externer Port: <input type="number" name="ext_port" min="1" max="65535" required></label>
      <label>Interne Ziel-IP: <input type="text" name="int_ip" placeholder="z.B. 192.168.178.84" required></label>
      <label>Interner Ziel-Port: <input type="number" name="int_port" min="1" max="65535" required></label>
      <button type="submit">Hinzufügen</button>
    </form>

    <h2>Aktuelle Regeln</h2>
    <table>
      <tr><th>Typ</th><th>Extern</th><th>Ziel</th><th>Aktion</th></tr>
      {% for r in rules %}
      <tr>
        <td>{{ r.proto.upper() }}</td>
        <td>{{ r.extif }}:{{ r.ext_port }}</td>
        <td>{{ r.int_ip }}:{{ r.int_port }}</td>
        <td>
          <form method="post" action="/del" style="display:inline;">
            <input type="hidden" name="extif" value="{{ r.extif }}">
            <input type="hidden" name="intif" value="{{ r.intif }}">
            <input type="hidden" name="ext_port" value="{{ r.ext_port }}">
            <input type="hidden" name="int_ip" value="{{ r.int_ip }}">
            <input type="hidden" name="int_port" value="{{ r.int_port }}">
            <input type="hidden" name="proto" value="{{ r.proto }}">
            <button type="submit">Entfernen</button>
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
        raise RuntimeError(f"Befehl fehlgeschlagen: {' '.join(cmd)}\n{e.output}")

@app.route('/')
def index():
    # Netzwerkschnittstellen ermitteln
    all_if = netifaces.interfaces()
    externals = [i for i in all_if if i != 'lo']
    internals = [i for i in all_if if i.startswith('wg')]

    # Regeln per iptables-save auslesen und parsen
    raw = run(['iptables-save', '-t', 'nat'])
    rules = []
    for line in raw.splitlines():
        if line.startswith('-A PREROUTING') and '-j DNAT' in line:
            parts = line.split()
            try:
                proto = parts[parts.index('-p') + 1]
                extif = parts[parts.index('-i') + 1]
                ext_port = parts[parts.index('--dport') + 1]
                dest = parts[parts.index('--to-destination') + 1]
                int_ip, int_port = dest.split(':')
            except (ValueError, IndexError):
                continue
            rules.append({
                'proto': proto,
                'extif': extif,
                'intif': None,
                'ext_port': ext_port,
                'int_ip': int_ip,
                'int_port': int_port
            })
    return render_template_string(TEMPLATE, externals=externals, internals=internals, rules=rules)

@app.route('/add', methods=['POST'])
def add():
    extif   = request.form['extif']
    intif   = request.form['intif']
    ext_port= request.form['ext_port']
    int_ip  = request.form['int_ip']
    int_port= request.form['int_port']
    try:
        run(['sysctl', '-w', 'net.ipv4.ip_forward=1'])
        # TCP
        run(['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', extif,
             '-p', 'tcp', '--dport', ext_port,
             '-j', 'DNAT', '--to-destination', f"{int_ip}:{int_port}"])
        run(['iptables', '-A', 'FORWARD', '-i', extif, '-o', intif,
             '-p', 'tcp', '--dport', int_port, '-d', int_ip,
             '-j', 'ACCEPT'])
        # UDP
        run(['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', extif,
             '-p', 'udp', '--dport', ext_port,
             '-j', 'DNAT', '--to-destination', f"{int_ip}:{int_port}"])
        run(['iptables', '-A', 'FORWARD', '-i', extif, '-o', intif,
             '-p', 'udp', '--dport', int_port, '-d', int_ip,
             '-j', 'ACCEPT'])
        # MASQUERADE
        run(['iptables', '-t', 'nat', '-C', 'POSTROUTING', '-o', intif, '-j', 'MASQUERADE'])
    except RuntimeError as e:
        flash(str(e))
        return redirect(url_for('index'))
    try:
        run(['iptables', '-t', 'nat', '-A', 'POSTROUTING', '-o', intif, '-j', 'MASQUERADE'])
    except RuntimeError:
        pass
    # Return packets
    try:
        run(['iptables', '-A', 'FORWARD', '-i', intif, '-o', extif,
             '-m', 'conntrack', '--ctstate', 'ESTABLISHED,RELATED',
             '-j', 'ACCEPT'])
    except RuntimeError:
        pass
    flash(f"Regel TCP/UDP {extif}:{ext_port} → {int_ip}:{int_port} hinzugefügt.")
    return redirect(url_for('index'))

@app.route('/del', methods=['POST'])
def delete():
    extif    = request.form['extif']
    intif    = request.form['intif']
    ext_port = request.form['ext_port']
    int_ip   = request.form['int_ip']
    int_port = request.form['int_port']
    proto    = request.form['proto']
    try:
        # Entfernen der NAT-Regel
        run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', extif,
             '-p', proto, '--dport', ext_port,
             '-j', 'DNAT', '--to-destination', f"{int_ip}:{int_port}"])
        
        # Entfernen der FORWARD-Regel nur, wenn intif einen gültigen Wert hat
        if intif and intif != "None":
            run(['iptables', '-D', 'FORWARD', '-i', extif, '-o', intif,
                 '-p', proto, '--dport', int_port, '-d', int_ip,
                 '-j', 'ACCEPT'])
    except RuntimeError as e:
        flash(str(e))
    else:
        flash(f"Regel {proto.upper()} {extif}:{ext_port} entfernt.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    if not sys.platform.startswith('linux'):
        print("Nur unter Linux lauffähig.")
        sys.exit(1)
    app.run(host='0.0.0.0', port=5000)
