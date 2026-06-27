import unittest
import os
from utils.cache import Cache
from utils.logger import get_logger

class TestUtils(unittest.TestCase):
    def test_logger(self):
        logger = get_logger()
        self.assertIsNotNone(logger)

    def test_cache(self):
        db_path = "test_cache2.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        cache = Cache(db_path, ttl_days=1)
        cache.set("test_key", {"data": "test"})
        val = cache.get("test_key")
        self.assertEqual(val, {"data": "test"})
        self.assertIsNone(cache.get("missing"))
        if os.path.exists(db_path):
            os.remove(db_path)

if __name__ == '__main__':
    unittest.main()
