import os
import json
import datetime
from config.settings import Settings
from config.secrets_manager import SecretsManager
from collectors.instagram_collector import InstagramCollector
from utils.logger import get_logger

logger = get_logger()

def test_collection():
    username = "Smart.lens.iq"
    
    # We must ensure there is a data/accounts directory
    os.makedirs("data/accounts", exist_ok=True)
    out_path = f"data/accounts/Smart_lens_iq.json"
    
    # Check if keys are available
    settings = Settings.load()
    if not settings.apify_rotator:
        print("ERROR: No Apify keys configured in environment (APIFY_1, APIFY_2, APIFY_3).")
        return

    collector = InstagramCollector()
    
    try:
        posts = collector.collect_posts(username, max_results=20)
    except Exception as e:
        logger.error(f"Collection failed: {e}")
        posts = []

    profile = {}
    if posts and "ownerUsername" in posts[0]:
        profile = {
            "username": posts[0].get("ownerUsername"),
            "fullName": posts[0].get("ownerFullName"),
            "followersCount": posts[0].get("followersCount", 0),
            "followsCount": posts[0].get("followsCount", 0)
        }

    formatted_posts = []
    raw_comments = []
    for p in posts:
        formatted_posts.append({
            "post_url": p.get("url"),
            "caption": p.get("caption"),
            "media_type": p.get("type"),
            "timestamp": p.get("timestamp"),
        })
        
        if "latestComments" in p:
            for c in p["latestComments"][:20]: # up to 20 per post
                raw_comments.append(c)
            
    result = {
      "platform": "instagram",
      "account": username,
      "timestamp": datetime.datetime.now().isoformat(),
      "profile": profile,
      "posts": formatted_posts,
      "raw_comments": raw_comments,
      "errors": []
    }
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        
    print(f"File path: {os.path.abspath(out_path)}")
    print(f"Number of posts collected: {len(formatted_posts)}")
    print(f"Number of comments collected: {len(raw_comments)}")
    
    try:
        current_key = settings.apify_rotator.get_current_key()
        # mask the key for printing
        masked = current_key[:4] + "***" + current_key[-2:] if len(current_key) > 6 else "***"
        print(f"Successful APIFY key used: {masked}")
    except:
        print("Successful APIFY key used: None")

if __name__ == "__main__":
    test_collection()
