from googleapiclient.discovery import build
from config.settings import Settings
from config.constants import YOUTUBE_ROTATION_ERRORS, YOUTUBE_ROTATION_HTTP_CODES
from utils.retry import with_retry
from utils.logger import get_logger

logger = get_logger()
settings = Settings.load()

class YouTubeCollector:
    @with_retry(rotator=settings.youtube_rotator, error_patterns=YOUTUBE_ROTATION_ERRORS, http_codes=YOUTUBE_ROTATION_HTTP_CODES)
    def collect_videos(self, channel_id: str, max_results: int = 20):
        if not settings.youtube_rotator:
            logger.warning("No YouTube keys configured.")
            return []
        
        api_key = settings.youtube_rotator.get_current_key()
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        request = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            maxResults=max_results,
            order="date",
            type="video"
        )
        response = request.execute()
        return response.get("items", [])
