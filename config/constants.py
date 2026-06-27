"""
constants.py
Project-wide constants.
"""

MAX_POSTS = 20
MAX_VIDEOS = 20
MAX_COMPETITORS = 20

CACHE_TTL_DAYS = 7
CACHE_DB_NAME = "collection_cache.db"

RETRY_BASE_DELAY_SECONDS = 2
RETRY_MAX_DELAY_SECONDS = 30
MAX_RETRIES = 3

YOUTUBE_ROTATION_ERRORS = frozenset([
    "quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded", 
    "forbidden", "accessNotConfigured", "keyInvalid", "badRequest"
])
YOUTUBE_ROTATION_HTTP_CODES = frozenset([403, 429])

APIFY_ROTATION_ERRORS = frozenset([
    "credits exhausted", "rate limit", "rate limited", "actor failed",
    "timeout", "insufficient credits", "payment required", "account limit"
])
APIFY_ROTATION_HTTP_CODES = frozenset([402, 429, 503])

DATA_DIR = "data"
ACCOUNTS_DIR = f"{DATA_DIR}/accounts"
COMPETITORS_DIR = f"{DATA_DIR}/competitors"
COMMENTS_DIR = f"{DATA_DIR}/comments"
LOGS_DIR = f"{DATA_DIR}/logs"
LOG_FILE = f"{LOGS_DIR}/app.log"

POOL_YOUTUBE = "youtube"
POOL_APIFY = "apify"
POOL_GEMINI = "gemini"
