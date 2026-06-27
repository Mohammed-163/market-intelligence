import unittest
from analyzers.engagement_analyzer import EngagementAnalyzer
from analyzers.content_analyzer import ContentAnalyzer
from analyzers.account_analyzer import AccountAnalyzer

FAKE_POSTS = [
    {"likesCount": 100, "commentsCount": 10, "type": "image", "timestamp": "2024-01-01T10:00:00Z"},
    {"likesCount": 200, "commentsCount": 20, "type": "video", "timestamp": "2024-01-03T14:00:00Z"},
    {"likesCount":  50, "commentsCount":  5, "type": "image", "timestamp": "2024-01-05T18:00:00Z"},
]

class TestEngagementAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = EngagementAnalyzer()

    def test_calculate_er(self):
        er = self.analyzer.calculate_er(10_000, FAKE_POSTS)
        self.assertGreater(er, 0)

    def test_avg_likes(self):
        avg = self.analyzer.avg_likes(FAKE_POSTS)
        self.assertAlmostEqual(avg, (100 + 200 + 50) / 3, places=1)

    def test_empty_posts(self):
        self.assertEqual(self.analyzer.calculate_er(1000, []), 0.0)

class TestContentAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = ContentAnalyzer()

    def test_analyze_by_type(self):
        result = self.analyzer.analyze_by_type(FAKE_POSTS)
        self.assertIn("best_type", result)
        self.assertEqual(result["best_type"], "video")

    def test_posting_times(self):
        result = self.analyzer.analyze_posting_times(FAKE_POSTS)
        self.assertIn("best_hour", result)

class TestAccountAnalyzer(unittest.TestCase):
    def test_growth(self):
        result = AccountAnalyzer().analyze_growth(12000, 10000)
        self.assertEqual(result["growth_rate"], 20.0)

    def test_activity(self):
        result = AccountAnalyzer().analyze_activity(FAKE_POSTS)
        self.assertGreater(result["avg_per_week"], 0)

if __name__ == "__main__":
    unittest.main()
