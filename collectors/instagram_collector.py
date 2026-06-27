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

    def collect_posts(self, username: str, max_results: int = MAX_POSTS) -> dict:
        if not self.rotator:
            logger.warning("No Apify keys configured. Skipping Instagram collection.")
            return {"raw_data": [], "account": None, "posts": [], "comments": []}
            
        raw_data = self._collect(username, max_results)
        
        from models.account import Account
        from models.post import Post
        
        account = None
        posts = []
        
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
                
        return {
            "raw_data": raw_data,
            "account": account,
            "posts": posts,
            "comments": []
        }

    @with_retry(error_patterns=APIFY_ROTATION_ERRORS, http_codes=APIFY_ROTATION_HTTP_CODES)
    def _collect(self, username: str, max_results: int) -> list:
        api_key = self.rotator.get_current_key()
        from apify_client import ApifyClient
        client  = ApifyClient(api_key)
        run = client.actor("apify/instagram-scraper").call(run_input={
            "usernames":     [username],
            "resultsLimit":  max_results,
            "addParentData": True,
        })
        return list(client.dataset(run["defaultDatasetId"]).iterate_items())
