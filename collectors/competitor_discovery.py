import time
from utils.logger import get_logger
from config.constants import MAX_COMPETITORS, YOUTUBE_ROTATION_ERRORS, YOUTUBE_ROTATION_HTTP_CODES, APIFY_ROTATION_ERRORS, APIFY_ROTATION_HTTP_CODES
from config.settings import Settings
from utils.retry import with_retry
from googleapiclient.discovery import build
from apify_client import ApifyClient
from models.competitor import Competitor

logger = get_logger()
settings = Settings.load()

class CompetitorDiscovery:
    
    @with_retry(rotator=settings.youtube_rotator, error_patterns=YOUTUBE_ROTATION_ERRORS, http_codes=YOUTUBE_ROTATION_HTTP_CODES)
    def _discover_youtube(self, keyword: str) -> dict:
        if not settings.youtube_rotator:
            logger.warning("No YouTube keys configured for discovery.")
            return {"raw_data": [], "competitors": []}
            
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
        channel_ids = [c["id"]["channelId"] for c in response.get("items", []) if "channelId" in c.get("id", {})]
        
        if channel_ids:
            channel_resp = youtube.channels().list(
                part="snippet,statistics",
                id=",".join(channel_ids)
            ).execute()
            
            for item in channel_resp.get("items", []):
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})
                
                competitor = Competitor(
                    username=snippet.get("title", ""),
                    full_name=snippet.get("customUrl", ""),
                    platform="youtube",
                    followers=int(stats.get("subscriberCount", 0)) if stats.get("subscriberCount") else None,
                    following=None,
                    posts_count=int(stats.get("videoCount", 0)) if stats.get("videoCount") else None,
                    bio=snippet.get("description", ""),
                    external_url=f"https://youtube.com/{snippet.get('customUrl', '')}",
                    category=None,
                    verified=None
                )
                results.append(competitor)
                
        return {"raw_data": response, "competitors": results}

    @with_retry(rotator=settings.apify_rotator, error_patterns=APIFY_ROTATION_ERRORS, http_codes=APIFY_ROTATION_HTTP_CODES)
    def _discover_instagram(self, keyword: str) -> dict:
        if not settings.apify_rotator:
            logger.warning("No Apify keys configured for IG discovery.")
            return {"raw_data": [], "competitors": []}
            
        api_key = settings.apify_rotator.get_current_key()
        client = ApifyClient(api_key)
        
        run_input = {
            "search": keyword,
            "searchType": "hashtag",
            "searchLimit": MAX_COMPETITORS
        }
        
        run = client.actor("apify/instagram-scraper").call(run_input=run_input)
        
        results = []
        seen = set()
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            username = item.get("ownerUsername")
            if username and username not in seen:
                seen.add(username)
                competitor = Competitor(
                    username=username,
                    full_name=item.get("ownerFullName"),
                    platform="instagram",
                    followers=None, # Not reliably available in hashtag search without a second API call
                    bio=None
                )
                results.append(competitor)
                if len(results) >= MAX_COMPETITORS:
                    break
                    
        return {"raw_data": run, "competitors": results}

    def discover_competitors(self, keyword: str, platform: str) -> dict:
        logger.info(f"Discovering up to {MAX_COMPETITORS} competitors for '{keyword}' on {platform}")
        
        if platform.lower() == "youtube":
            return self._discover_youtube(keyword)
        elif platform.lower() == "instagram":
            return self._discover_instagram(keyword)
        else:
            logger.warning(f"Discovery for platform '{platform}' is not fully implemented or supported.")
            return {"raw_data": [], "competitors": []}

