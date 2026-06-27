import json
import os
from utils.logger import get_logger

logger = get_logger()

class JSONWriter:
    @staticmethod
    def _ensure_dir(path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)

    @staticmethod
    def save_account(account_dict: dict):
        path = f"data/accounts/{account_dict['platform']}_{account_dict['username']}.json"
        JSONWriter._ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(account_dict, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved account to {path}")

    @staticmethod
    def save_posts(platform: str, username: str, posts_list: list):
        path = f"data/posts/{platform}_{username}.json"
        JSONWriter._ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(posts_list, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(posts_list)} posts to {path}")

    @staticmethod
    def save_comments(platform: str, username: str, post_id: str, comments_list: list):
        path = f"data/comments/{platform}_{username}_{post_id}.json"
        JSONWriter._ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(comments_list, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(comments_list)} comments to {path}")

    @staticmethod
    def save_competitors(platform: str, keyword: str, competitors_list: list):
        path = f"data/competitors/{platform}_{keyword}.json"
        JSONWriter._ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(competitors_list, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(competitors_list)} competitors to {path}")

    @staticmethod
    def save_raw_response(platform: str, username: str, file_name: str, data):
        path = f"data/raw/{platform}/{username}/{file_name}"
        JSONWriter._ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved raw response to {path}")
