from dataclasses import dataclass
from schemas.account_schema import AccountProfile

@dataclass
class Competitor:
    profile:          AccountProfile
    er_percent:       float = 0.0
    followers_delta:  int   = 0
    er_delta:         float = 0.0
