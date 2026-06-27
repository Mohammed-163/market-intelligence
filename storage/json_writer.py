import json
import os
from datetime import datetime, timezone
from utils.logger import get_logger

logger = get_logger()

class JSONWriter:
    @staticmethod
    def _ensure_dir(path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)

    @staticmethod
    def save_entity(folder: str, platform: str, username: str, timestamp: str, metadata: dict, normalized_data, raw_response) -> str:
        if not normalized_data and not raw_response:
            return None
            
        path = f"data/{folder}/{platform}_{username}_{timestamp}.json"
        JSONWriter._ensure_dir(path)
        
        payload = {
            "metadata": metadata,
            "normalized_data": normalized_data,
            "raw_response": raw_response
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            
        return path

    @staticmethod
    def save_pure_raw(platform: str, username: str, timestamp: str, raw_data) -> str:
        if not raw_data:
            return None
            
        path = f"data/raw/{platform}/{username}_{timestamp}.json"
        JSONWriter._ensure_dir(path)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)
            
        return path

    @staticmethod
    def save_manifest(platform: str, username: str, timestamp: str, manifest_data: dict) -> str:
        path = f"data/manifests/{platform}_{username}_{timestamp}.json"
        JSONWriter._ensure_dir(path)
        
        manifest_data["created_at"] = datetime.now(timezone.utc).isoformat()
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved manifest to {path}")
        return path
