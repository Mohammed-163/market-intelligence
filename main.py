import argparse
from utils.logger import get_logger
from config.settings import Settings
from collectors.youtube_collector import YouTubeCollector
from collectors.instagram_collector import InstagramCollector
from collectors.tiktok_collector import TikTokCollector
from collectors.competitor_discovery import CompetitorDiscovery
from storage.json_writer import JSONWriter

logger = get_logger()

def save_collected_data(platform: str, username_or_id: str, data: dict):
    # Save raw
    if data.get("raw_data"):
        JSONWriter.save_raw_response(platform, username_or_id, "raw_data.json", data["raw_data"])
    
    # Save parsed
    if data.get("account"):
        JSONWriter.save_account(data["account"].to_dict())
    
    if data.get("posts"):
        posts_list = [p.to_dict() for p in data["posts"]]
        JSONWriter.save_posts(platform, username_or_id, posts_list)

def main():
    parser = argparse.ArgumentParser(description="Market Intelligence Data Collector")
    parser.add_argument("--youtube", help="YouTube Channel ID")
    parser.add_argument("--instagram", help="Instagram Username")
    parser.add_argument("--tiktok", help="TikTok Username")
    parser.add_argument("--discover", help="Keyword to discover competitors")
    args = parser.parse_args()

    logger.info("Starting Market Intelligence collection...")
    settings = Settings.load()

    if args.discover:
        discovery = CompetitorDiscovery()
        for platform in ["youtube", "instagram", "tiktok"]:
            res = discovery.discover_competitors(args.discover, platform)
            if res.get("competitors"):
                comp_list = [c.to_dict() for c in res["competitors"]]
                JSONWriter.save_competitors(platform, args.discover, comp_list)
            if res.get("raw_data"):
                JSONWriter.save_raw_response(platform, f"discover_{args.discover}", "raw_discovery.json", res["raw_data"])

    if args.youtube:
        collector = YouTubeCollector()
        data = collector.collect_videos(args.youtube)
        logger.info(f"Collected YouTube videos for {args.youtube}.")
        save_collected_data("youtube", args.youtube, data)
        
    if args.instagram:
        collector = InstagramCollector()
        data = collector.collect_posts(args.instagram)
        logger.info(f"Collected Instagram posts for {args.instagram}.")
        save_collected_data("instagram", args.instagram, data)
        
    if args.tiktok:
        collector = TikTokCollector()
        data = collector.collect_videos_sync(args.tiktok)
        logger.info(f"Collected TikTok videos for {args.tiktok}.")
        save_collected_data("tiktok", args.tiktok, data)
        
    if not any([args.youtube, args.instagram, args.tiktok, args.discover]):
        logger.warning("No targets specified. Use --help for usage.")

if __name__ == "__main__":
    main()
