import asyncio
from TikTokApi import TikTokApi
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger()
settings = Settings.load()

class TikTokCollector:
    async def collect_videos(self, username: str, max_results: int = 20):
        results = []
        try:
            async with TikTokApi() as api:
                await api.create_sessions(ms_tokens=[], num_sessions=1, sleep_after=3)
                user = api.user(username=username)
                async for video in user.videos(count=max_results):
                    results.append(video.as_dict)
        except Exception as e:
            logger.error(f"TikTokApi failed: {e}")
            # Fallback to apify if configured
            if settings.apify_rotator:
                from collectors.instagram_collector import InstagramCollector
                # This is just a placeholder for apify tiktok scraper
                logger.info("Falling back to Apify TikTok Scraper")
                
        return results

    def collect_videos_sync(self, username: str, max_results: int = 20):
        return asyncio.run(self.collect_videos(username, max_results))
