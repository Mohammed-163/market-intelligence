import argparse
import sys
from utils.logger import get_logger
from config.settings import Settings
from collectors.youtube_collector import YouTubeCollector
from collectors.instagram_collector import InstagramCollector
from collectors.tiktok_collector import TikTokCollector
from collectors.competitor_discovery import CompetitorDiscovery

logger = get_logger()

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
            discovery.discover_competitors(args.discover, platform)

    if args.youtube:
        collector = YouTubeCollector()
        videos = collector.collect_videos(args.youtube)
        logger.info(f"Collected {len(videos)} YouTube videos.")
        
    if args.instagram:
        collector = InstagramCollector()
        posts = collector.collect_posts(args.instagram)
        logger.info(f"Collected {len(posts)} Instagram posts.")
        
    if args.tiktok:
        collector = TikTokCollector()
        videos = collector.collect_videos_sync(args.tiktok)
        logger.info(f"Collected {len(videos)} TikTok videos.")

    if not any([args.youtube, args.instagram, args.tiktok, args.discover]):
        logger.warning("No targets specified. Use --help for usage.")

if __name__ == "__main__":
    main()
