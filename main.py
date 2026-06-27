"""
main.py
Entry point for the Market Intelligence pipeline.

Usage:
    python main.py --instagram Smart.lens.iq --report
    python main.py --youtube UCxxxxx --tiktok username --report
    python main.py --discover "beauty salon" --instagram account
"""
import argparse
import sys
from utils.logger import get_logger
from config.settings import Settings

logger = get_logger()


def main():
    parser = argparse.ArgumentParser(description="Market Intelligence Data Collector & Analyser")
    parser.add_argument("--instagram", help="Instagram username")
    parser.add_argument("--tiktok",    help="TikTok username")
    parser.add_argument("--youtube",   help="YouTube channel ID")
    parser.add_argument("--discover",  help="Keyword to discover competitors")
    # BUG FIX: --report flag was completely missing from argparse
    parser.add_argument("--report",    action="store_true", help="Generate full analysis report")
    args = parser.parse_args()

    if not any([args.youtube, args.instagram, args.tiktok, args.discover]):
        logger.warning("No targets specified. Use --help for usage.")
        sys.exit(0)

    logger.info("=== Market Intelligence pipeline starting ===")
    settings = Settings.load()

    # ── STEP 1: Collect ───────────────────────────────────────────────────────
    raw_data = {}

    if args.instagram:
        from collectors.instagram_collector import InstagramCollector
        collector = InstagramCollector()
        posts = collector.collect_posts(args.instagram)
        raw_data["instagram"] = {"account": args.instagram, "posts": posts}
        logger.info(f"[Collect] Instagram: {len(posts)} posts")

    if args.youtube:
        from collectors.youtube_collector import YouTubeCollector
        collector = YouTubeCollector()
        videos = collector.collect_videos(args.youtube)
        raw_data["youtube"] = {"account": args.youtube, "posts": videos}
        logger.info(f"[Collect] YouTube: {len(videos)} videos")

    if args.tiktok:
        from collectors.tiktok_collector import TikTokCollector
        collector = TikTokCollector()
        videos = collector.collect_videos_sync(args.tiktok)
        raw_data["tiktok"] = {"account": args.tiktok, "posts": videos}
        logger.info(f"[Collect] TikTok: {len(videos)} videos")

    if args.discover:
        from collectors.competitor_discovery import CompetitorDiscovery
        discovery = CompetitorDiscovery()
        for platform in ["instagram", "tiktok", "youtube"]:
            comp = discovery.discover_competitors(args.discover, platform)
            logger.info(f"[Discover] {platform}: {len(comp)} competitors found")

    if not args.report:
        logger.info("Collection complete. Pass --report to run full analysis.")
        return

    # ── STEP 2–6: Analyze → Sentiment → Competitors → Report → Save ──────────
    from analyzers.account_analyzer   import AccountAnalyzer
    from analyzers.engagement_analyzer import EngagementAnalyzer
    from analyzers.content_analyzer   import ContentAnalyzer
    from analyzers.sentiment_analyzer  import SentimentAnalyzer
    from services.gemini_service       import GeminiService
    from services.report_service       import ReportService

    if not settings.secrets.gemini_keys:
        logger.error("No Gemini keys found. Sentiment analysis will be skipped.")

    gemini   = GeminiService(settings.secrets.gemini_keys) if settings.secrets.gemini_keys else None
    reporter = ReportService()

    for platform, data in raw_data.items():
        posts    = data.get("posts", [])
        account  = data.get("account", "unknown")
        profile  = posts[0] if posts else {}

        followers = (
            profile.get("followersCount", 0) or
            profile.get("statistics", {}).get("subscriberCount", 0)
        )

        # Step 2: Analyze
        eng_summary  = EngagementAnalyzer().summary(followers, posts)
        content_data = ContentAnalyzer().analyze_by_type(posts)
        timing_data  = ContentAnalyzer().analyze_posting_times(posts)
        activity     = AccountAnalyzer().analyze_activity(posts)
        logger.info(f"[Analyze] {platform}: ER={eng_summary['er_percent']}%")

        # Step 3: Sentiment
        sentiment = {"positive": 0.0, "neutral": 0.0, "negative": 0.0, "total": 0}
        if gemini:
            comments_raw = []
            for p in posts:
                for c in p.get("latestComments", []):
                    text = c.get("text") or c.get("ownerUsername", "")
                    if text:
                        comments_raw.append(text)
            sentiment = SentimentAnalyzer(gemini).analyze(comments_raw)
            logger.info(f"[Sentiment] {platform}: {sentiment}")

        # Step 4: Build report
        report_data = {
            "platform":   platform,
            "profile":    profile,
            "engagement": eng_summary,
            "content":    {**content_data, **timing_data},
            "sentiment":  sentiment,
            "activity":   activity,
            "competitors": {},
        }
        report = reporter.build(report_data, account)

        # Step 5: Save
        safe_name = account.replace(".", "_").replace("/", "_")
        reporter.save_json(report, safe_name)
        reporter.save_markdown(report, safe_name)
        logger.info(f"[Report] Saved → data/reports/{safe_name}.json/.md")

    logger.info("=== Pipeline complete ===")


if __name__ == "__main__":
    main()
