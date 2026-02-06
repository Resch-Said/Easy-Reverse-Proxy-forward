import unittest
from unittest import mock

from app import create_app


class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_add_rule_persists_rule(self):
        with (
            mock.patch("app.routes.apply_rule"),
            mock.patch("app.routes.load_persisted_rules", return_value=[]),
            mock.patch("app.routes.save_persisted_rules") as save_rules,
        ):
            response = self.client.post(
                "/add",
                data={
                    "extif": "eth0",
                    "intif": "wg0",
                    "ext_port": "443",
                    "int_ip": "10.0.0.2",
                    "int_port": "8443",
                    "protocol": "both",
                    "name": "test",
                },
            )

        self.assertEqual(302, response.status_code)
        saved_rules = save_rules.call_args[0][0]
        self.assertEqual(1, len(saved_rules))
        self.assertEqual("eth0", saved_rules[0]["extif"])
        self.assertEqual("test", saved_rules[0]["name"])

    def test_index_renders_template(self):
        with (
            mock.patch("app.routes.netifaces.interfaces", return_value=["lo", "eth0"]),
            mock.patch("app.routes.load_persisted_rules", return_value=[]),
        ):
            response = self.client.get("/")

        self.assertEqual(200, response.status_code)

    def test_add_rule_handles_apply_error(self):
        with (
            mock.patch("app.routes.apply_rule", side_effect=RuntimeError("boom")),
            mock.patch("app.routes.load_persisted_rules", return_value=[]),
            mock.patch("app.routes.save_persisted_rules") as save_rules,
        ):
            response = self.client.post(
                "/add",
                data={
                    "extif": "eth0",
                    "intif": "wg0",
                    "ext_port": "443",
                    "int_ip": "10.0.0.2",
                    "int_port": "8443",
                    "protocol": "tcp",
                },
            )

        self.assertEqual(302, response.status_code)
        save_rules.assert_not_called()

    def test_delete_rule_updates_rules(self):
        rule = {
            "extif": "eth0",
            "intif": "wg0",
            "ext_port": "443",
            "int_ip": "10.0.0.2",
            "int_port": "8443",
            "protocol": "both",
        }
        with (
            mock.patch("app.routes.load_persisted_rules", return_value=[rule]),
            mock.patch("app.routes.save_persisted_rules") as save_rules,
            mock.patch("app.routes.run"),
        ):
            response = self.client.post("/del", data=rule)

        self.assertEqual(302, response.status_code)
        self.assertEqual([], save_rules.call_args[0][0])

    def test_enable_rule_sets_enabled(self):
        rule = {
            "extif": "eth0",
            "intif": "wg0",
            "ext_port": "443",
            "int_ip": "10.0.0.2",
            "int_port": "8443",
            "protocol": "tcp",
            "enabled": False,
        }
        with (
            mock.patch("app.routes.load_persisted_rules", return_value=[rule]),
            mock.patch("app.routes.save_persisted_rules") as save_rules,
            mock.patch("app.routes.apply_rule"),
        ):
            response = self.client.post("/enable", data=rule)

        self.assertEqual(302, response.status_code)
        updated_rules = save_rules.call_args[0][0]
        self.assertTrue(updated_rules[0]["enabled"])

    def test_disable_rule_sets_disabled(self):
        rule = {
            "extif": "eth0",
            "intif": "wg0",
            "ext_port": "443",
            "int_ip": "10.0.0.2",
            "int_port": "8443",
            "protocol": "both",
            "enabled": True,
        }
        with (
            mock.patch("app.routes.load_persisted_rules", return_value=[rule]),
            mock.patch("app.routes.save_persisted_rules") as save_rules,
            mock.patch("app.routes.run"),
        ):
            response = self.client.post("/disable", data=rule)

        self.assertEqual(302, response.status_code)
        updated_rules = save_rules.call_args[0][0]
        self.assertFalse(updated_rules[0]["enabled"])
