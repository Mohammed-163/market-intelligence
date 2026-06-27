import asyncio
from TikTokApi import TikTokApi
from config.settings import Settings
from config.constants import APIFY_ROTATION_ERRORS, APIFY_ROTATION_HTTP_CODES, MAX_VIDEOS
from utils.logger import get_logger
from apify_client import ApifyClient
from utils.retry import with_retry

logger = get_logger()

class TikTokCollector:
    def __init__(self):
        self.settings = Settings.load()
        self.rotator = self.settings.apify_rotator

    @with_retry(error_patterns=APIFY_ROTATION_ERRORS, http_codes=APIFY_ROTATION_HTTP_CODES)
    def _collect_with_apify(self, username: str, max_results: int = 20):
        if not self.rotator:
            logger.warning("No Apify keys configured for TikTok fallback.")
            return []
            
        api_key = self.rotator.get_current_key()
        client = ApifyClient(api_key)
        
        run_input = {
            "profiles": [username],
            "resultsPerPage": max_results,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }
        
        run = client.actor("clockwork/tiktok-scraper").call(run_input=run_input)
        
        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append(item)
            
        return results

    async def collect_videos(self, username: str, max_results: int = MAX_VIDEOS, cache=None) -> dict:
        cache_key = f"tiktok:{username.lower()}:{max_results}"
        raw_data = None
        if cache:
            try:
                raw_data = cache.get(cache_key)
                if raw_data is not None:
                    logger.info(f"Cache hit for TikTok @{username} — skipping API call.")
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

        if raw_data is None:
            raw_data = []
            try:
                async with TikTokApi() as api:
                    await api.create_sessions(ms_tokens=[], num_sessions=1, sleep_after=3)
                    user = api.user(username=username)
                    async for video in user.videos(count=max_results):
                        raw_data.append(video.as_dict)
            except Exception as e:
                logger.error(f"TikTokApi failed: {e}")
                logger.info("Falling back to Apify TikTok Scraper")
                raw_data = self._collect_with_apify(username, max_results)
            
            if cache and raw_data:
                try:
                    cache.set(cache_key, raw_data)
                except Exception as e:
                    logger.warning(f"Cache write failed: {e}")
                
        from models.account import Account
        from models.post import Post
        from datetime import datetime, timezone
        
        account = None
        posts = []
        raw_account = []
        
        if raw_data:
            first = raw_data[0]
            author = first.get('author', {})
            raw_account.append(author)
            account = Account(
                platform="tiktok",
                username=username,
                followers=author.get('followerCount') or author.get('stats', {}).get('followerCount'),
                following=author.get('followingCount') or author.get('stats', {}).get('followingCount'),
                posts_count=author.get('videoCount') or author.get('stats', {}).get('videoCount'),
                bio=author.get('signature')
            )
            
            for item in raw_data:
                stats = item.get('stats', item)
                post = Post(
                    post_id=str(item.get('id') or item.get('video_id') or ""),
                    caption=item.get('desc') or item.get('text') or "",
                    likes=item.get('diggCount') or stats.get('diggCount'),
                    comments=item.get('commentCount') or stats.get('commentCount'),
                    views=item.get('playCount') or stats.get('playCount'),
                    posted_at=str(item.get('createTime') or item.get('create_time') or ""),
                    type="video"
                )
                posts.append(post)

        metadata = {
            "collection_date": datetime.now(timezone.utc).isoformat(),
            "platform": "tiktok",
            "collector_version": "2.0",
            "api_used": "tiktok_unofficial/apify_fallback",
            "account_requested": username
        }

        return {
            "metadata": metadata,
            "raw_account": raw_account,
            "raw_posts": raw_data,
            "raw_comments": [],
            "normalized_account": account.to_dict() if account else {},
            "normalized_posts": [p.to_dict() for p in posts],
            "competitors": []
        }

    def collect_videos_sync(self, username: str, max_results: int = MAX_VIDEOS, cache=None):
        return asyncio.run(self.collect_videos(username, max_results, cache))
