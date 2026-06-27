import time
from utils.logger import get_logger
from config.constants import MAX_COMPETITORS, MAX_COMPETITOR_DEEP_COLLECTION, YOUTUBE_ROTATION_ERRORS, YOUTUBE_ROTATION_HTTP_CODES, APIFY_ROTATION_ERRORS, APIFY_ROTATION_HTTP_CODES
from config.settings import Settings
from utils.retry import with_retry
from googleapiclient.discovery import build
from apify_client import ApifyClient
from models.competitor import Competitor

logger = get_logger()

class CompetitorDiscovery:
    def __init__(self):
        self.settings = Settings.load()
        self.youtube_rotator = self.settings.youtube_rotator
        self.apify_rotator = self.settings.apify_rotator
        
    @with_retry(rotator_attr="youtube_rotator", error_patterns=YOUTUBE_ROTATION_ERRORS, http_codes=YOUTUBE_ROTATION_HTTP_CODES)
    def _discover_youtube(self, keyword: str) -> dict:
        if not self.youtube_rotator:
            logger.warning("No YouTube keys configured for discovery.")
            return {"raw_data": [], "competitors": []}
            
        api_key = self.youtube_rotator.get_current_key()
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

    @with_retry(rotator_attr="apify_rotator", error_patterns=APIFY_ROTATION_ERRORS, http_codes=APIFY_ROTATION_HTTP_CODES)
    def _discover_instagram(self, keyword: str) -> dict:
        if not self.apify_rotator:
            logger.warning("No Apify keys configured for IG discovery.")
            return {"raw_data": [], "competitors": []}
            
        api_key = self.apify_rotator.get_current_key()
        client = ApifyClient(api_key)
        
        run_input = {
            "search": keyword,
            "searchType": "hashtag",
            "searchLimit": MAX_COMPETITORS
        }
        
        run = client.actor("apify/instagram-scraper").call(run_input=run_input)
        
        dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else getattr(run, "defaultDatasetId", getattr(run, "default_dataset_id", None))
        
        results = []
        raw_items = []
        seen = set()
        for item in client.dataset(dataset_id).iterate_items():
            raw_items.append(item)
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
                    
        return {"raw_data": raw_items, "competitors": results}

    def discover_competitors(self, keyword: str, platform: str, cache=None) -> dict:
        if platform.lower() == "tiktok":
            return {
                "supported": False,
                "reason": "TikTok competitor discovery is currently not supported."
            }

        logger.info(f"Discovering up to {MAX_COMPETITORS} competitors for '{keyword}' on {platform}")
        
        cache_key = f"competitors:{platform.lower()}:{keyword.lower().replace(' ', '_')}"
        raw_data = None
        if cache:
            try:
                raw_data = cache.get(cache_key)
                if raw_data is not None:
                    logger.info(f"Cache hit for discovery '{keyword}' on {platform} — skipping API call.")
                    return raw_data
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

        if platform.lower() == "youtube":
            result = self._discover_youtube(keyword)
        elif platform.lower() == "instagram":
            result = self._discover_instagram(keyword)
        else:
            logger.warning(f"Discovery for platform '{platform}' is not fully implemented or supported.")
            result = {"raw_data": [], "competitors": []}
            
        # Deep Collection Logic
        if result and result.get("competitors"):
            competitors_list = result["competitors"]
            
            # Instagram Deep Collection
            if platform.lower() == "instagram":
                from collectors.instagram_collector import InstagramCollector
                ig_collector = InstagramCollector()
                
                for i, comp in enumerate(competitors_list):
                    if i >= MAX_COMPETITOR_DEEP_COLLECTION:
                        break
                    logger.info(f"Deep collecting Instagram competitor: {comp.username}")
                    data = ig_collector.collect_posts(comp.username, max_results=5, cache=cache)
                    
                    norm_account = data.get("normalized_account", {})
                    norm_posts = data.get("normalized_posts", [])
                    
                    comp.full_name = norm_account.get("full_name", comp.full_name)
                    comp.followers = norm_account.get("followers", comp.followers)
                    comp.following = norm_account.get("following", comp.following)
                    comp.posts_count = norm_account.get("posts_count", comp.posts_count)
                    comp.bio = norm_account.get("bio", comp.bio)
                    comp.verified = norm_account.get("verified", comp.verified)
                    comp.profile_pic_url = norm_account.get("profile_pic_url", None)
                    comp.external_url = norm_account.get("external_url", comp.external_url)
                    comp.sample_posts = norm_posts
            
            # YouTube Deep Collection
            elif platform.lower() == "youtube":
                from collectors.youtube_collector import YouTubeCollector
                yt_collector = YouTubeCollector()
                
                for i, comp in enumerate(competitors_list):
                    if i >= MAX_COMPETITOR_DEEP_COLLECTION:
                        break
                    
                    logger.info(f"Deep collecting YouTube competitor: {comp.username}")
                    data = yt_collector.collect_videos(comp.username, max_results=5, cache=cache)
                    
                    norm_account = data.get("normalized_account", {})
                    norm_posts = data.get("normalized_posts", [])
                    
                    comp.full_name = norm_account.get("full_name", comp.full_name)
                    comp.followers = norm_account.get("followers", comp.followers)
                    comp.following = norm_account.get("following", comp.following)
                    comp.posts_count = norm_account.get("posts_count", comp.posts_count)
                    comp.bio = norm_account.get("bio", comp.bio)
                    comp.verified = norm_account.get("verified", comp.verified)
                    comp.profile_pic_url = norm_account.get("profile_pic_url", None)
                    comp.external_url = norm_account.get("external_url", comp.external_url)
                    comp.sample_posts = norm_posts

            if cache:
                try:
                    cache_payload = {
                        "raw_data": result["raw_data"],
                        "competitors": [c.to_dict() if hasattr(c, 'to_dict') else c for c in competitors_list]
                    }
                    cache.set(cache_key, cache_payload)
                except Exception as e:
                    logger.warning(f"Cache write failed: {e}")
                
        return result

