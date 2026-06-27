import unittest
from collectors.competitor_discovery import CompetitorDiscovery

class TestCollectors(unittest.TestCase):
    def test_competitor_discovery(self):
        discovery = CompetitorDiscovery()
        results = discovery.discover_competitors("shoes", "instagram")
        self.assertEqual(len(results), 20)
        self.assertEqual(results[0]["username"], "competitor_0_instagram")

if __name__ == '__main__':
    unittest.main()
