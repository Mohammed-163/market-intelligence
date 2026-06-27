import time
from utils.logger import get_logger
from config.constants import MAX_COMPETITORS, YOUTUBE_ROTATION_ERRORS, YOUTUBE_ROTATION_HTTP_CODES, APIFY_ROTATION_ERRORS, APIFY_ROTATION_HTTP_CODES
from config.settings import Settings
from utils.retry import with_retry
from googleapiclient.discovery import build
from apify_client import ApifyClient

logger = get_logger()
settings = Settings.load()

class CompetitorDiscovery:
    
    @with_retry(rotator=settings.youtube_rotator, error_patterns=YOUTUBE_ROTATION_ERRORS, http_codes=YOUTUBE_ROTATION_HTTP_CODES)
    def _discover_youtube(self, keyword: str):
        if not settings.youtube_rotator:
            logger.warning("No YouTube keys configured for discovery.")
            return []
            
        api_key = settings.youtube_rotator.get_current_key()
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        request = youtube.search().list(
            part="snippet",
            q=keyword,
            type="channel",
            maxResults=MAX_COMPETITORS
        )
        response = request.execute()
        
        results = []
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            results.append({
                "platform": "youtube",
                "username": snippet.get("channelTitle"),
                "channel_id": item.get("id", {}).get("channelId"),
                "description": snippet.get("description"),
                "keyword": keyword
            })
        return results

    @with_retry(rotator=settings.apify_rotator, error_patterns=APIFY_ROTATION_ERRORS, http_codes=APIFY_ROTATION_HTTP_CODES)
    def _discover_instagram(self, keyword: str):
        if not settings.apify_rotator:
            logger.warning("No Apify keys configured for IG discovery.")
            return []
            
        api_key = settings.apify_rotator.get_current_key()
        client = ApifyClient(api_key)
        
        run_input = {
            "search": keyword,
            "searchType": "hashtag",
            "searchLimit": MAX_COMPETITORS
        }
        
        run = client.actor("apify/instagram-scraper").call(run_input=run_input)
        
        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append({
                "platform": "instagram",
                "username": item.get("ownerUsername"),
                "keyword": keyword
            })
        
        # Deduplicate usernames
        unique = []
        seen = set()
        for r in results:
            if r["username"] and r["username"] not in seen:
                seen.add(r["username"])
                unique.append(r)
                if len(unique) >= MAX_COMPETITORS:
                    break
        return unique

    def discover_competitors(self, keyword: str, platform: str):
        logger.info(f"Discovering up to {MAX_COMPETITORS} competitors for '{keyword}' on {platform}")
        
        if platform.lower() == "youtube":
            return self._discover_youtube(keyword)
        elif platform.lower() == "instagram":
            return self._discover_instagram(keyword)
        else:
            logger.warning(f"Discovery for platform '{platform}' is not fully implemented or supported.")
            return [{"username": f"competitor_{i}_{platform}", "keyword": keyword} for i in range(MAX_COMPETITORS)]

