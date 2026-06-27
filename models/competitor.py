from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Competitor:
    username: str
    platform: str
    full_name: Optional[str] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    posts_count: Optional[int] = None
    bio: Optional[str] = None
    external_url: Optional[str] = None
    category: Optional[str] = None
    verified: Optional[bool] = None

    def to_dict(self):
        return asdict(self)
