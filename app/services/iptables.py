import subprocess


def run(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{exc.output}")


# Rule application logic (used for both adding and restoring rules)
def apply_rule(rule):
    extif = rule["extif"]
    intif = rule["intif"]
    ext_port = rule["ext_port"]
    int_ip = rule["int_ip"]
    int_port = rule["int_port"]
    protocol = rule.get("protocol", "both")  # Default to 'both' for backward compatibility

    # Enable IP forwarding
    run(["sysctl", "-w", "net.ipv4.ip_forward=1"])

    # Determine which protocols to apply
    protocols = []
    if protocol == "both":
        protocols = ["tcp", "udp"]
    else:
        protocols = [protocol]  # Only apply the selected protocol

    for proto in protocols:
        # NAT PREROUTING
        try:
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
        except RuntimeError:
            run(
                [
                    "iptables",
                    "-t",
                    "nat",
                    "-A",
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
            # FORWARD
            run(
                [
                    "iptables",
                    "-A",
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
    # MASQUERADE on internal interface
    try:
        run(["iptables", "-t", "nat", "-C", "POSTROUTING", "-o", intif, "-j", "MASQUERADE"])
    except RuntimeError:
        run(["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", intif, "-j", "MASQUERADE"])
    # Return route (ESTABLISHED)
    try:
        run(
            [
                "iptables",
                "-C",
                "FORWARD",
                "-i",
                intif,
                "-o",
                extif,
                "-m",
                "conntrack",
                "--ctstate",
                "ESTABLISHED,RELATED",
                "-j",
                "ACCEPT",
            ]
        )
    except RuntimeError:
        run(
            [
                "iptables",
                "-A",
                "FORWARD",
                "-i",
                intif,
                "-o",
                extif,
                "-m",
                "conntrack",
                "--ctstate",
                "ESTABLISHED,RELATED",
                "-j",
                "ACCEPT",
            ]
        )
