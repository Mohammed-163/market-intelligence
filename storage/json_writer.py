import json
import os
from utils.logger import get_logger

logger = get_logger()

class JSONWriter:
    @staticmethod
    def _ensure_dir(path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)

    @staticmethod
    def save_account_data(platform: str, username: str, payload: dict):
        base_dir = f"data/{platform}_{username}"
        JSONWriter._ensure_dir(base_dir)

        # Mapping keys in the payload to filenames
        file_mapping = {
            "metadata": "metadata.json",
            "raw_account": "raw_account.json",
            "raw_posts": "raw_posts.json",
            "raw_comments": "raw_comments.json",
            "normalized_account": "normalized_account.json",
            "normalized_posts": "normalized_posts.json",
            "competitors": "competitors.json"
        }

        for key, filename in file_mapping.items():
            if key in payload and payload[key] is not None:
                path = os.path.join(base_dir, filename)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(payload[key], f, indent=2, ensure_ascii=False)
                
        logger.info(f"Saved complete data package for {platform}_{username} to {base_dir}/")
