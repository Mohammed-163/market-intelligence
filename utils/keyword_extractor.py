"""
keyword_extractor.py
Deterministic keyword extraction from collected Instagram data.
Analyzes bio, captions, hashtags, and profile name to generate ranked niche keywords.
Optional Gemini enhancement if API keys are available.
"""
import re
from collections import Counter
from utils.logger import get_logger
from config.constants import MAX_KEYWORDS

logger = get_logger()

# Common stop words and Instagram filler that should never be keywords
STOP_WORDS = frozenset([
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "not", "no", "nor",
    "so", "if", "then", "than", "too", "very", "just", "about", "above",
    "after", "again", "all", "also", "am", "any", "as", "back", "because",
    "before", "between", "both", "each", "few", "get", "got", "he", "her",
    "here", "him", "his", "how", "i", "im", "into", "it", "its", "let",
    "like", "me", "more", "most", "much", "my", "new", "now", "off", "old",
    "only", "other", "our", "out", "own", "over", "say", "she", "some",
    "still", "such", "take", "tell", "that", "their", "them", "these",
    "they", "this", "those", "through", "under", "up", "us", "use", "want",
    "way", "we", "well", "what", "when", "where", "which", "while", "who",
    "why", "you", "your",
    # Instagram filler
    "follow", "followers", "following", "link", "bio", "click", "check",
    "post", "posts", "comment", "comments", "share", "tag", "repost",
    "dm", "swipe", "tap", "story", "stories", "reel", "reels", "live",
    "giveaway", "contest", "hashtag", "instagood", "instadaily",
    "photooftheday", "picoftheday", "love", "life", "happy", "beautiful",
    "amazing", "best", "good", "great", "day", "today", "tomorrow",
    "yesterday", "morning", "night", "via", "please", "thanks", "thank",
    "see", "look", "go", "going", "come", "know", "think", "make",
    "made", "one", "two", "three", "first", "last", "next", "every",
])

# Minimum word length to consider
MIN_WORD_LENGTH = 3


def extract_hashtags(raw_posts: list) -> list:
    """Extract all hashtags from post captions."""
    hashtags = []
    for item in raw_posts:
        caption = item.get("caption", "") or ""
        # Extract #hashtag patterns
        found = re.findall(r"#(\w+)", caption, re.UNICODE)
        for h in found:
            h_lower = h.lower()
            if h_lower not in STOP_WORDS and len(h_lower) >= MIN_WORD_LENGTH:
                hashtags.append(h_lower)
    return hashtags


def extract_bio_terms(bio: str) -> list:
    """Extract meaningful terms from the profile bio."""
    if not bio:
        return []
    # Remove URLs and special chars
    bio_clean = re.sub(r"https?://\S+", "", bio)
    bio_clean = re.sub(r"[^\w\s]", " ", bio_clean)
    words = bio_clean.lower().split()
    return [w for w in words if w not in STOP_WORDS and len(w) >= MIN_WORD_LENGTH]


def extract_caption_terms(raw_posts: list) -> list:
    """Extract meaningful terms from all captions (excluding hashtags)."""
    terms = []
    for item in raw_posts:
        caption = item.get("caption", "") or ""
        # Remove hashtags and URLs
        clean = re.sub(r"#\w+", "", caption)
        clean = re.sub(r"https?://\S+", "", clean)
        clean = re.sub(r"@\w+", "", clean)
        clean = re.sub(r"[^\w\s]", " ", clean)
        words = clean.lower().split()
        for w in words:
            if w not in STOP_WORDS and len(w) >= MIN_WORD_LENGTH:
                terms.append(w)
    return terms


def extract_profile_name_terms(username: str, full_name: str = None) -> list:
    """Extract terms from profile name and username."""
    terms = []
    # Split username by common separators
    parts = re.split(r"[._\-]", username.lower())
    for p in parts:
        if p not in STOP_WORDS and len(p) >= MIN_WORD_LENGTH:
            terms.append(p)
    if full_name:
        words = re.sub(r"[^\w\s]", " ", full_name.lower()).split()
        for w in words:
            if w not in STOP_WORDS and len(w) >= MIN_WORD_LENGTH:
                terms.append(w)
    return terms


