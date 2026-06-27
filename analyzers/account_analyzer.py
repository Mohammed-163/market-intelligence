"""
account_analyzer.py
Calculates growth rate, activity metrics, and overall account health.
"""
from typing import List, Dict, Any
from utils.logger import get_logger

logger = get_logger()


class AccountAnalyzer:

    def analyze_growth(self, current_followers: int, previous_followers: int) -> Dict[str, Any]:
        """Follower growth rate between two snapshots."""
        if previous_followers == 0:
            return {"growth_rate": 0.0, "diff": 0}
        diff = current_followers - previous_followers
        rate = (diff / previous_followers) * 100
        return {"growth_rate": round(rate, 2), "diff": diff}

    def analyze_activity(self, posts: List[Dict]) -> Dict[str, Any]:
        """Posting frequency analysis."""
        if not posts:
            return {"total_posts": 0, "avg_per_week": 0.0, "span_days": 0}

        from utils.date_utils import parse_timestamp
        timestamps = [parse_timestamp(p.get("timestamp")) for p in posts]
        timestamps = [t for t in timestamps if t]

        if len(timestamps) < 2:
            return {"total_posts": len(posts), "avg_per_week": 0.0, "span_days": 0}

        timestamps.sort()
        span_days = max((timestamps[-1] - timestamps[0]).days, 1)
        avg_per_week = round((len(posts) / span_days) * 7, 2)

        return {
            "total_posts": len(posts),
            "avg_per_week": avg_per_week,
            "span_days": span_days,
        }
