from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Post:
    url:            str
    media_type:     str
    timestamp:      Optional[str] = None
    caption:        Optional[str] = None
    likes_count:    int = 0
    comments_count: int = 0
    views_count:    int = 0
    hashtags:       List[str] = field(default_factory=list)
    platform:       str = "instagram"
