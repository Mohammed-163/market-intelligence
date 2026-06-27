from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config.secrets_manager import SecretsManager, SecretKeys
from config.key_rotation import KeyRotator
from config.constants import POOL_YOUTUBE, POOL_APIFY, CACHE_DB_NAME, CACHE_TTL_DAYS

@dataclass
class Settings:
    secrets: SecretKeys
    youtube_rotator: Optional[KeyRotator]
    apify_rotator: Optional[KeyRotator]
    project_root: Path
    cache_ttl_days: int
    cache_db_path: Path

    @classmethod
    def load(cls) -> "Settings":
        secrets = SecretsManager.load()
        project_root = Path(__file__).parent.parent
        
        yt_rotator = KeyRotator(POOL_YOUTUBE, secrets.youtube_keys) if secrets.youtube_keys else None
        apify_rotator = KeyRotator(POOL_APIFY, secrets.apify_tokens) if secrets.apify_tokens else None
        
        return cls(
            secrets=secrets,
            youtube_rotator=yt_rotator,
            apify_rotator=apify_rotator,
            project_root=project_root,
            cache_ttl_days=CACHE_TTL_DAYS,
            cache_db_path=project_root / CACHE_DB_NAME
        )
