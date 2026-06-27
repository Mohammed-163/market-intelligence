"""
pipeline.py
End-to-end orchestrator.
Starting from ONLY an Instagram username, automatically:
  1. Collects primary account data
  2. Extracts niche keywords (deterministic or Gemini-enhanced)
  3. Discovers competitors on Instagram + YouTube (+ TikTok attempt)
  4. Deep-collects top competitors
  5. Deduplicates across keywords
  6. Saves normalized data, raw responses, and manifests
"""
from datetime import datetime, timezone
from utils.logger import get_logger
from utils.keyword_extractor import extract_keywords, extract_keywords_with_gemini
from collectors.instagram_collector import InstagramCollector
from collectors.competitor_discovery import CompetitorDiscovery
from storage.json_writer import JSONWriter
from config.constants import MAX_KEYWORDS

logger = get_logger()


def _process_and_save(platform: str, username: str, data: dict, posts_limit: int):
    """Save normalized data, raw responses, and manifest for a single collection result."""
    if not data:
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    metadata = data.get("metadata", {})
    metadata["posts_limit"] = posts_limit

    manifest = {}

    # 1. Raw dump
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
        competitors_serialized = [
            c.to_dict() if hasattr(c, 'to_dict') else c
            for c in data["competitors"]
        ]
        manifest["competitors_file"] = JSONWriter.save_entity(
            "competitors", platform, username, timestamp,
            metadata, competitors_serialized, data.get("raw_data", [])
        )

    # 6. Manifest
    JSONWriter.save_manifest(platform, username, timestamp, manifest)
    logger.info(f"Saved all entities for {platform}: {username}")


