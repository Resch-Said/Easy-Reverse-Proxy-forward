import json
import os

from app.config import RULES_FILE
from app.services.iptables import apply_rule, run


# Persistence functions
def load_persisted_rules():
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, "r") as handle:
            return json.load(handle)
    return []


def save_persisted_rules(rules):
    try:
        with open(RULES_FILE, "w") as handle:
            json.dump(rules, handle, indent=2)
        print(f"✓ Rules saved successfully to {RULES_FILE}")
    except Exception as exc:
        print(f"✗ ERROR saving rules to {RULES_FILE}: {exc}")
        raise RuntimeError(f"Failed to save rules: {exc}")


def restore_persistent_rules():
    print("Restoring persistent rules...")
    rules = load_persisted_rules()
    print(f"Found rules: {len(rules)}")
    for rule in rules:
        # Only restore active rules
        if rule.get("enabled", True):  # Default is active for backward compatibility
            try:
                # First delete any existing rules to avoid duplicates
                try:
                    for proto in ("tcp", "udp"):
                        # Delete NAT rule
                        run(
                            [
                                "iptables",
                                "-t",
                                "nat",
                                "-D",
                                "PREROUTING",
                                "-i",
                                rule["extif"],
                                "-p",
                                proto,
                                "--dport",
                                rule["ext_port"],
                                "-j",
                                "DNAT",
                                "--to-destination",
                                f"{rule['int_ip']}:{rule['int_port']}",
                            ]
                        )
                        # Delete Forward rule
                        run(
                            [
                                "iptables",
                                "-D",
                                "FORWARD",
                                "-i",
                                rule["extif"],
                                "-o",
                                rule["intif"],
                                "-p",
                                proto,
                                "--dport",
                                rule["int_port"],
                                "-d",
                                rule["int_ip"],
                                "-j",
                                "ACCEPT",
                            ]
                        )
                except RuntimeError:
                    # Ignore if the rules do not exist
                    pass

                # Then add new rules
                apply_rule(rule)
                print(
                    "Rule restored: "
                    f"{rule['extif']}:{rule['ext_port']} → "
                    f"{rule['int_ip']}:{rule['int_port']}"
                )
            except RuntimeError as exc:
                print(f"Error restoring rule: {str(exc)}")
        else:
            print(
                "Rule skipped (disabled): "
                f"{rule['extif']}:{rule['ext_port']} → "
                f"{rule['int_ip']}:{rule['int_port']}"
            )
