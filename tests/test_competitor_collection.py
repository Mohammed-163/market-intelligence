import unittest
from unittest.mock import patch, MagicMock
from collectors.competitor_discovery import CompetitorDiscovery
from models.competitor import Competitor

class TestCompetitorCollection(unittest.TestCase):
    def setUp(self):
        # Prevent actually loading settings and crashing if no env vars exist
        with patch('config.settings.Settings.load') as mock_load:
            mock_settings = MagicMock()
            mock_settings.youtube_rotator = MagicMock()
            mock_settings.apify_rotator = MagicMock()
            mock_load.return_value = mock_settings
            self.discovery = CompetitorDiscovery()

    @patch('collectors.competitor_discovery.CompetitorDiscovery._discover_youtube')
    @patch('collectors.youtube_collector.YouTubeCollector.collect_videos')
    def test_youtube_deep_collection(self, mock_collect_videos, mock_discover_youtube):
        # Setup mock discovery response
        comp1 = Competitor(username="channel1", platform="youtube", followers=100)
        comp2 = Competitor(username="channel2", platform="youtube", followers=200)
        mock_discover_youtube.return_value = {
            "raw_data": ["raw_chan1", "raw_chan2"],
            "competitors": [comp1, comp2]
        }
        
        # Setup mock deep collection response
        mock_collect_videos.side_effect = [
            {
                "normalized_account": {"followers": 150, "bio": "Bio 1", "profile_pic_url": "pic1.jpg"},
                "normalized_posts": [{"id": "vid1"}, {"id": "vid2"}]
            },
            {
                "normalized_account": {"followers": 250, "bio": "Bio 2", "profile_pic_url": "pic2.jpg"},
                "normalized_posts": [{"id": "vid3"}]
            }
        ]
        
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        
        # Execute
        result = self.discovery.discover_competitors("tech", "youtube", cache=mock_cache)
        
        # Verify basic logic
        self.assertEqual(len(result["competitors"]), 2)
        c1, c2 = result["competitors"]
        
        # Verify enrichment
        self.assertEqual(c1.followers, 150)
        self.assertEqual(c1.bio, "Bio 1")
        self.assertEqual(c1.profile_pic_url, "pic1.jpg")
        self.assertEqual(len(c1.sample_posts), 2)
        
        self.assertEqual(c2.followers, 250)
        self.assertEqual(len(c2.sample_posts), 1)
        
        # Verify cache was called properly
        self.assertEqual(mock_collect_videos.call_count, 2)
        mock_collect_videos.assert_any_call("channel1", max_results=5, cache=mock_cache)
        
        # Verify discovery result was cached
        mock_cache.set.assert_called_once()
        args, _ = mock_cache.set.call_args
        self.assertEqual(args[0], "competitors:youtube:tech")
        self.assertEqual(len(args[1]["competitors"]), 2)
        self.assertEqual(args[1]["competitors"][0]["bio"], "Bio 1") # Ensures enriched data is cached!

    @patch('collectors.competitor_discovery.CompetitorDiscovery._discover_instagram')
    @patch('collectors.instagram_collector.InstagramCollector.collect_posts')
    @patch('config.constants.MAX_COMPETITOR_DEEP_COLLECTION', 1)
    def test_instagram_limit_enforcement(self, mock_collect_posts, mock_discover_instagram):
        # Setup mock discovery response with 3 competitors
        comps = [
            Competitor(username="ig1", platform="instagram"),
            Competitor(username="ig2", platform="instagram"),
            Competitor(username="ig3", platform="instagram")
        ]
        mock_discover_instagram.return_value = {
            "raw_data": [],
            "competitors": comps
        }
        
        # Setup mock deep collection
        mock_collect_posts.return_value = {
            "normalized_account": {"bio": "Deep Enriched"},
            "normalized_posts": []
        }
        
        # Execute
        # Note: We mocked MAX_COMPETITOR_DEEP_COLLECTION to 1.
        with patch('collectors.competitor_discovery.MAX_COMPETITOR_DEEP_COLLECTION', 1):
            result = self.discovery.discover_competitors("tech", "instagram")
        
        # Verify
        self.assertEqual(len(result["competitors"]), 3)
        self.assertEqual(mock_collect_posts.call_count, 1) # Only 1 should be deep collected!
        
        c1, c2, c3 = result["competitors"]
        self.assertEqual(c1.bio, "Deep Enriched")
        self.assertIsNone(c2.bio) # Not enriched
        self.assertIsNone(c3.bio) # Not enriched

    def test_tiktok_unsupported(self):
        result = self.discovery.discover_competitors("tech", "tiktok")
        self.assertFalse(result.get("supported", True))
        self.assertIn("not supported", result.get("reason", ""))

    def test_cache_hit(self):
        mock_cache = MagicMock()
        mock_cache.get.return_value = {"cached": "data"}
        
        result = self.discovery.discover_competitors("tech", "youtube", cache=mock_cache)
        
        self.assertEqual(result, {"cached": "data"})
        mock_cache.get.assert_called_with("competitors:youtube:tech")

if __name__ == '__main__':
    unittest.main()