def _save_keywords(keywords: list, ig_username: str):
    """Save extracted keywords as a JSON artifact."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    metadata = {
        "source_account": ig_username,
        "extraction_date": datetime.now(timezone.utc).isoformat(),
        "keyword_count": len(keywords),
    }
    JSONWriter.save_entity(
        "keywords", "instagram", ig_username, timestamp,
        metadata, {"keywords": keywords}, {}
    )
    logger.info(f"Saved {len(keywords)} extracted keywords for @{ig_username}")


def _save_merged_competitors(platform: str, ig_username: str, competitors: list):
    """Save deduplicated competitor list for a platform."""
    if not competitors:
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    metadata = {
        "source_account": ig_username,
        "platform": platform,
        "collection_date": datetime.now(timezone.utc).isoformat(),
        "competitor_count": len(competitors),
        "collector_version": "2.0",
        "api_used": "pipeline_discovery",
    }

    competitors_serialized = [
        c.to_dict() if hasattr(c, 'to_dict') else c
        for c in competitors
    ]

    # Save normalized competitor data
    JSONWriter.save_entity(
        "competitors", platform, f"pipeline_{ig_username}", timestamp,
        metadata, competitors_serialized, []
    )

    # Save raw competitor data separately
    JSONWriter.save_pure_raw(
        platform, f"competitors_{ig_username}", timestamp,
        competitors_serialized
    )

    # Save manifest
    manifest = {
        "competitors_file": f"data/competitors/{platform}_pipeline_{ig_username}_{timestamp}.json",
        "raw_file": f"data/raw/{platform}/competitors_{ig_username}_{timestamp}.json",
        "competitor_count": len(competitors),
        "source_account": ig_username,
    }
    JSONWriter.save_manifest(platform, f"pipeline_{ig_username}", timestamp, manifest)
    logger.info(f"Saved {len(competitors)} deduplicated {platform} competitors for @{ig_username}")


def run_pipeline(ig_username: str, posts_limit: int, cache, settings=None):
    """
    Full end-to-end pipeline. Only requires an Instagram username.
    
    Flow:
      1. Collect primary Instagram account
      2. Extract keywords from collected data
      3. For each keyword: discover competitors on IG + YT + TikTok
      4. Deduplicate competitors across all keywords
      5. Save everything (normalized, raw, manifests)
    """
    logger.info("=" * 60)
    logger.info(f"PIPELINE START — Source: @{ig_username}")
    logger.info("=" * 60)

    # ─────────────────────────────────────────────
    # Phase 1: Collect primary Instagram account
    # ─────────────────────────────────────────────
    logger.info("[Phase 1] Collecting primary Instagram account...")
    ig_collector = InstagramCollector()
    primary_data = ig_collector.collect_posts(ig_username, max_results=posts_limit, cache=cache)

    if not primary_data or not primary_data.get("raw_posts"):
        logger.error(f"Failed to collect data for @{ig_username}. Pipeline aborted.")
        return

    _process_and_save("instagram", ig_username, primary_data, posts_limit)
    logger.info(f"[Phase 1] Primary account @{ig_username} collected and saved.")

    # ─────────────────────────────────────────────
    # Phase 2: Extract keywords (with optional Gemini)
    # ─────────────────────────────────────────────
    logger.info("[Phase 2] Extracting niche keywords...")

    keywords = []
    if settings and hasattr(settings, 'secrets') and settings.secrets.gemini_keys:
        gemini_key = settings.secrets.gemini_keys[0]
        logger.info("[Phase 2] Gemini key found — using LLM-enhanced extraction.")
        keywords = extract_keywords_with_gemini(primary_data, gemini_key, MAX_KEYWORDS)
    else:
        logger.info("[Phase 2] No Gemini keys — using deterministic extraction.")
        keywords = extract_keywords(primary_data, MAX_KEYWORDS)

    if not keywords:
        logger.warning("[Phase 2] No keywords extracted. Pipeline cannot discover competitors.")
        return

    _save_keywords(keywords, ig_username)
    logger.info(f"[Phase 2] Keywords extracted: {keywords}")

    # ─────────────────────────────────────────────
    # Phase 3 + 4: Discover + Deep-collect competitors
    # ─────────────────────────────────────────────
    logger.info("[Phase 3] Discovering competitors across platforms...")

    discovery = CompetitorDiscovery()

    # Accumulators for dedup
    ig_seen = set()         # key: username (lowercase)
    yt_seen = set()         # key: channel_id
    tiktok_seen = set()     # key: username (lowercase)

    ig_competitors = []
    yt_competitors = []
    tiktok_result = None

    for keyword in keywords:
        logger.info(f"[Phase 3] Processing keyword: '{keyword}'")

        # ── Instagram discovery ──
        try:
            ig_result = discovery.discover_competitors(keyword, "instagram", cache=cache)
            if ig_result and ig_result.get("competitors"):
                for comp in ig_result["competitors"]:
                    comp_obj = comp if hasattr(comp, 'username') else None
                    if comp_obj is None:
                        # Came from cache as dict
                        key = comp.get("username", "").lower()
                    else:
                        key = comp_obj.username.lower()

                    # Skip the source account itself
                    if key == ig_username.lower():
                        continue

                    if key and key not in ig_seen:
                        ig_seen.add(key)
                        ig_competitors.append(comp)
        except Exception as e:
            logger.error(f"Instagram discovery failed for '{keyword}': {e}")

        # ── YouTube discovery ──
        try:
            yt_result = discovery.discover_competitors(keyword, "youtube", cache=cache)
            if yt_result and yt_result.get("competitors"):
                for comp in yt_result["competitors"]:
                    if hasattr(comp, 'channel_id'):
                        key = comp.channel_id
                    elif isinstance(comp, dict):
                        key = comp.get("channel_id", "")
                    else:
                        key = ""

                    if key and key not in yt_seen:
                        yt_seen.add(key)
                        yt_competitors.append(comp)
                    elif not key:
                        # No channel_id, fallback to username dedup
                        uname = comp.username if hasattr(comp, 'username') else comp.get("username", "")
                        if uname and uname not in yt_seen:
                            yt_seen.add(uname)
                            yt_competitors.append(comp)
        except Exception as e:
            logger.error(f"YouTube discovery failed for '{keyword}': {e}")

        # ── TikTok discovery (try once, not per keyword) ──
        if tiktok_result is None:
            try:
                tiktok_result = discovery.discover_competitors(keyword, "tiktok", cache=cache)
                if tiktok_result and tiktok_result.get("supported") is False:
                    logger.info(f"[Phase 3] TikTok discovery: {tiktok_result.get('reason', 'Not supported')}")
                elif tiktok_result and tiktok_result.get("competitors"):
                    for comp in tiktok_result["competitors"]:
                        key = comp.username.lower() if hasattr(comp, 'username') else comp.get("username", "").lower()
                        if key and key not in tiktok_seen:
                            tiktok_seen.add(key)
            except Exception as e:
                logger.warning(f"TikTok discovery failed: {e}")
                tiktok_result = {"supported": False, "reason": f"TikTok discovery failed: {e}"}

    # ─────────────────────────────────────────────
    # Phase 5: Save deduplicated results
    # ─────────────────────────────────────────────
    logger.info("[Phase 5] Saving deduplicated competitors...")
    logger.info(f"  Instagram: {len(ig_competitors)} unique competitors")
    logger.info(f"  YouTube:   {len(yt_competitors)} unique competitors")

    _save_merged_competitors("instagram", ig_username, ig_competitors)
    _save_merged_competitors("youtube", ig_username, yt_competitors)

    # Save TikTok status
    if tiktok_result:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        JSONWriter.save_entity(
            "competitors", "tiktok", f"pipeline_{ig_username}", timestamp,
            {"source_account": ig_username, "platform": "tiktok"},
            tiktok_result, []
        )

    logger.info("=" * 60)
    logger.info(f"PIPELINE COMPLETE — @{ig_username}")
    logger.info(f"  Keywords used:          {len(keywords)}")
    logger.info(f"  Instagram competitors:  {len(ig_competitors)}")
    logger.info(f"  YouTube competitors:    {len(yt_competitors)}")
    logger.info("=" * 60)
