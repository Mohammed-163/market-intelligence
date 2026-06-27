import asyncio
from TikTokApi import TikTokApi
from config.settings import Settings
from config.constants import APIFY_ROTATION_ERRORS, APIFY_ROTATION_HTTP_CODES, MAX_VIDEOS
from utils.logger import get_logger
from apify_client import ApifyClient
from utils.retry import with_retry

logger = get_logger()
settings = Settings.load()

class TikTokCollector:
    @with_retry(rotator=settings.apify_rotator, error_patterns=APIFY_ROTATION_ERRORS, http_codes=APIFY_ROTATION_HTTP_CODES)
    def _collect_with_apify(self, username: str, max_results: int = 20):
        if not settings.apify_rotator:
            logger.warning("No Apify keys configured for TikTok fallback.")
            return []
            
        api_key = settings.apify_rotator.get_current_key()
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

    async def collect_videos(self, username: str, max_results: int = MAX_VIDEOS):
        results = []
        try:
            async with TikTokApi() as api:
                await api.create_sessions(ms_tokens=[], num_sessions=1, sleep_after=3)
                user = api.user(username=username)
                async for video in user.videos(count=max_results):
                    results.append(video.as_dict)
        except Exception as e:
            logger.error(f"TikTokApi failed: {e}")
            logger.info("Falling back to Apify TikTok Scraper")
            results = self._collect_with_apify(username, max_results)
                
        return results

    def collect_videos_sync(self, username: str, max_results: int = MAX_VIDEOS):
        return asyncio.run(self.collect_videos(username, max_results))
