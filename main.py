import argparse
from datetime import datetime, timezone
from utils.logger import get_logger
from config.settings import Settings
from collectors.youtube_collector import YouTubeCollector
from collectors.instagram_collector import InstagramCollector
from collectors.tiktok_collector import TikTokCollector
from collectors.competitor_discovery import CompetitorDiscovery
from storage.json_writer import JSONWriter
from storage.cache import Cache
from config.constants import MAX_POSTS

logger = get_logger()

def process_and_save(platform: str, username: str, data: dict, posts_limit: int):
    if not data:
        return
        
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    metadata = data.get("metadata", {})
    metadata["posts_limit"] = posts_limit
    
    manifest = {}
    
    # 1. Pure Raw Dump
    raw_dump = data.get("raw_posts", [])
    if not raw_dump and data.get("raw_data"):
        raw_dump = data.get("raw_data")
        
    if raw_dump:
        manifest["raw_dump_file"] = JSONWriter.save_pure_raw(platform, username, timestamp, raw_dump)
        
    # 2. Account
    if data.get("normalized_account"):
        manifest["account_file"] = JSONWriter.save_entity(
            "accounts", platform, username, timestamp,
            metadata, data["normalized_account"], data.get("raw_account", {})
        )
        
    # 3. Posts
    if data.get("normalized_posts"):
        manifest["posts_file"] = JSONWriter.save_entity(
            "posts", platform, username, timestamp,
            metadata, data["normalized_posts"], data.get("raw_posts", {})
        )
        
    # 4. Comments
    if data.get("raw_comments"):
        manifest["comments_file"] = JSONWriter.save_entity(
            "comments", platform, username, timestamp,
            metadata, [], data.get("raw_comments", [])
        )
        
    # 5. Competitors
    if data.get("competitors"):
        manifest["competitors_file"] = JSONWriter.save_entity(
            "competitors", platform, username, timestamp,
            metadata, [c.to_dict() if hasattr(c, 'to_dict') else c for c in data["competitors"]], data.get("raw_data", [])
        )
        
    # 6. Manifest
    JSONWriter.save_manifest(platform, username, timestamp, manifest)
    logger.info(f"Successfully processed and saved all entities for {platform}: {username}")

def main():
    parser = argparse.ArgumentParser(description="Market Intelligence Data Collector")
    parser.add_argument("--youtube", help="YouTube Channel ID")
    parser.add_argument("--instagram", help="Instagram Username")
    parser.add_argument("--tiktok", help="TikTok Username")
    parser.add_argument("--discover", help="Keyword to discover competitors")
    parser.add_argument("--posts", type=int, default=MAX_POSTS, help="Number of posts/videos to collect")
    args = parser.parse_args()

    logger.info("Starting Market Intelligence collection...")
    settings = Settings.load()
    
    cache = Cache(str(settings.cache_db_path), settings.cache_ttl_days)

    if args.discover:
        discovery = CompetitorDiscovery()
        for platform in ["youtube", "instagram", "tiktok"]:
            res = discovery.discover_competitors(args.discover, platform, cache=cache)
            if res:
                res["metadata"] = {
                    "platform": platform,
                    "requested_username": f"keyword_{args.discover}",
                    "collection_date": datetime.now(timezone.utc).isoformat(),
                    "collector_version": "2.0",
                    "api_used": "discovery"
                }
                process_and_save(platform, f"discovery_{args.discover.replace(' ', '_')}", res, args.posts)

    if args.youtube:
        collector = YouTubeCollector()
        data = collector.collect_videos(args.youtube, max_results=args.posts, cache=cache)
        process_and_save("youtube", args.youtube, data, args.posts)
        
    if args.instagram:
        collector = InstagramCollector()
        data = collector.collect_posts(args.instagram, max_results=args.posts, cache=cache)
        process_and_save("instagram", args.instagram, data, args.posts)
        
    if args.tiktok:
        collector = TikTokCollector()
        data = collector.collect_videos_sync(args.tiktok, max_results=args.posts, cache=cache)
        process_and_save("tiktok", args.tiktok, data, args.posts)
        
    if not any([args.youtube, args.instagram, args.tiktok, args.discover]):
        logger.warning("No targets specified. Use --help for usage.")

if __name__ == "__main__":
    main()
