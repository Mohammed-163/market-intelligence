import os
import shutil
import re
from loguru import logger as loguru_logger

log_lines = []

def log_sink(message):
    log_lines.append(str(message).strip())

loguru_logger.add(log_sink, format="{message}", level="DEBUG")

# Clean previous test data
if os.path.exists("data"):
    shutil.rmtree("data")

from pipeline import run_pipeline
from config.settings import Settings

def extract_logs():
    print("\n" + "="*70)
    print("PHASE 1 & 2 PROOFS")
    print("="*70)
    
    # 1. Instagram Discovery Flow
    ig_keywords = []
    ig_raw = {}
    ig_parsed = {}
    
    for line in log_lines:
        if "[IG TRACE] keyword=" in line:
            kw = line.split("keyword=")[1]
            if kw not in ig_keywords:
                ig_keywords.append(kw)
                ig_raw[kw] = 0
                ig_parsed[kw] = 0
        elif "[IG TRACE] raw results count=" in line:
            kw = ig_keywords[-1] if ig_keywords else "Unknown"
            ig_raw[kw] = int(line.split("count=")[1])
        elif "[IG TRACE] parsed competitors count=" in line:
            kw = ig_keywords[-1] if ig_keywords else "Unknown"
            ig_parsed[kw] = int(line.split("count=")[1])
            
    # Aggregate values
    ig_deduped = 0
    ig_saved = 0
    for line in log_lines:
        if "[IG TRACE] competitors after dedup=" in line:
            ig_deduped = int(line.split("dedup=")[1])
        elif "[IG TRACE] Saved=" in line:
            ig_saved = int(line.split("Saved=")[1])

    # 2. Gemini Flow
    gemini_prompt = ""
    gemini_response = ""
    gemini_keywords = []
    
    for i, line in enumerate(log_lines):
        if "[GEMINI TRACE] Prompt:" in line:
            gemini_prompt = line.split("Prompt: ")[1]
        elif "[GEMINI TRACE] Raw response:" in line:
            gemini_response = line.split("Raw response: ")[1]
        elif "Gemini selected Competitor Search Keywords:" in line:
            gemini_keywords = line.split("Keywords: ")[1]

    # Print Instagram Proofs
    print("\n--- INSTAGRAM COMPETITOR DISCOVERY ---")
    for kw in ig_keywords:
        print(f"Keyword: {kw}")
        print(f"Raw results: {ig_raw[kw]}")
        print(f"Parsed competitors: {ig_parsed[kw]}")
        print("-" * 30)
    print(f"After deduplication: {ig_deduped}")
    print(f"Saved: {ig_saved}")
    
    # Print Gemini Proofs
    print("\n--- GEMINI KEYWORD QUALITY ---")
    print(f"Exact prompt sent (snippet): {gemini_prompt}")
    print(f"Raw response: {gemini_response}")
    print(f"Selected Keywords: {gemini_keywords}")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    settings = Settings.load()
    # Trigger pipeline
    run_pipeline("smart.lens.iq", posts_limit=5, cache=None, settings=settings)
    extract_logs()
