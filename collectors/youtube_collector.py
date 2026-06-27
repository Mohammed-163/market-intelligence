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

    def _resolve_channel_id(self, identifier: str) -> str:
        identifier = identifier.strip()
        # If it's already a UC... ID
        if identifier.startswith('UC') and len(identifier) == 24:
            return identifier
            
        # Extract handle from URL or @
        if 'youtube.com' in identifier or 'youtu.be' in identifier:
            import re
            match = re.search(r'(?:youtube\.com\/(?:@|c\/|user\/|channel\/)?|youtu\.be\/)([\w-]+)', identifier)
            if match:
                identifier = match.group(1)
        
        # If it's a handle, search for it
        if not identifier.startswith('UC') or len(identifier) != 24:
            if not self.rotator:
                return identifier
            try:
                from googleapiclient.discovery import build
                api_key = self.rotator.get_current_key()
                youtube = build('youtube', 'v3', developerKey=api_key)
                # Ensure the search term starts with @ if it's likely a handle
                search_term = identifier if identifier.startswith('@') else f"@{identifier}"
                request = youtube.search().list(part="snippet", q=search_term, type="channel", maxResults=1)
                response = request.execute()
                items = response.get("items", [])
                if items:
                    return items[0]["id"]["channelId"]
            except Exception as e:
                logger.warning(f"Failed to resolve channel handle {identifier}: {e}")
                
        return identifier

    def collect_videos(self, channel_id: str, max_results: int = MAX_VIDEOS, cache=None) -> dict:
        if not self.rotator:
            logger.warning("No YouTube keys configured. Skipping YouTube collection.")
            return {}
            
        resolved_id = self._resolve_channel_id(channel_id)
            
        cache_key = f"youtube:{resolved_id.strip().lower()}:{max_results}"
        raw_data = None
        if cache:
            try:
                raw_data = cache.get(cache_key)
                if raw_data is not None:
                    logger.info(f"Cache hit for YouTube channel '{channel_id}' — skipping API call.")
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

        if raw_data is None:
            raw_data = self._collect(resolved_id, max_results)
            if cache and raw_data and raw_data.get("videos"):
                try:
                    cache.set(cache_key, raw_data)
                except Exception as e:
                    logger.warning(f"Cache write failed: {e}")
        videos_raw = raw_data.get("videos", [])
        comments_raw = raw_data.get("comments", [])
        
        from models.account import Account
        from models.post import Post
        from models.comment import Comment
        from datetime import datetime, timezone
        
        account = None
        posts = []
        parsed_comments = []
        
        if videos_raw:
            first = videos_raw[0].get("snippet", {})
            account = Account(
                platform="youtube",
                username=first.get("channelTitle", channel_id),
                followers=None,
                following=None,
                posts_count=None,
                bio=None
            )
            
            for item in videos_raw:
                snippet = item.get("snippet", {})
                id_info = item.get("id", {})
                stats = item.get("statistics", {})
                
                post = Post(
                    post_id=id_info.get("videoId", ""),
                    caption=snippet.get("title", ""),
                    likes=int(stats.get("likeCount", 0)) if stats.get("likeCount") else None,
                    comments=int(stats.get("commentCount", 0)) if stats.get("commentCount") else None,
                    views=int(stats.get("viewCount", 0)) if stats.get("viewCount") else None,
                    posted_at=snippet.get("publishedAt"),
                    type="video"
                )
                posts.append(post)
                
            for c in comments_raw:
                snippet = c.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                parsed_c = Comment(
                    comment_id=c.get("id", ""),
                    author=snippet.get("authorDisplayName", ""),
                    text=snippet.get("textDisplay", ""),
                    likes=snippet.get("likeCount", 0)
                )
                parsed_comments.append(parsed_c)
                
        metadata = {
            "collection_date": datetime.now(timezone.utc).isoformat(),
            "platform": "youtube",
            "collector_version": "2.0",
            "api_used": "youtube_v3",
            "account_requested": channel_id
        }
                
        return {
            "metadata": metadata,
            "raw_account": [videos_raw[0]] if videos_raw else [],
            "raw_posts": videos_raw,
            "raw_comments": comments_raw,
            "normalized_account": account.to_dict() if account else {},
            "normalized_posts": [p.to_dict() for p in posts],
            "competitors": []
        }

    @with_retry(error_patterns=YOUTUBE_ROTATION_ERRORS, http_codes=YOUTUBE_ROTATION_HTTP_CODES)
    def _collect(self, channel_id: str, max_results: int) -> dict:
        yt   = build("youtube", "v3", developerKey=self.rotator.get_current_key())
        resp = yt.search().list(
            part="snippet", channelId=channel_id,
            maxResults=max_results, order="date", type="video",
        ).execute()
        
        videos = resp.get("items", [])
        if not videos:
            return {"videos": [], "comments": []}
            
        video_ids = [v["id"]["videoId"] for v in videos if "id" in v and "videoId" in v["id"]]
        
        if video_ids:
            stats_resp = yt.videos().list(
                part="statistics",
                id=",".join(video_ids)
            ).execute()
            
            stats_map = {item["id"]: item["statistics"] for item in stats_resp.get("items", [])}
            for v in videos:
                vid = v["id"]["videoId"]
                if vid in stats_map:
                    v["statistics"] = stats_map[vid]
                    
        all_comments = []
        for vid in video_ids:
            try:
                c_resp = yt.commentThreads().list(
                    part="snippet",
                    videoId=vid,
                    maxResults=20
                ).execute()
                for c in c_resp.get("items", []):
                    c["videoId"] = vid
                    all_comments.append(c)
            except Exception as e:
                logger.warning(f"Failed to fetch comments for video {vid}: {e}")
                
        return {"videos": videos, "comments": all_comments}
