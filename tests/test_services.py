import unittest
from unittest.mock import MagicMock, patch
from services.report_service import ReportService

class TestReportService(unittest.TestCase):
    def setUp(self):
        self.service = ReportService(output_dir="/tmp/test_reports")

    def test_build_report(self):
        data = {
            "platform": "instagram",
            "profile": {"followersCount": 5000},
            "engagement": {"er_percent": 3.5},
            "content": {},
            "sentiment": {"positive": 70.0, "neutral": 20.0, "negative": 10.0, "total": 100},
            "competitors": {},
            "activity": {},
        }
        report = self.service.build(data, "test_account")
        self.assertEqual(report["account"], "test_account")
        self.assertEqual(report["platform"], "instagram")
        self.assertIn("generated_at", report)

    def test_save_json(self):
        import os, json
        report = {"account": "test", "platform": "instagram", "generated_at": "now"}
        path = self.service.save_json(report, "unit_test_report")
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            loaded = json.load(f)
        self.assertEqual(loaded["account"], "test")
        os.remove(path)

if __name__ == "__main__":
    unittest.main()
