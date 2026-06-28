import os
import json
from collectors.competitor_discovery import CompetitorDiscovery
from utils.logger import get_logger

logger = get_logger()

def debug_apify():
    # Load secrets
    from config.settings import Settings
    settings = Settings.load()
    if not settings.secrets.apify_tokens:
        print("No apify tokens found")
        return
        
    discovery = CompetitorDiscovery()
    keyword = "product photography"
    
    print(f"Testing Apify discovery with keyword: {keyword}")
    result = discovery._discover_instagram(keyword)
    
    raw = result.get("raw_data", [])
    comps = result.get("competitors", [])
    print(f"Raw results length: {len(raw)}")
    print(f"Competitors length: {len(comps)}")
    
    if raw:
        print("Sample raw item:")
        print(json.dumps(raw[0], indent=2))
        
if __name__ == "__main__":
    debug_apify()
