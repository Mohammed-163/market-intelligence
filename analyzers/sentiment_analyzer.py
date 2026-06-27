"""
sentiment_analyzer.py
Comment sentiment analysis via Gemini.
"""
import json
from typing import List, Dict, Any
from utils.logger import get_logger

logger = get_logger()


class SentimentAnalyzer:

    def __init__(self, gemini_service):
        self.gemini = gemini_service

    def analyze(self, comments: List[str], batch_size: int = 50) -> Dict[str, Any]:
        if not comments:
            return {"positive": 0.0, "neutral": 0.0, "negative": 0.0, "total": 0}

        counts = {"positive": 0, "neutral": 0, "negative": 0}
        total  = 0

        for i in range(0, len(comments), batch_size):
            batch = comments[i : i + batch_size]
            try:
                batch_result = self._analyze_batch(batch)
                for k in counts:
                    counts[k] += batch_result.get(k, 0)
                total += len(batch)
            except Exception as e:
                logger.error(f"Sentiment batch failed: {e}")

        if total == 0:
            return {"positive": 0.0, "neutral": 0.0, "negative": 0.0, "total": 0}

        return {
            "positive": round(counts["positive"] / total * 100, 1),
            "neutral":  round(counts["neutral"]  / total * 100, 1),
            "negative": round(counts["negative"] / total * 100, 1),
            "total":    total,
        }

    def _analyze_batch(self, comments: List[str]) -> Dict[str, int]:
        with open("prompts/sentiment_analysis.txt", encoding="utf-8") as f:
            template = f.read()

        comments_text = "\n".join(f"- {c}" for c in comments)
        prompt = template.replace("{{COMMENTS}}", comments_text)
        raw = self.gemini.analyze(prompt)

        try:
            # Strip markdown fences if Gemini wraps in ```json
            clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
            data = json.loads(clean)
            return {k: int(data.get(k, 0)) for k in ("positive", "neutral", "negative")}
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Could not parse Gemini sentiment response: {raw[:120]}")
            return {"positive": 0, "neutral": 0, "negative": 0}
