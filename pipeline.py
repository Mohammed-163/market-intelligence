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


def _save_merged_competitors(platform: str, ig_username: str, competitors: list, errors: list = None) -> dict:
    """Save deduplicated competitor list for a platform."""
    if not competitors and not errors:
        return {}

    logger.info(f"[TRACE] BEFORE SAVE: {len(competitors)} {platform} competitors")
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

    logger.info(f"[TRACE] SENDING TO JSONWRITER: {len(competitors_serialized)} competitors")
    
    competitors_file = None
    if competitors_serialized:
        logger.info(f"[TRACE] FILE WILL BE CREATED AT: data/competitors/{platform}_pipeline_{ig_username}_{timestamp}.json")
        # Save normalized competitor data
        competitors_file = JSONWriter.save_entity(
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
        "status": "partial_success" if errors else "success",
        "partial_results_saved": bool(competitors_file),
        f"{platform}_competitors_collected": len(competitors_serialized),
        "errors": errors or [],
        "source_account": ig_username,
    }
    if competitors_file:
        manifest["competitors_file"] = competitors_file
        manifest["raw_file"] = f"data/raw/{platform}/competitors_{ig_username}_{timestamp}.json"
        
    JSONWriter.save_manifest(platform, f"pipeline_{ig_username}", timestamp, manifest)
    logger.info(f"Saved {len(competitors)} deduplicated {platform} competitors for @{ig_username}")
    return manifest


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
    
    global_errors = []
    ig_discovered_count = 0
    yt_discovered_count = 0

    for keyword in keywords:
        logger.info(f"[Phase 3] Processing keyword: '{keyword}'")

        # ── Instagram discovery ──
        try:
            ig_result = discovery.discover_competitors(keyword, "instagram", cache=cache)
            if ig_result and ig_result.get("competitors"):
                ig_discovered_count += len(ig_result["competitors"])
                for comp in ig_result["competitors"]:
                    comp_obj = comp if hasattr(comp, 'username') else None
                    if comp_obj is None:
                        key = comp.get("username", "").lower()
                    else:
                        key = comp_obj.username.lower()

                    if key == ig_username.lower():
                        continue

                    if key and key not in ig_seen:
                        ig_seen.add(key)
                        ig_competitors.append(comp)
        except Exception as e:
            logger.error(f"Instagram discovery failed for '{keyword}': {e}")
            global_errors.append({"platform": "instagram", "keyword": keyword, "error": str(e)})

        # ── YouTube discovery ──
        try:
            yt_result = discovery.discover_competitors(keyword, "youtube", cache=cache)
            if yt_result and yt_result.get("competitors"):
                yt_discovered_count += len(yt_result["competitors"])
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
                        uname = comp.username if hasattr(comp, 'username') else comp.get("username", "")
                        if uname and uname not in yt_seen:
                            yt_seen.add(uname)
                            yt_competitors.append(comp)
        except Exception as e:
            logger.error(f"YouTube discovery failed for '{keyword}': {e}")
            global_errors.append({"platform": "youtube", "keyword": keyword, "error": str(e)})

        # ── TikTok discovery (try once, not per keyword) ──
        if tiktok_result is None:
            try:
                tiktok_result = discovery.discover_competitors(keyword, "tiktok", cache=cache)
                if tiktok_result and tiktok_result.get("supported") is False:
                    logger.info(f"[Phase 3] TikTok discovery: {tiktok_result.get('reason', 'Not supported')}")
                    global_errors.append({"platform": "tiktok", "error": tiktok_result.get("reason")})
                elif tiktok_result and tiktok_result.get("competitors"):
                    for comp in tiktok_result["competitors"]:
                        key = comp.username.lower() if hasattr(comp, 'username') else comp.get("username", "").lower()
                        if key and key not in tiktok_seen:
                            tiktok_seen.add(key)
            except Exception as e:
                logger.warning(f"TikTok discovery failed: {e}")
                tiktok_result = {"supported": False, "reason": f"TikTok discovery failed: {e}"}
                global_errors.append({"platform": "tiktok", "error": str(e)})

    logger.info(f"[TRACE] AFTER DEDUPLICATION:")
    logger.info(f"[TRACE]   Instagram competitors: {len(ig_competitors)}")
    logger.info(f"[TRACE]   YouTube competitors:   {len(yt_competitors)}")

    # ─────────────────────────────────────────────
    # Phase 5: Save deduplicated results
    # ─────────────────────────────────────────────
    logger.info("[Phase 5] Saving deduplicated competitors...")

    ig_errors = [e for e in global_errors if e["platform"] == "instagram"]
    yt_errors = [e for e in global_errors if e["platform"] == "youtube"]

    _save_merged_competitors("instagram", ig_username, ig_competitors, errors=ig_errors)
    _save_merged_competitors("youtube", ig_username, yt_competitors, errors=yt_errors)

    if tiktok_result:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        tk_errors = [e for e in global_errors if e["platform"] == "tiktok"]
        manifest = {
            "status": "partial_success" if tk_errors else "success",
            "source_account": ig_username,
            "platform": "tiktok",
            "errors": tk_errors,
            "reason": tiktok_result.get("reason")
        }
        JSONWriter.save_manifest("tiktok", f"pipeline_{ig_username}", timestamp, manifest)

    # Calculate final stats
    ig_collected = sum(1 for c in ig_competitors if getattr(c, 'deep_collection_status', None) == 'success')
    yt_collected = sum(1 for c in yt_competitors if getattr(c, 'deep_collection_status', None) == 'success')

    logger.info("=" * 60)
    logger.info("========== EXECUTION SUMMARY ==========")
    logger.info(f"Source Account: @{ig_username}")
    logger.info(f"Keywords Generated: {len(keywords)}")
    logger.info(f"Instagram competitors discovered: {ig_discovered_count}")
    logger.info(f"Instagram competitors collected:  {ig_collected} (total deduped: {len(ig_competitors)})")
    logger.info(f"YouTube competitors discovered:   {yt_discovered_count}")
    logger.info(f"YouTube competitors collected:    {yt_collected} (total deduped: {len(yt_competitors)})")
    logger.info(f"TikTok competitors collected:     0 (Unsupported)")
    logger.info(f"Total failures encountered:       {len(global_errors)}")
    logger.info(f"Partial results saved:            True")
    logger.info("=" * 60)
