import unittest

from app.services import iptables


class TestIptablesApplyRule(unittest.TestCase):
    def test_apply_rule_uses_both_protocols(self):
        calls = []

        def fake_run(cmd):
            calls.append(cmd)
            return ""

        original_run = iptables.run
        iptables.run = fake_run
        try:
            iptables.apply_rule(
                {
                    "extif": "eth0",
                    "intif": "wg0",
                    "ext_port": "443",
                    "int_ip": "10.0.0.2",
                    "int_port": "8443",
                    "protocol": "both",
                }
            )
        finally:
            iptables.run = original_run

        self.assertTrue(any(cmd[:2] == ["sysctl", "-w"] for cmd in calls))
        tcp_nat_check = [
            "iptables",
            "-t",
            "nat",
            "-C",
            "PREROUTING",
            "-i",
            "eth0",
            "-p",
            "tcp",
            "--dport",
            "443",
            "-j",
            "DNAT",
            "--to-destination",
            "10.0.0.2:8443",
        ]
        udp_nat_check = tcp_nat_check.copy()
        udp_nat_check[8] = "udp"
        self.assertIn(tcp_nat_check, calls)
        self.assertIn(udp_nat_check, calls)
