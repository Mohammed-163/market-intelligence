from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Post:
    post_id: str
    caption: str
    likes: Optional[int] = None
    comments: Optional[int] = None
    views: Optional[int] = None
    posted_at: Optional[str] = None
    type: Optional[str] = None

    def to_dict(self):
        return asdict(self)
