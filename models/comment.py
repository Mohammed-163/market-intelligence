from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Comment:
    comment_id: str
    author: str
    text: str
    likes: Optional[int] = None

    def to_dict(self):
        return asdict(self)
