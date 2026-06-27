"""
engagement_analyzer.py
ER%, Likes/Post, Comments/Post, Views/Post.
"""
from typing import List, Dict, Any


class EngagementAnalyzer:

    @staticmethod
    def _get(post: Dict, *keys, default=0):
        for k in keys:
            v = post.get(k)
            if v is not None:
                return v
        return default

    def calculate_er(self, followers: int, posts: List[Dict]) -> float:
        """ER% = avg(likes + comments) / followers * 100"""
        if not posts or followers == 0:
            return 0.0
        total = sum(
            self._get(p, "likes_count", "likesCount") +
            self._get(p, "comments_count", "commentsCount")
            for p in posts
        )
        return round((total / len(posts) / followers) * 100, 2)

    def avg_likes(self, posts: List[Dict]) -> float:
        if not posts:
            return 0.0
        return round(sum(self._get(p, "likes_count", "likesCount") for p in posts) / len(posts), 2)

    def avg_comments(self, posts: List[Dict]) -> float:
        if not posts:
            return 0.0
        return round(sum(self._get(p, "comments_count", "commentsCount") for p in posts) / len(posts), 2)

    def avg_views(self, posts: List[Dict]) -> float:
        if not posts:
            return 0.0
        return round(sum(self._get(p, "views_count", "videoViewCount", "viewCount") for p in posts) / len(posts), 2)

    def summary(self, followers: int, posts: List[Dict]) -> Dict[str, Any]:
        return {
            "er_percent": self.calculate_er(followers, posts),
            "avg_likes": self.avg_likes(posts),
            "avg_comments": self.avg_comments(posts),
            "avg_views": self.avg_views(posts),
        }
