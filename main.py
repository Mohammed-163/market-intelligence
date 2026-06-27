import argparse
from utils.logger import get_logger
from config.settings import Settings
from collectors.youtube_collector import YouTubeCollector
from collectors.instagram_collector import InstagramCollector
from collectors.tiktok_collector import TikTokCollector
from collectors.competitor_discovery import CompetitorDiscovery
from storage.json_writer import JSONWriter
from config.constants import MAX_POSTS

logger = get_logger()

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

    if args.discover:
        discovery = CompetitorDiscovery()
        for platform in ["youtube", "instagram", "tiktok"]:
            res = discovery.discover_competitors(args.discover, platform)
            if res:
                from datetime import datetime, timezone
                metadata = {
                    "collection_date": datetime.now(timezone.utc).isoformat(),
                    "platform": platform,
                    "collector_version": "2.0",
                    "api_used": "discovery",
                    "account_requested": f"keyword_{args.discover}"
                }
                payload = {
                    "metadata": metadata,
                    "raw_account": [],
                    "raw_posts": res.get("raw_data", []), # raw_data from search
                    "raw_comments": [],
                    "normalized_account": {},
                    "normalized_posts": [],
                    "competitors": [c.to_dict() for c in res.get("competitors", [])]
                }
                JSONWriter.save_account_data(platform, f"discovery_{args.discover.replace(' ', '_')}", payload)

    if args.youtube:
        collector = YouTubeCollector()
        data = collector.collect_videos(args.youtube, max_results=args.posts)
        if data:
            logger.info(f"Collected YouTube videos for {args.youtube}.")
            JSONWriter.save_account_data("youtube", args.youtube, data)
        
    if args.instagram:
        collector = InstagramCollector()
        data = collector.collect_posts(args.instagram, max_results=args.posts)
        if data:
            logger.info(f"Collected Instagram posts for {args.instagram}.")
            JSONWriter.save_account_data("instagram", args.instagram, data)
        
    if args.tiktok:
        collector = TikTokCollector()
        data = collector.collect_videos_sync(args.tiktok, max_results=args.posts)
        if data:
            logger.info(f"Collected TikTok videos for {args.tiktok}.")
            JSONWriter.save_account_data("tiktok", args.tiktok, data)
        
    if not any([args.youtube, args.instagram, args.tiktok, args.discover]):
        logger.warning("No targets specified. Use --help for usage.")

if __name__ == "__main__":
    main()
