"""
competitor_analyzer.py
Compares main account against discovered competitors.
"""
from typing import List, Dict, Any
from analyzers.engagement_analyzer import EngagementAnalyzer


class CompetitorAnalyzer:

    def __init__(self):
        self._eng = EngagementAnalyzer()

    def compare(self, main: Dict, competitors: List[Dict]) -> Dict[str, Any]:
        """
        main / competitors each have keys: profile (dict), posts (list)
        """
        main_profile   = main.get("profile", {})
        main_followers = main_profile.get("followersCount", 0)
        main_er        = self._eng.calculate_er(main_followers, main.get("posts", []))

        results = []
        for comp in competitors:
            p = comp.get("profile", {})
            f = p.get("followersCount", 0)
            er = self._eng.calculate_er(f, comp.get("posts", []))
            results.append({
                "username":        p.get("username"),
                "followers":       f,
                "er_percent":      er,
                "followers_delta": f - main_followers,
                "er_delta":        round(er - main_er, 2),
            })

        results.sort(key=lambda x: x["followers"], reverse=True)

        return {
            "main": {
                "username":   main_profile.get("username"),
                "followers":  main_followers,
                "er_percent": main_er,
            },
            "competitors": results,
        }
