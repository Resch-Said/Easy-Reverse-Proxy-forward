import traceback

import netifaces
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.services.iptables import apply_rule, run
from app.services.persistence import load_persisted_rules, save_persisted_rules

web = Blueprint("web", __name__)


@web.route("/")
def index():
    # Network interfaces
    all_if = netifaces.interfaces()
    externals = [interface for interface in all_if if interface != "lo"]
    internals = [
        interface
        for interface in all_if
        if interface.startswith(("wg", "tun", "tap", "tailscale"))
    ]
    # Display persistent rules
    rules = load_persisted_rules()
    return render_template("index.html", externals=externals, internals=internals, rules=rules)


@web.route("/add", methods=["POST"])
def add():
    try:
        extif = request.form["extif"]
        intif = request.form["intif"]
        ext_port = request.form["ext_port"]
        int_ip = request.form["int_ip"]
        int_port = request.form["int_port"]
        protocol = request.form["protocol"]  # 'both', 'tcp', or 'udp'
        name = request.form.get("name", "").strip()

        new_rule = {
            "extif": extif,
            "intif": intif,
            "ext_port": ext_port,
            "int_ip": int_ip,
            "int_port": int_port,
            "protocol": protocol,
        }
        if name:
            new_rule["name"] = name

        try:
            apply_rule(new_rule)
        except RuntimeError as exc:
            flash(f"Error applying iptables rule: {str(exc)}")
            return redirect(url_for("web.index"))

        # Update persistence
        rules = load_persisted_rules()

        # Check if the rule already exists (without considering the new protocol field)
        existing_rule = None
        for rule in rules:
            if (
                rule["extif"] == extif
                and rule["intif"] == intif
                and rule["ext_port"] == ext_port
                and rule["int_ip"] == int_ip
                and rule["int_port"] == int_port
            ):
                existing_rule = rule
                break

        if existing_rule:
            # Update existing rule with the new protocol
            existing_rule["protocol"] = protocol
            if name:
                existing_rule["name"] = name
        else:
            # Add new rule
            rules.append(new_rule)

        save_persisted_rules(rules)

        # User-friendly protocol name for the message
        proto_name = "TCP/UDP" if protocol == "both" else protocol.upper()
        flash(f"Rule {proto_name} {extif}:{ext_port} → {int_ip}:{int_port} added.")

    except Exception as exc:
        print(f"✗ ERROR in /add route: {exc}")
        traceback.print_exc()
        flash(f"Error adding rule: {str(exc)}")

    return redirect(url_for("web.index"))


@web.route("/del", methods=["POST"])
def delete():
    extif = request.form["extif"]
    intif = request.form["intif"]
    ext_port = request.form["ext_port"]
    int_ip = request.form["int_ip"]
    int_port = request.form["int_port"]
    protocol = request.form.get("protocol", "both")  # Default is 'both' for backward compatibility

    # Update persistence first - always remove the rule from the JSON
    rules = load_persisted_rules()
    old_rules_count = len(rules)
    rules = [
        rule
        for rule in rules
        if not (
            rule["extif"] == extif
            and rule["intif"] == intif
            and rule["ext_port"] == ext_port
            and rule["int_ip"] == int_ip
            and rule["int_port"] == int_port
        )
    ]
    save_persisted_rules(rules)

    # Determine which protocols to remove
    protocols = []
    if protocol == "both":
        protocols = ["tcp", "udp"]
    else:
        protocols = [protocol]  # Only remove the selected protocol

    # Now try to remove the iptables rules
    errors = []
    for proto in protocols:
        try:
            # Check if the rule exists before we delete it
            run(
                [
                    "iptables",
                    "-t",
                    "nat",
                    "-C",
                    "PREROUTING",
                    "-i",
                    extif,
                    "-p",
                    proto,
                    "--dport",
                    ext_port,
                    "-j",
                    "DNAT",
                    "--to-destination",
                    f"{int_ip}:{int_port}",
                ]
            )
            # If yes, remove
            run(
                [
                    "iptables",
                    "-t",
                    "nat",
                    "-D",
                    "PREROUTING",
                    "-i",
                    extif,
                    "-p",
                    proto,
                    "--dport",
                    ext_port,
                    "-j",
                    "DNAT",
                    "--to-destination",
                    f"{int_ip}:{int_port}",
                ]
            )
        except RuntimeError:
            errors.append(f"{proto.upper()}-NAT rule not found")

        try:
            # Check if the Forward rule exists
            run(
                [
                    "iptables",
                    "-C",
                    "FORWARD",
                    "-i",
                    extif,
                    "-o",
                    intif,
                    "-p",
                    proto,
                    "--dport",
                    int_port,
                    "-d",
                    int_ip,
                    "-j",
                    "ACCEPT",
                ]
            )
            # If yes, remove
            run(
                [
                    "iptables",
                    "-D",
                    "FORWARD",
                    "-i",
                    extif,
                    "-o",
                    intif,
                    "-p",
                    proto,
                    "--dport",
                    int_port,
                    "-d",
                    int_ip,
                    "-j",
                    "ACCEPT",
                ]
            )
        except RuntimeError:
            errors.append(f"{proto.upper()}-FORWARD rule not found")

    # User-friendly protocol name for the message
    proto_name = "TCP/UDP" if protocol == "both" else protocol.upper()

    # Inform the user
    if old_rules_count > len(rules):
        if errors:
            flash(
                f"Rule {proto_name} {extif}:{ext_port} → {int_ip}:{int_port} removed from "
                f"configuration, but: {', '.join(errors)}"
            )
        else:
            flash(f"Rule {proto_name} {extif}:{ext_port} → {int_ip}:{int_port} completely removed.")
    else:
        flash(f"Rule {proto_name} {extif}:{ext_port} → {int_ip}:{int_port} not found.")

    return redirect(url_for("web.index"))


