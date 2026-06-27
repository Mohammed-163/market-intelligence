import os
from dataclasses import dataclass
from typing import List, Tuple

@dataclass(frozen=True)
class SecretKeys:
    youtube_keys: Tuple[str, ...] = ()
    apify_tokens: Tuple[str, ...] = ()
    gemini_keys: Tuple[str, ...] = ()

class SecretsManager:
    _ENV_MAP = {
        "youtube": ["YOUTUBE_1", "YOUTUBE_2"],
        "apify": ["APIFY_1", "APIFY_2", "APIFY_3"],
        "gemini": ["GEMINI_1", "GEMINI_2"],
    }

    @classmethod
    def load(cls) -> SecretKeys:
        return SecretKeys(
            youtube_keys=cls._load_pool("youtube"),
            apify_tokens=cls._load_pool("apify"),
            gemini_keys=cls._load_pool("gemini"),
        )

    @classmethod
    def _load_pool(cls, pool_name: str) -> Tuple[str, ...]:
        keys = []
        for name in cls._ENV_MAP.get(pool_name, []):
            val = os.environ.get(name, "").strip()
            if val:
                keys.append(val)
        return tuple(keys)