def rank_keywords(all_terms: list, max_keywords: int = MAX_KEYWORDS) -> list:
    """
    Rank keywords by frequency. Returns all unique keywords up to max_keywords,
    sorted by relevance (frequency descending).
    No artificial minimum — if the account produces 1 keyword, return 1.
    """
    counter = Counter(all_terms)
    # Return up to max_keywords, sorted by frequency
    ranked = [term for term, _count in counter.most_common(max_keywords)]
    return ranked


def extract_keywords(collected_data: dict, max_keywords: int = MAX_KEYWORDS) -> list:
    """
    Main entry point. Extracts and ranks niche keywords from collected Instagram data.
    
    Args:
        collected_data: The unified dict returned by InstagramCollector.collect_posts()
        max_keywords: Maximum number of keywords to return (configurable, default 15)
    
    Returns:
        Ranked list of keyword strings. Length depends on account content (1 to max_keywords).
    """
    raw_posts = collected_data.get("raw_posts", [])
    normalized_account = collected_data.get("normalized_account", {})
    
    username = normalized_account.get("username", "")
    bio = normalized_account.get("bio", "")
    
    logger.info(f"Extracting keywords from @{username} data...")
    
    # Collect all terms from different sources
    all_terms = []
    
    # 1. Hashtags (highest signal — count each occurrence x3 for ranking boost)
    hashtags = extract_hashtags(raw_posts)
    all_terms.extend(hashtags * 3)
    
    # 2. Bio terms (high signal — count x2)
    bio_terms = extract_bio_terms(bio)
    all_terms.extend(bio_terms * 2)
    
    # 3. Profile name terms (high signal — count x2)
    profile_terms = extract_profile_name_terms(username)
    all_terms.extend(profile_terms * 2)
    
    # 4. Caption terms (normal weight)
    caption_terms = extract_caption_terms(raw_posts)
    all_terms.extend(caption_terms)
    
    if not all_terms:
        logger.warning(f"No meaningful terms found for @{username}. Falling back to username.")
        return [username]
    
    keywords = rank_keywords(all_terms, max_keywords)
    
    logger.info(f"Extracted {len(keywords)} keywords for @{username}: {keywords}")
    return keywords


def extract_keywords_with_gemini(collected_data: dict, gemini_key: str, max_keywords: int = MAX_KEYWORDS) -> list:
    """
    Enhanced keyword extraction using Gemini LLM.
    Falls back to deterministic extraction if Gemini fails.
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        
        normalized_account = collected_data.get("normalized_account", {})
        raw_posts = collected_data.get("raw_posts", [])
        
        username = normalized_account.get("username", "")
        bio = normalized_account.get("bio", "") or ""
        
        # Build context from captions
        captions = []
        for item in raw_posts[:10]:  # Use up to 10 captions
            caption = item.get("caption", "")
            if caption:
                captions.append(caption[:200])  # Truncate long captions
        
        prompt = f"""Analyze this Instagram account and extract niche/industry keywords.

Username: {username}
Bio: {bio}
Sample captions:
{chr(10).join(captions[:5])}

Return ONLY a JSON array of keyword strings representing the account's business niche, 
industry, services, and topics. No explanations. Example: ["product photography", "ecommerce"]

Keywords:"""
        
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        
        import json
        # Try to parse JSON array from response
        text = response.text.strip()
        # Handle markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        
        keywords = json.loads(text)
        if isinstance(keywords, list) and len(keywords) > 0:
            keywords = [k.lower().strip() for k in keywords if isinstance(k, str)]
            keywords = keywords[:max_keywords]
            logger.info(f"Gemini extracted {len(keywords)} keywords for @{username}: {keywords}")
            return keywords
    except Exception as e:
        logger.warning(f"Gemini keyword extraction failed: {e}. Falling back to deterministic extraction.")
    
    return extract_keywords(collected_data, max_keywords)
