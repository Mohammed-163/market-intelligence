"""
youtube_service.py
Single abstraction layer for YouTube Data API v3.
"""
from googleapiclient.discovery import build
from config.key_rotation import KeyRotator
from utils.logger import get_logger
from typing import List, Dict

logger = get_logger()


class YouTubeService:

    def __init__(self, rotator: KeyRotator):
        self.rotator = rotator

    def _build(self):
        return build("youtube", "v3", developerKey=self.rotator.get_current_key())

    def search_channel_videos(self, channel_id: str, max_results: int = 20) -> List[Dict]:
        try:
            resp = self._build().search().list(
                part="snippet",
                channelId=channel_id,
                maxResults=max_results,
                order="date",
                type="video",
            ).execute()
            return resp.get("items", [])
        except Exception as e:
            logger.error(f"YouTube search_channel_videos failed: {e}")
            return []

    def get_video_stats(self, video_ids: List[str]) -> List[Dict]:
        if not video_ids:
            return []
        try:
            resp = self._build().videos().list(
                part="statistics,snippet",
                id=",".join(video_ids[:50]),
            ).execute()
            return resp.get("items", [])
        except Exception as e:
            logger.error(f"YouTube get_video_stats failed: {e}")
            return []

    def get_comments(self, video_id: str, max_results: int = 100) -> List[Dict]:
        try:
            resp = self._build().commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(max_results, 100),
                order="relevance",
            ).execute()
            return [
                item["snippet"]["topLevelComment"]["snippet"]
                for item in resp.get("items", [])
            ]
        except Exception as e:
            logger.error(f"YouTube get_comments failed for {video_id}: {e}")
            return []
