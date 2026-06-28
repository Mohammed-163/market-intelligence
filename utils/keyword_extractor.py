from collections import Counter
import re
from typing import List, Dict, Any
from utils.logger import get_logger
from config.constants import MAX_KEYWORDS

logger = get_logger()

def extract_hashtags(posts: List[Dict[str, Any]]) -> List[str]:
    """Extract all hashtags from post captions."""
    hashtags = []
    for post in posts:
        caption = post.get("caption", "")
        if caption:
            tags = re.findall(r'#(\w+)', caption)
            hashtags.extend([t.lower() for t in tags])
    return hashtags

def _clean_text(text: str) -> str:
    """Basic text cleanup."""
    # Remove URLs
    text = re.sub(r'http\S+', '', text)
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_keywords_with_gemini(collected_data: dict, gemini_key: str, max_keywords: int = MAX_KEYWORDS) -> list:
    """
    Enhanced keyword extraction using Gemini LLM.
    Sends full bio, all unique hashtags, and cleaned captions to Gemini.
    Expects a structured JSON response and returns `competitor_search_keywords`.
    Falls back to deterministic extraction if Gemini fails.
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        
        normalized_account = collected_data.get("normalized_account", {})
        raw_posts = collected_data.get("raw_posts", [])
        
        username = normalized_account.get("username", "")
        bio = normalized_account.get("bio", "") or ""
        
        # 1. Full Bio
        full_bio = _clean_text(bio)
        
        # 2. All Unique Hashtags
        all_hashtags = list(set(extract_hashtags(raw_posts)))
        
        # 3. Cleaned Captions
        all_captions = []
        for item in raw_posts:
            caption = item.get("caption", "")
            if caption:
                clean_cap = _clean_text(caption)
                if clean_cap:
                    all_captions.append(clean_cap)
                    
        # Assemble text block for Gemini (limit to ~50k chars for safety, though Flash supports 1M)
        MAX_CONTEXT_CHARS = 50000
        text_block = f"Username: {username}\n\nBio: {full_bio}\n\nHashtags: {' '.join(all_hashtags)}\n\n"
        
        # Sort captions by length descending as a proxy for "richest content" if engagement isn't available
        # Or just use the first N because raw_posts usually sorted by recency in Apify.
        unique_captions = list(dict.fromkeys(all_captions))
        
        for i, cap in enumerate(unique_captions):
            addition = f"Caption {i+1}: {cap}\n"
            if len(text_block) + len(addition) > MAX_CONTEXT_CHARS:
                text_block += "\n[Remaining captions truncated due to context limit]"
                break
            text_block += addition
        
        prompt = f"""Analyze this Instagram account's data and extract its niche, industry, and search keywords.

{text_block}

Keyword extraction requirements:
1. You must return ONLY a valid JSON object matching this schema:
{{
  "industry": "string",
  "primary_keywords": ["string"],
  "secondary_keywords": ["string"],
  "sub_niches": ["string"],
  "competitor_search_keywords": ["string"]
}}
2. Ensure 'competitor_search_keywords' contains highly specific, long-tail commercial search phrases that would yield direct competitors in a YouTube/Instagram search.
3. FORBIDDEN WORDS: Do not use single words, brand names, usernames, or generic words like: lens, smart, اعلان, تصوير, photo, photography, business, company, service, official, viral, fyp.
4. EXACT LENGTH REQUIREMENT: Every phrase in 'competitor_search_keywords' MUST be exactly 2 to 6 words long. Single words are completely banned.
5. 'competitor_search_keywords' must have between 1 and {max_keywords} keywords.

