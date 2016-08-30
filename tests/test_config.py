"""
Goal: Test config class exceptions

Authors:
     Andrei Sura <sura.andrei@gmail.com>
"""
import unittest
import logging
# from olass.config import Config
from olass.olass_client import ConfigErr
from olass.olass_client import OlassClient

lformat = '%(name)s.%(levelname)s ' \
    '- %(filename)s+%(lineno)d: %(message)s'
logging.basicConfig(format=lformat, level=logging.INFO)
log = logging.getLogger(__name__)


# class TestConfig(BaseTestCase):
class TestConfig(unittest.TestCase):

    def test_config_constructor(self):
        # missing_all = {}
        # config = Config(root_path='.', defaults=missing_all)
        app = OlassClient(config_file='config/settings_tests.py',
                          interactive=False)

        app.config.from_dictionary({"ENABLED_RULES": ['missing_rule']})
        self.assertRaisesRegexp(ConfigErr, "Invalid rule", app.validate_config)

        app.config.from_dictionary({"ENABLED_RULES": None})
        self.assertRaisesRegexp(ConfigErr, "ENABLED_RULES", app.validate_config)  # NOQA

        app.config.from_dictionary({"SALT": 'abc'})
        self.assertRaisesRegexp(ConfigErr, "64 characters", app.validate_config)  # NOQA

        app.config.from_dictionary({"SALT": None})
        self.assertRaisesRegexp(ConfigErr, "SALT", app.validate_config)

        app.config.from_dictionary({'DB_PASS': None})
        self.assertRaisesRegexp(ConfigErr, "DB_PASS", app.validate_config)

        app.config.from_dictionary({'DB_USER': None})
        self.assertRaisesRegexp(ConfigErr, "DB_USER", app.validate_config)

        app.config.from_dictionary({'DB_PORT': None})
        self.assertRaisesRegexp(ConfigErr, "DB_PORT", app.validate_config)

        app.config.from_dictionary({'DB_HOST': None})
        self.assertRaisesRegexp(ConfigErr, "DB_HOST", app.validate_config)

        app.config.from_dictionary({'DB_TYPE': None})
        self.assertRaisesRegexp(ConfigErr, "DB_TYPE", app.validate_config)

        app.config.from_dictionary({"SAVE_URL": None})
        self.assertRaisesRegexp(ConfigErr, "SAVE_URL", app.validate_config)

        app.config.from_dictionary({"TOKEN_URL": None})
        self.assertRaisesRegexp(ConfigErr, "TOKEN_URL", app.validate_config)

        app.config.from_dictionary({"CLIENT_SECRET": None})
        self.assertRaisesRegexp(ConfigErr, "CLIENT_SECRET", app.validate_config)  # NOQA

        app.config.from_dictionary({"CLIENT_ID": None})
        self.assertRaisesRegexp(ConfigErr, "CLIENT_ID", app.validate_config)
