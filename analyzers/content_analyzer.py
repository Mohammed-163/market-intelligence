"""
content_analyzer.py
Best/worst content types and optimal posting times.
"""
from typing import List, Dict, Any
from collections import Counter, defaultdict


class ContentAnalyzer:

    @staticmethod
    def _engagement(post: Dict) -> int:
        return (
            post.get("likes_count", post.get("likesCount", 0)) +
            post.get("comments_count", post.get("commentsCount", 0))
        )

    def analyze_by_type(self, posts: List[Dict]) -> Dict[str, Any]:
        """Rank media types by average engagement."""
        groups: Dict[str, List[int]] = defaultdict(list)
        for p in posts:
            media_type = p.get("type", p.get("media_type", "unknown"))
            groups[media_type].append(self._engagement(p))

        ranked = {
            t: {"count": len(v), "avg_engagement": round(sum(v) / len(v), 2)}
            for t, v in groups.items()
        }
        sorted_types = sorted(ranked.items(), key=lambda x: x[1]["avg_engagement"], reverse=True)

        return {
            "types": dict(sorted_types),
            "best_type": sorted_types[0][0] if sorted_types else None,
            "worst_type": sorted_types[-1][0] if sorted_types else None,
        }

    def analyze_posting_times(self, posts: List[Dict]) -> Dict[str, Any]:
        """Find best hour and day to post by avg engagement."""
        from utils.date_utils import parse_timestamp
        hour_eng: Dict[int, List[int]] = defaultdict(list)
        day_eng: Dict[str, List[int]] = defaultdict(list)

        for p in posts:
            ts = parse_timestamp(p.get("timestamp"))
            if not ts:
                continue
            eng = self._engagement(p)
            hour_eng[ts.hour].append(eng)
            day_eng[ts.strftime("%A")].append(eng)

        def avg_map(d):
            return {k: round(sum(v) / len(v), 2) for k, v in d.items()}

        best_hour = max(hour_eng, key=lambda h: sum(hour_eng[h]) / len(hour_eng[h]), default=None)
        best_day  = max(day_eng,  key=lambda d: sum(day_eng[d])  / len(day_eng[d]),  default=None)

        return {
            "best_hour": best_hour,
            "best_day":  best_day,
            "hours": avg_map(hour_eng),
            "days":  avg_map(day_eng),
        }

    def top_hashtags(self, posts: List[Dict], top_n: int = 10) -> List[str]:
        counter: Counter = Counter()
        for p in posts:
            tags = p.get("hashtags", [])
            if isinstance(tags, list):
                counter.update(tags)
            else:
                caption = p.get("caption", "") or ""
                counter.update(w for w in caption.split() if w.startswith("#"))
        return [tag for tag, _ in counter.most_common(top_n)]
