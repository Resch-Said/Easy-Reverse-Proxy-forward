import json
import tempfile
import unittest

from app.services import persistence


class TestPersistence(unittest.TestCase):
    def test_save_and_load_rules(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = f"{tmpdir}/rules.json"
            original_rules_file = persistence.RULES_FILE
            persistence.RULES_FILE = rules_path
            try:
                rules = [{"extif": "eth0", "intif": "wg0"}]
                persistence.save_persisted_rules(rules)
                loaded = persistence.load_persisted_rules()
                self.assertEqual(rules, loaded)
            finally:
                persistence.RULES_FILE = original_rules_file

    def test_restore_persistent_rules_skips_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = f"{tmpdir}/rules.json"
            rules = [
                {
                    "extif": "eth0",
                    "intif": "wg0",
                    "ext_port": "80",
                    "int_ip": "10.0.0.2",
                    "int_port": "8080",
                    "protocol": "both",
                    "enabled": True,
                },
                {
                    "extif": "eth1",
                    "intif": "wg1",
                    "ext_port": "22",
                    "int_ip": "10.0.0.3",
                    "int_port": "22",
                    "protocol": "both",
                    "enabled": False,
                },
            ]
            with open(rules_path, "w") as handle:
                json.dump(rules, handle)

            original_rules_file = persistence.RULES_FILE
            original_apply_rule = persistence.apply_rule
            original_run = persistence.run
            calls = {"apply_rule": [], "run": []}

            def fake_apply_rule(rule):
                calls["apply_rule"].append(rule)

            def fake_run(cmd):
                calls["run"].append(cmd)
                return ""

            persistence.RULES_FILE = rules_path
            persistence.apply_rule = fake_apply_rule
            persistence.run = fake_run
            try:
                persistence.restore_persistent_rules()
            finally:
                persistence.RULES_FILE = original_rules_file
                persistence.apply_rule = original_apply_rule
                persistence.run = original_run

            self.assertEqual(1, len(calls["apply_rule"]))
            self.assertEqual("eth0", calls["apply_rule"][0]["extif"])
