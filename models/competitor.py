from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Competitor:
    username: str
    platform: str
    followers: Optional[int] = None

    def to_dict(self):
        return asdict(self)
