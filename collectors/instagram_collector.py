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

    def collect_posts(self, username: str, max_results: int = MAX_POSTS, cache=None) -> dict:
        if not self.rotator:
            logger.warning("No Apify keys configured. Skipping Instagram collection.")
            return {}
            
        cache_key = f"instagram:{username.lower()}:{max_results}"
        raw_data = None
        if cache:
            try:
                raw_data = cache.get(cache_key)
                if raw_data is not None:
                    logger.info(f"Cache hit for Instagram @{username} — skipping Apify call.")
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

        if raw_data is None:
            raw_data = self._collect(username, max_results)
            if cache and raw_data:
                try:
                    cache.set(cache_key, raw_data)
                except Exception as e:
                    logger.warning(f"Cache write failed: {e}")
        
        from models.account import Account
        from models.post import Post
        from models.comment import Comment
        from datetime import datetime, timezone
        
        account = None
        posts = []
        raw_comments = []
        parsed_comments = []
        
        if raw_data:
            first = raw_data[0]
            account = Account(
                platform="instagram",
                username=username,
                followers=first.get('ownerFollowersCount'),
                following=None,
                posts_count=first.get('ownerPostsCount'),
                bio=first.get('ownerBiography')
            )
            
            for item in raw_data:
                post = Post(
                    post_id=item.get('id', ''),
                    caption=item.get('caption', ''),
                    likes=item.get('likesCount'),
                    comments=item.get('commentsCount'),
                    views=item.get('videoViewCount'),
                    posted_at=item.get('timestamp'),
                    type=item.get('type', 'image')
                )
                posts.append(post)
                
                if 'latestComments' in item and item['latestComments']:
                    for c in item['latestComments']:
                        raw_comments.append(c)
                        parsed_c = Comment(
                            comment_id=c.get('id', ''),
                            author=c.get('ownerUsername', ''),
                            text=c.get('text', ''),
                            likes=c.get('likesCount')
                        )
                        parsed_comments.append(parsed_c)
                        
        metadata = {
            "collection_date": datetime.now(timezone.utc).isoformat(),
            "platform": "instagram",
            "collector_version": "2.0",
            "api_used": "apify/instagram-scraper",
            "account_requested": username
        }

        return {
            "metadata": metadata,
            "raw_account": [raw_data[0]] if raw_data else [],
            "raw_posts": raw_data,
            "raw_comments": raw_comments,
            "normalized_account": account.to_dict() if account else {},
            "normalized_posts": [p.to_dict() for p in posts],
            "competitors": [] # if comments need to be saved independently, we could map them, but normalized_posts should suffice or add normalized_comments
        }
    @with_retry(error_patterns=APIFY_ROTATION_ERRORS, http_codes=APIFY_ROTATION_HTTP_CODES)
    def _collect(self, username: str, max_results: int) -> list:
        api_key = self.rotator.get_current_key()
        from apify_client import ApifyClient
        client  = ApifyClient(api_key)
        run = client.actor("apify/instagram-scraper").call(run_input={
            "directUrls":    [f"https://www.instagram.com/{username}/"],
            "resultsType":   "posts",
            "resultsLimit":  max_results,
            "addParentData": True,
        })
        
        # In apify-client v3, run is an object, not a dict.
        dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else getattr(run, "defaultDatasetId", getattr(run, "default_dataset_id", None))
        
        return list(client.dataset(dataset_id).iterate_items())
