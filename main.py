import argparse
import sys
import json
from utils.logger import get_logger
from config.settings import Settings
from collectors.youtube_collector import YouTubeCollector
from collectors.instagram_collector import InstagramCollector
from collectors.tiktok_collector import TikTokCollector
from collectors.competitor_discovery import CompetitorDiscovery
from ai.gemini_analyzer import GeminiAnalyzer
from db.database import SessionLocal, Account, Post, Insight

logger = get_logger()

def save_data(platform, account_name, results):
    db = SessionLocal()
    try:
        # Create or get account
        acc = db.query(Account).filter_by(platform=platform, username=account_name).first()
        if not acc:
            acc = Account(platform=platform, username=account_name)
            db.add(acc)
            db.commit()
            db.refresh(acc)
        
        for p in results:
            post = Post(
                account_id=acc.id,
                post_url=p.get('url') or p.get('post_url') or "N/A",
                caption=str(p.get('caption') or p.get('snippet', {}).get('title', '')),
                media_type=p.get('type') or "video",
                timestamp=str(p.get('timestamp') or "N/A")
            )
            db.add(post)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to save data: {e}")
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="Market Intelligence Data Collector")
    parser.add_argument("--youtube", help="YouTube Channel ID")
    parser.add_argument("--instagram", help="Instagram Username")
    parser.add_argument("--tiktok", help="TikTok Username")
    parser.add_argument("--discover", help="Keyword to discover competitors")
    parser.add_argument("--analyze", action="store_true", help="Run AI analysis on collected data")
    args = parser.parse_args()

    logger.info("Starting Market Intelligence collection...")
    settings = Settings.load()
    
    collected_data = []
    target = None

    if args.discover:
        discovery = CompetitorDiscovery()
        for platform in ["youtube", "instagram", "tiktok"]:
            discovery.discover_competitors(args.discover, platform)

    if args.youtube:
        collector = YouTubeCollector()
        videos = collector.collect_videos(args.youtube)
        logger.info(f"Collected {len(videos)} YouTube videos.")
        save_data("youtube", args.youtube, videos)
        collected_data.extend(videos)
        target = args.youtube
        
    if args.instagram:
        collector = InstagramCollector()
        posts = collector.collect_posts(args.instagram)
        logger.info(f"Collected {len(posts)} Instagram posts.")
        save_data("instagram", args.instagram, posts)
        collected_data.extend(posts)
        target = args.instagram
        
    if args.tiktok:
        collector = TikTokCollector()
        videos = collector.collect_videos_sync(args.tiktok)
        logger.info(f"Collected {len(videos)} TikTok videos.")
        save_data("tiktok", args.tiktok, videos)
        collected_data.extend(videos)
        target = args.tiktok
        
    if args.analyze and target and collected_data:
        analyzer = GeminiAnalyzer()
        # limit data size for prompt
        sample_data = collected_data[:10]
        report = analyzer.generate_market_report(target, sample_data)
        logger.info(f"AI Report:\n{report}")
        
        db = SessionLocal()
        db.add(Insight(target=target, insight_text=report))
        db.commit()
        db.close()

    if not any([args.youtube, args.instagram, args.tiktok, args.discover]):
        logger.warning("No targets specified. Use --help for usage.")

if __name__ == "__main__":
    main()
