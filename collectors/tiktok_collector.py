import asyncio
from config.secrets_manager import SecretsManager
from config.key_rotation import KeyRotator
from config.constants import POOL_APIFY, MAX_VIDEOS
from utils.logger import get_logger

logger = get_logger()


class TikTokCollector:

    def __init__(self):
        secrets = SecretsManager.load()
        self.apify_rotator = (
            KeyRotator(POOL_APIFY, secrets.apify_tokens)
            if secrets.apify_tokens else None
        )

    async def collect_videos(self, username: str, max_results: int = MAX_VIDEOS) -> list:
        try:
            from TikTokApi import TikTokApi
            results = []
            async with TikTokApi() as api:
                await api.create_sessions(ms_tokens=[], num_sessions=1, sleep_after=3)
                async for video in api.user(username=username).videos(count=max_results):
                    results.append(video.as_dict)
            return results
        except Exception as e:
            logger.warning(f"TikTokApi failed ({e}). Falling back to Apify…")
            return self._collect_via_apify(username, max_results)

    # BUG FIX: old fallback imported InstagramCollector but never used it for TikTok.
    # Now correctly calls Apify's free TikTok scraper actor.
    def _collect_via_apify(self, username: str, max_results: int) -> list:
        if not self.apify_rotator:
            logger.error("No Apify keys — TikTok fallback unavailable.")
            return []
        try:
            from apify_client import ApifyClient
            client = ApifyClient(self.apify_rotator.get_current_key())
            run    = client.actor("clockworks/free-tiktok-scraper").call(run_input={
                "profiles":     [username],
                "resultsLimit": max_results,
            })
            return list(client.dataset(run["defaultDatasetId"]).iterate_items())
        except Exception as e:
            logger.error(f"Apify TikTok fallback failed: {e}")
            return []

    def collect_videos_sync(self, username: str, max_results: int = MAX_VIDEOS) -> list:
        return asyncio.run(self.collect_videos(username, max_results))
