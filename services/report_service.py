"""
report_service.py
Assembles and serialises the final intelligence report in multiple formats.
"""
import datetime
from typing import Dict, Any
from utils.file_manager import FileManager
from utils.logger import get_logger

logger = get_logger()


class ReportService:
    DEFAULT_DIR = "data/reports"

    def __init__(self, output_dir: str = DEFAULT_DIR):
        self.output_dir = output_dir
        self.fm = FileManager()

    # ------------------------------------------------------------------ build
    def build(self, data: Dict[str, Any], account: str) -> Dict[str, Any]:
        return {
            "generated_at": datetime.datetime.now().isoformat(),
            "account":      account,
            "platform":     data.get("platform", "unknown"),
            "profile":      data.get("profile",  {}),
            "engagement":   data.get("engagement", {}),
            "content":      data.get("content",    {}),
            "sentiment":    data.get("sentiment",  {}),
            "competitors":  data.get("competitors",{}),
            "activity":     data.get("activity",   {}),
        }

    # ------------------------------------------------------------------ save
    def save_json(self, report: Dict, filename: str) -> str:
        path = f"{self.output_dir}/{filename}.json"
        self.fm.write_json(path, report)
        logger.info(f"JSON report saved: {path}")
        return path

    def save_markdown(self, report: Dict, filename: str) -> str:
        path = f"{self.output_dir}/{filename}.md"
        self.fm.write_text(path, self._to_markdown(report))
        logger.info(f"Markdown report saved: {path}")
        return path

    # ---------------------------------------------------------------- private
    def _to_markdown(self, r: Dict) -> str:
        profile    = r.get("profile",    {})
        engagement = r.get("engagement", {})
        sentiment  = r.get("sentiment",  {})
        content    = r.get("content",    {})
        competitors = r.get("competitors", {}).get("competitors", [])

        lines = [
            f"# Market Intelligence Report — {r.get('account', '')}",
            f"**Generated:** {r.get('generated_at', '')}  |  **Platform:** {r.get('platform', '')}",
            "",
            "## 👤 Profile",
            f"- **Followers:** {profile.get('followersCount', 'N/A'):,}",
            f"- **Following:** {profile.get('followsCount',  'N/A'):,}",
            "",
            "## 📊 Engagement",
            f"- **ER%:** {engagement.get('er_percent', 0)}%",
            f"- **Avg Likes:** {engagement.get('avg_likes', 0):,.0f}",
            f"- **Avg Comments:** {engagement.get('avg_comments', 0):,.0f}",
            f"- **Avg Views:** {engagement.get('avg_views', 0):,.0f}",
            "",
            "## 💬 Sentiment",
            f"- 🟢 Positive: {sentiment.get('positive', 0)}%",
            f"- 🟡 Neutral:  {sentiment.get('neutral',  0)}%",
            f"- 🔴 Negative: {sentiment.get('negative', 0)}%",
            f"- **Total comments analysed:** {sentiment.get('total', 0)}",
            "",
            "## 🏆 Content",
            f"- **Best type:**  {content.get('best_type',  'N/A')}",
            f"- **Worst type:** {content.get('worst_type', 'N/A')}",
            f"- **Best hour:**  {content.get('best_hour',  'N/A')}:00",
            f"- **Best day:**   {content.get('best_day',   'N/A')}",
            "",
        ]
        if competitors:
            lines += ["## ⚔️ Competitors", "| Username | Followers | ER% | Δ Followers |",
                      "|----------|-----------|-----|-------------|"]
            for c in competitors:
                lines.append(
                    f"| {c.get('username','?')} | {c.get('followers',0):,} | "
                    f"{c.get('er_percent',0)}% | {c.get('followers_delta',0):+,} |"
                )
        return "\n".join(lines)
