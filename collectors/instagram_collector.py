from apify_client import ApifyClient
from config.secrets_manager import SecretsManager
from config.key_rotation import KeyRotator
from config.constants import APIFY_ROTATION_ERRORS, APIFY_ROTATION_HTTP_CODES, POOL_APIFY, MAX_POSTS
from utils.retry import with_retry
from utils.logger import get_logger

logger = get_logger()


class InstagramCollector:
    # BUG FIX: Settings.load() was at module level — crashed if env vars missing at import time.
    def __init__(self):
        secrets = SecretsManager.load()
        self.rotator = (
            KeyRotator(POOL_APIFY, secrets.apify_tokens)
            if secrets.apify_tokens else None
        )

    def collect_posts(self, username: str, max_results: int = MAX_POSTS) -> list:
        if not self.rotator:
            logger.warning("No Apify keys configured. Skipping Instagram collection.")
            return []
        return self._collect(username, max_results)

    # BUG FIX: @with_retry was applied with module-level (None) rotator at definition time.
    @with_retry(error_patterns=APIFY_ROTATION_ERRORS, http_codes=APIFY_ROTATION_HTTP_CODES)
    def _collect(self, username: str, max_results: int) -> list:
        api_key = self.rotator.get_current_key()
        client  = ApifyClient(api_key)
        run = client.actor("apify/instagram-scraper").call(run_input={
            "usernames":     [username],
            "resultsLimit":  max_results,
            "addParentData": True,
        })
        return list(client.dataset(run["defaultDatasetId"]).iterate_items())