@web.route("/enable", methods=["POST"])
def enable_rule():
    extif = request.form["extif"]
    intif = request.form["intif"]
    ext_port = request.form["ext_port"]
    int_ip = request.form["int_ip"]
    int_port = request.form["int_port"]
    protocol = request.form.get("protocol", "both")  # Default is 'both' for backward compatibility

    # Update the rule in persistent storage
    rules = load_persisted_rules()
    for rule in rules:
        if (
            rule["extif"] == extif
            and rule["intif"] == intif
            and rule["ext_port"] == ext_port
            and rule["int_ip"] == int_ip
            and rule["int_port"] == int_port
        ):
            # Enable the rule and set status to "enabled"
            rule["enabled"] = True
            try:
                apply_rule(rule)
                # User-friendly protocol name for the message
                proto_name = "TCP/UDP" if protocol == "both" else protocol.upper()
                flash(f"Rule {proto_name} {extif}:{ext_port} → {int_ip}:{int_port} enabled.")
            except RuntimeError as exc:
                flash(f"Error enabling rule: {str(exc)}")
            break

    save_persisted_rules(rules)
    return redirect(url_for("web.index"))


@web.route("/disable", methods=["POST"])
def disable_rule():
    extif = request.form["extif"]
    intif = request.form["intif"]
    ext_port = request.form["ext_port"]
    int_ip = request.form["int_ip"]
    int_port = request.form["int_port"]
    protocol = request.form.get("protocol", "both")  # Default is 'both' for backward compatibility

    # Mark the rule as disabled in persistent storage
    rules = load_persisted_rules()
    for rule in rules:
        if (
            rule["extif"] == extif
            and rule["intif"] == intif
            and rule["ext_port"] == ext_port
            and rule["int_ip"] == int_ip
            and rule["int_port"] == int_port
        ):
            # Set status to "disabled"
            rule["enabled"] = False

            # Determine which protocols to remove
            protocols = []
            if protocol == "both":
                protocols = ["tcp", "udp"]
            else:
                protocols = [protocol]  # Only remove the selected protocol

            # Remove iptables rules
            errors = []
            for proto in protocols:
                try:
                    # Remove NAT rule
                    run(
                        [
                            "iptables",
                            "-t",
                            "nat",
                            "-D",
                            "PREROUTING",
                            "-i",
                            extif,
                            "-p",
                            proto,
                            "--dport",
                            ext_port,
                            "-j",
                            "DNAT",
                            "--to-destination",
                            f"{int_ip}:{int_port}",
                        ]
                    )
                except RuntimeError:
                    errors.append(f"{proto.upper()}-NAT rule not found")

                try:
                    # Remove Forward rule
                    run(
                        [
                            "iptables",
                            "-D",
                            "FORWARD",
                            "-i",
                            extif,
                            "-o",
                            intif,
                            "-p",
                            proto,
                            "--dport",
                            int_port,
                            "-d",
                            int_ip,
                            "-j",
                            "ACCEPT",
                        ]
                    )
                except RuntimeError:
                    errors.append(f"{proto.upper()}-FORWARD rule not found")

            # User-friendly protocol name for the message
            proto_name = "TCP/UDP" if protocol == "both" else protocol.upper()

            if errors:
                flash(
                    f"Rule {proto_name} {extif}:{ext_port} → {int_ip}:{int_port} disabled, but: "
                    f"{', '.join(errors)}"
                )
            else:
                flash(f"Rule {proto_name} {extif}:{ext_port} → {int_ip}:{int_port} disabled.")
            break

    save_persisted_rules(rules)
    return redirect(url_for("web.index"))
