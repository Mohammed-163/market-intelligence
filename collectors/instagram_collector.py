from apify_client import ApifyClient
from config.settings import Settings
from config.constants import APIFY_ROTATION_ERRORS, APIFY_ROTATION_HTTP_CODES
from utils.retry import with_retry
from utils.logger import get_logger

logger = get_logger()
settings = Settings.load()

class InstagramCollector:
    @with_retry(rotator=settings.apify_rotator, error_patterns=APIFY_ROTATION_ERRORS, http_codes=APIFY_ROTATION_HTTP_CODES)
    def collect_posts(self, username: str, max_results: int = 20):
        if not settings.apify_rotator:
            logger.warning("No Apify keys configured.")
            return []
            
        api_key = settings.apify_rotator.get_current_key()
        client = ApifyClient(api_key)
        
        run_input = {
            "usernames": [username],
            "resultsLimit": max_results
        }
        
        # Apify Instagram Scraper Actor
        run = client.actor("apify/instagram-scraper").call(run_input=run_input)
        
        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append(item)
            
        return results
