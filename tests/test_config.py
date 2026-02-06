import tempfile
import unittest

from app import config


class TestConfig(unittest.TestCase):
    def test_ensure_data_dir_creates_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_data_dir = config.DATA_DIR
            original_rules_file = config.RULES_FILE
            config.DATA_DIR = tmpdir
            config.RULES_FILE = f"{tmpdir}/rules.json"
            try:
                config.ensure_data_dir()
                self.assertTrue(config.os.path.isdir(tmpdir))
            finally:
                config.DATA_DIR = original_data_dir
                config.RULES_FILE = original_rules_file

    def test_create_app_sets_secret_key(self):
        from app import create_app

        app_instance = create_app()
        self.assertTrue(app_instance.config.get("SECRET_KEY"))
