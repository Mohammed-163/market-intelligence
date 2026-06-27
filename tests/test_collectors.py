import unittest
from collectors.competitor_discovery import CompetitorDiscovery

class TestCollectors(unittest.TestCase):
    def test_competitor_discovery(self):
        discovery = CompetitorDiscovery()
        results = discovery.discover_competitors("shoes", "instagram")
        self.assertIsInstance(results, list)

if __name__ == '__main__':
    unittest.main()
