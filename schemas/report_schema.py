from dataclasses import dataclass, field
from typing import Dict, List, Any
import datetime

@dataclass
class EngagementSummary:
    er_percent:   float = 0.0
    avg_likes:    float = 0.0
    avg_comments: float = 0.0
    avg_views:    float = 0.0

@dataclass
class SentimentSummary:
    positive: float = 0.0
    neutral:  float = 0.0
    negative: float = 0.0
    total:    int   = 0

@dataclass
class Report:
    account:      str
    platform:     str
    generated_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    profile:      Dict[str, Any]      = field(default_factory=dict)
    engagement:   EngagementSummary   = field(default_factory=EngagementSummary)
    sentiment:    SentimentSummary    = field(default_factory=SentimentSummary)
    content:      Dict[str, Any]      = field(default_factory=dict)
    competitors:  List[Dict]          = field(default_factory=list)
    activity:     Dict[str, Any]      = field(default_factory=dict)
