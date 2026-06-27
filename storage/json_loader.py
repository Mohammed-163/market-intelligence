import json
import os
from utils.logger import get_logger

logger = get_logger()

class JSONLoader:
    @staticmethod
    def load_json(filepath: str):
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
