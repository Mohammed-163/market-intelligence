import unittest
from config.secrets_manager import SecretsManager

class TestConfig(unittest.TestCase):
    def test_secrets_manager(self):
        secrets = SecretsManager.load()
        self.assertIsNotNone(secrets)

if __name__ == '__main__':
    unittest.main()
