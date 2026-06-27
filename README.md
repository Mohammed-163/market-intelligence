# Market Intelligence — Raw Data Collector

A **data collection system** that gathers raw data from Instagram, YouTube, and TikTok.  
No analysis, no scoring, no reports — just structured JSON files ready for downstream processing.

---

## What It Does

| Platform  | Method                        | Data Collected                         |
|-----------|-------------------------------|----------------------------------------|
| Instagram | Apify (key rotation × 3)     | Account info, last 20 posts, comments  |
| YouTube   | Official API (key rotation × 2) | Channel info, last 20 videos, comments |
| TikTok    | TikTokApi → Apify fallback   | Account info, last 20 videos, comments |

Additionally, a **competitor discovery** module finds 20 candidate competitors per platform using hashtags, keywords, and categories.

---

## Project Structure

```
market-intelligence/
│
├── collectors/                  # Platform-specific collectors
│   ├── __init__.py
│   ├── instagram_collector.py   # Instagram data via Apify
│   ├── youtube_collector.py     # YouTube data via official API
│   ├── tiktok_collector.py      # TikTok data via TikTokApi / Apify
│   └── competitor_discovery.py  # Discover competitor accounts
│
├── utils/                       # Shared utilities
│   ├── __init__.py
│   ├── logger.py                # Structured logging (loguru)
│   ├── retry.py                 # Retry + API key rotation logic
│   └── cache.py                 # SQLite cache (7-day TTL)
│
├── data/                        # Output directory (committed to repo)
│   ├── accounts/                # Account + posts JSON
│   ├── competitors/             # Competitor discovery JSON
│   ├── comments/                # Raw comments JSON
│   └── logs/                    # Application logs
│
├── main.py                      # Entry point
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

---

## API Keys (GitHub Secrets)

All keys are loaded from **GitHub Secrets** — never hardcoded.

| Secret      | Purpose                              |
|-------------|--------------------------------------|
| `YOUTUBE_1` | YouTube Data API key (primary)       |
| `YOUTUBE_2` | YouTube Data API key (fallback)      |
| `APIFY_1`   | Apify token (primary)               |
| `APIFY_2`   | Apify token (fallback 1)            |
| `APIFY_3`   | Apify token (fallback 2)            |
| `GEMINI_1`  | Reserved for future use             |
| `GEMINI_2`  | Reserved for future use             |

### Key Rotation

- **YouTube**: If a key returns `quotaExceeded`, `forbidden`, or HTTP errors → automatically switch to the next key.
- **Apify**: If a token returns credits exhausted, rate limited, actor failed, or timeout → automatically switch to the next token.

---

## Caching

Uses **SQLite** to avoid redundant paid API calls.

- If the same account was collected within the **last 7 days**, cached data is returned.
- Cache is stored locally (`.db` files are gitignored).

---

## Output Files

All output is **raw JSON**, committed to the repository automatically.

```
data/accounts/instagram_<username>.json
data/accounts/youtube_<channelname>.json
data/accounts/tiktok_<username>.json

data/competitors/instagram_competitors.json
data/competitors/youtube_competitors.json
data/competitors/tiktok_competitors.json

data/comments/instagram_comments.json
data/comments/youtube_comments.json
data/comments/tiktok_comments.json
```

---

## Auto-Commit

After every data update, the system automatically runs:

```bash
git add .
git commit -m "Data update - YYYY-MM-DD HH:MM:SS"
git push
```

---

## Usage

```bash
pip install -r requirements.txt
python main.py
```

You will be prompted for at least one of:
- Instagram username
- YouTube channel URL
- TikTok username

---

## License

Private project — all rights reserved.
