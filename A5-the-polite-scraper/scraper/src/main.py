"""Polite scraper for Books to Scrape (first 3 catalogue pages, 60 books)."""

import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
OUTPUT_DIR = ROOT / "output"

SITE_URL = "https://books.toscrape.com/"
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/TheSant0x/FlyRank-Internship)"
TIMEOUT = 10
DELAY_SECONDS = 0.5

CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


def fetch_page(url: str, cache_path: Path | None) -> dict:
    """Fetch a page politely, or serve it from cache when a cached copy exists.

    Returns {"status": "fetch"|"cache"|"error", "text", "size", "url"}.
    """
    if cache_path is not None and cache_path.exists():
        text = cache_path.read_text(encoding="utf-8")
        return {"status": "cache", "text": text, "size": len(text.encode()), "url": url}

    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        return {"status": "error", "error": str(exc), "size": 0, "url": url}

    if response.status_code != 200:
        return {
            "status": "error",
            "error": f"HTTP {response.status_code}",
            "size": len(response.content),
            "url": url,
        }

    if cache_path is not None:
        cache_path.write_text(response.text, encoding="utf-8")
    return {
        "status": "fetch",
        "text": response.text,
        "size": len(response.content),
        "url": url,
    }


def main():
    page_one = f"{SITE_URL}catalogue/page-1.html"
    cache_path = CACHE_DIR / "catalogue-page-1.html"
    result = fetch_page(page_one, cache_path)
    print(f"{result['status'].upper()} {result['size']} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
