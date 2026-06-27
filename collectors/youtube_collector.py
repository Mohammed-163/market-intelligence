from googleapiclient.discovery import build
from config.secrets_manager import SecretsManager
from config.key_rotation import KeyRotator
from config.constants import YOUTUBE_ROTATION_ERRORS, YOUTUBE_ROTATION_HTTP_CODES, POOL_YOUTUBE, MAX_VIDEOS
from utils.retry import with_retry
from utils.logger import get_logger

logger = get_logger()


class YouTubeCollector:
    # BUG FIX: Settings.load() was at module level.
    def __init__(self):
        secrets = SecretsManager.load()
        self.rotator = (
            KeyRotator(POOL_YOUTUBE, secrets.youtube_keys)
            if secrets.youtube_keys else None
        )

    def collect_videos(self, channel_id: str, max_results: int = MAX_VIDEOS) -> dict:
        if not self.rotator:
            logger.warning("No YouTube keys configured. Skipping YouTube collection.")
            return {"raw_data": [], "account": None, "posts": [], "comments": []}
            
        raw_data = self._collect(channel_id, max_results)
        
        from models.account import Account
        from models.post import Post
        
        account = None
        posts = []
        
        if raw_data:
            first = raw_data[0].get("snippet", {})
            account = Account(
                platform="youtube",
                username=first.get("channelTitle", channel_id),
                followers=None,
                following=None,
                posts_count=None,
                bio=None
            )
            
            for item in raw_data:
                snippet = item.get("snippet", {})
                id_info = item.get("id", {})
                post = Post(
                    post_id=id_info.get("videoId", ""),
                    caption=snippet.get("title", ""),
                    likes=None,
                    comments=None,
                    views=None,
                    posted_at=snippet.get("publishedAt"),
                    type="video"
                )
                posts.append(post)
                
        return {
            "raw_data": raw_data,
            "account": account,
            "posts": posts,
            "comments": []
        }

    @with_retry(error_patterns=YOUTUBE_ROTATION_ERRORS, http_codes=YOUTUBE_ROTATION_HTTP_CODES)
    def _collect(self, channel_id: str, max_results: int) -> list:
        yt   = build("youtube", "v3", developerKey=self.rotator.get_current_key())
        resp = yt.search().list(
            part="snippet", channelId=channel_id,
            maxResults=max_results, order="date", type="video",
        ).execute()
        return resp.get("items", [])
