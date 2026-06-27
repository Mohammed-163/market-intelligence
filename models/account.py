from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Account:
    platform: str
    username: str
    followers: Optional[int] = None
    following: Optional[int] = None
    posts_count: Optional[int] = None
    bio: Optional[str] = None
    collected_at: Optional[str] = None

    def to_dict(self):
        return asdict(self)
