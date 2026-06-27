from dataclasses import dataclass, field
from typing import Optional

@dataclass
class AccountProfile:
    username:        str
    platform:        str
    followers_count: int = 0
    follows_count:   int = 0
    posts_count:     int = 0
    full_name:       Optional[str] = None
    bio:             Optional[str] = None
    is_verified:     bool = False
    profile_pic_url: Optional[str] = None
