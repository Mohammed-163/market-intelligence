"""
gemini_service.py
Single abstraction layer for Google Gemini API with key rotation.
"""
import google.generativeai as genai
from utils.logger import get_logger
from typing import Tuple

logger = get_logger()


class GeminiService:
    MODEL_NAME = "gemini-1.5-flash"

    def __init__(self, keys: Tuple[str, ...]):
        if not keys:
            raise ValueError("No Gemini API keys provided")
        self._keys = list(keys)
        self._idx  = 0

    def _configure(self):
        genai.configure(api_key=self._keys[self._idx])

    def _rotate(self):
        self._idx = (self._idx + 1) % len(self._keys)

    def analyze(self, prompt: str) -> str:
        """Send prompt to Gemini, auto-rotate key on quota errors."""
        max_attempts = len(self._keys)
        for attempt in range(max_attempts):
            try:
                self._configure()
                model = genai.GenerativeModel(self.MODEL_NAME)
                return model.generate_content(prompt).text
            except Exception as e:
                err = str(e).lower()
                if any(k in err for k in ("quota", "rate", "limit", "exhausted")):
                    logger.warning(f"Gemini quota error, rotating key ({attempt + 1}/{max_attempts}): {e}")
                    self._rotate()
                else:
                    logger.error(f"Gemini non-quota error: {e}")
                    raise
        raise RuntimeError("All Gemini keys exhausted")