JSON Output:"""
        
        logger.info(f"[GEMINI TRACE] Prompt: {prompt[:300]}... (truncated)")
        logger.info(f"[GEMINI TRACE] Context chars: {len(text_block)}")
        
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        
        import json
        text = response.text.strip()
        logger.info(f"[GEMINI TRACE] Raw response: {text}")
        
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            
        parsed_json = json.loads(text)
        
        search_keywords = parsed_json.get("competitor_search_keywords", [])
        if isinstance(search_keywords, list) and len(search_keywords) > 0:
            search_keywords = [k.lower().strip() for k in search_keywords if isinstance(k, str)]
            search_keywords = search_keywords[:max_keywords]
            
            # Log the full structure for debugging/visibility
            logger.info(f"Gemini Analysis for @{username}: Industry='{parsed_json.get('industry')}', Primary={parsed_json.get('primary_keywords')}")
            logger.info(f"Gemini selected Competitor Search Keywords: {search_keywords}")
            return search_keywords
            
        raise ValueError("Invalid JSON structure or empty competitor_search_keywords")
        
    except Exception as e:
        logger.warning(f"Gemini keyword extraction failed: {e}. Falling back to deterministic extraction.")
        return extract_keywords(collected_data, max_keywords)


# =====================================================================
# Deterministic Fallback Logic
# =====================================================================

def extract_bio_terms(bio: str) -> List[str]:
    if not bio:
        return []
    words = re.findall(r'\b[a-zA-Z]{4,}\b', bio.lower())
    return [w for w in words if w not in STOP_WORDS]

def extract_profile_name_terms(name: str) -> List[str]:
    if not name:
        return []
    name = re.sub(r'[^a-zA-Z\s]', ' ', name)
    words = name.lower().split()
    return [w for w in words if len(w) > 2 and w not in STOP_WORDS]

def extract_caption_terms(posts: List[Dict[str, Any]]) -> List[str]:
    terms = []
    for post in posts:
        caption = post.get("caption", "")
        if caption:
            words = re.findall(r'\b[a-zA-Z]{4,}\b', caption.lower())
            terms.extend([w for w in words if w not in STOP_WORDS])
    return terms

def rank_keywords(all_terms: List[str], limit: int) -> List[str]:
    counter = Counter(all_terms)
    return [term for term, _ in counter.most_common(limit)]

def extract_keywords(collected_data: dict, max_keywords: int = MAX_KEYWORDS) -> list:
    """
    Fallback deterministic keyword extraction.
    Ranks terms based on frequency across hashtags, bio, name, and captions.
    """
    normalized_account = collected_data.get("normalized_account", {})
    raw_posts = collected_data.get("raw_posts", [])
    
    username = normalized_account.get("username", "")
    bio = normalized_account.get("bio", "")
    full_name = normalized_account.get("full_name", "")
    
    all_terms = []
    
    # 1. Hashtags (highest signal — count x3)
    hashtags = extract_hashtags(raw_posts)
    all_terms.extend(hashtags * 3)
    
    # 2. Bio terms (high signal — count x2)
    bio_terms = extract_bio_terms(bio)
    all_terms.extend(bio_terms * 2)
    
    # 3. Profile name terms (high signal — count x2)
    profile_terms = extract_profile_name_terms(username)
    all_terms.extend(profile_terms * 2)
    if full_name:
        all_terms.extend(extract_profile_name_terms(full_name) * 2)
    
    # 4. Caption terms (normal weight)
    caption_terms = extract_caption_terms(raw_posts)
    all_terms.extend(caption_terms)
    
    if not all_terms:
        logger.warning(f"No meaningful terms found for @{username}. Falling back to username.")
        return [username]
    
    keywords = rank_keywords(all_terms, max_keywords)
    logger.info(f"Deterministic extraction found {len(keywords)} keywords for @{username}: {keywords}")
    return keywords

STOP_WORDS = {
    "this", "that", "with", "from", "your", "have", "what", "there", "their",
    "will", "would", "about", "which", "when", "make", "like", "time", "just",
    "know", "take", "people", "year", "good", "some", "could", "them", "see",
    "other", "than", "then", "now", "look", "only", "come", "its", "over", "think",
    "also", "back", "after", "use", "two", "how", "our", "work", "first", "well",
    "way", "even", "new", "want", "because", "any", "these", "give", "day", "most", "us",
    "photo", "photography", "business", "company", "service", "official", "viral", "fyp",
    "video", "post", "reel", "follow", "like", "comment", "share"
}
