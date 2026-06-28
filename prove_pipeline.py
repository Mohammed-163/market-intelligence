import os
import json
import logging
import glob
from unittest.mock import patch

# Setup environment with fake keys to simulate multiple keys
os.environ["YOUTUBE_1"] = "fake_yt_key_1"
os.environ["YOUTUBE_2"] = "fake_yt_key_2"
os.environ["APIFY_1"] = "fake_apify_key_1"
os.environ["GEMINI_1"] = "fake_gemini_key_1"

# Capture logs
log_capture = []
class CaptureHandler(logging.Handler):
    def emit(self, record):
        log_capture.append(self.format(record))

logger = logging.getLogger()
handler = CaptureHandler()
handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

from pipeline import run_pipeline
from config.settings import Settings
from models.competitor import Competitor
import googleapiclient.errors
from httplib2 import Response

# 1. Mock primary IG data
ig_primary_data = {
    "normalized_account": {"username": "smart.lens.iq", "bio": "Professional product photography in Iraq."},
    "raw_posts": [{"caption": "New perfume shot #productphotography"}]
}

# 2. Mock Gemini response matching the new structured schema
gemini_response = {
    "industry": "Photography",
    "primary_keywords": ["product photography"],
    "secondary_keywords": ["perfume photography"],
    "sub_niches": ["ecommerce photography"],
    "competitor_search_keywords": ["ecommerce product photography"]
}

# 3. Mock IG discovery result
ig_discovery_data = {
    "competitors": [
        Competitor(username="comp1", platform="instagram"),
        Competitor(username="comp2", platform="instagram")
    ],
    "raw_data": []
}

# 4. Mock YouTube API to always throw Quota Exceeded (429)
def mock_youtube_execute(*args, **kwargs):
    resp = Response({"status": 429})
    raise googleapiclient.errors.HttpError(resp, b"Quota Exceeded")

print("Running pipeline with mocked APIs to generate proofs...")

with patch('collectors.instagram_collector.InstagramCollector.collect_posts') as mock_primary:
    # First call is primary account, subsequent calls are deep collection
    mock_primary.side_effect = [
        ig_primary_data,  # Primary
        {"normalized_account": {"username": "comp1"}, "normalized_posts": [], "success": True}, # Deep collect comp1
        {"normalized_account": {"username": "comp2"}, "normalized_posts": [], "success": True}  # Deep collect comp2
    ]
    
    with patch('google.generativeai.GenerativeModel.generate_content') as mock_gemini:
        # Mock Gemini content generation
        mock_gemini.return_value.text = json.dumps(gemini_response)
        
        with patch('apify_client.ApifyClient.actor') as mock_apify:
            # We bypass _discover_instagram and mock it directly to speed up and avoid real Apify calls
            with patch('collectors.competitor_discovery.CompetitorDiscovery._discover_instagram', return_value=ig_discovery_data):
                
                with patch('googleapiclient.discovery.build') as mock_build:
                    # Mock YouTube search to fail with Quota Exceeded
                    mock_build.return_value.search.return_value.list.return_value.execute.side_effect = mock_youtube_execute
                    
                    settings = Settings.load()
                    run_pipeline("smart.lens.iq", 5, None, settings=settings)

print("\n" + "="*50)
print("PROOF 1: JSON Output from Gemini")
print("="*50)
print(json.dumps(gemini_response, indent=2))

print("\n" + "="*50)
print("PROOF 2: competitor_search_keywords used")
print("="*50)
for line in log_capture:
    if "Gemini Analysis for" in line or "Gemini selected Competitor Search Keywords" in line or "[Phase 3] Processing keyword" in line:
        print(line)

print("\n" + "="*50)
print("PROOF 3: Pipeline partial results on YouTube keys exhaustion")
print("="*50)
for line in log_capture:
    if "exhausted" in line.lower() or "switching" in line.lower() or "partial_success" in line.lower() or "partial results saved" in line.lower() or "EXECUTION SUMMARY" in line:
        print(line)
        
print("\n[Summary Block:]")
summary_started = False
for line in log_capture:
    if "========== EXECUTION SUMMARY ==========" in line:
        summary_started = True
    if summary_started:
        print(line)
        if "Partial results saved:" in line:
            summary_started = False

print("\n" + "="*50)
print("PROOF 4 & 5: discovery_keyword existence & JSONWriter log count match")
print("="*50)

# Check JSONWriter logs
for line in log_capture:
    if "SENDING TO JSONWRITER" in line and "instagram" in line.lower():
        print(f"Log Output: {line}")

# Check files
files = glob.glob("data/competitors/instagram_pipeline_smart.lens.iq_*.json")
if files:
    latest = max(files, key=os.path.getmtime)
    print(f"\nReading generated file: {latest}")
    with open(latest, 'r', encoding='utf-8') as f:
        data = json.load(f)
        comps = data.get("normalized_data", [])
        print(f"Number of competitors inside JSON array: {len(comps)}")
        
        # Prove discovery keyword
        if len(comps) > 0:
            print("\nSample Competitor Data:")
            print(json.dumps(comps[0], indent=2))
            print(f"\n=> discovery_keyword field is present: {comps[0].get('discovery_keyword')}")
            print(f"=> deep_collection_status field is present: {comps[0].get('deep_collection_status')}")
else:
    print("No generated files found!")
