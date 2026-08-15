"""Polite scraper for Books to Scrape (first 3 catalogue pages, 60 books)."""

import os
import re
import sys
import time
import json
import csv
import random
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, ValidationError

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
OUTPUT_DIR = ROOT / "output"

SITE_URL = "https://books.toscrape.com/"
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/TheSant0x/FlyRank-Internship)"
TIMEOUT = 10
DELAY_SECONDS = 0.5
RETRYABLE_STATUS = {500, 502, 503, 504}
MAX_RETRIES = 4

CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


class BookRecord(BaseModel):
    """The validated shape of one finished record."""

    title: str = Field(min_length=1)
    product_url: str = Field(pattern=r"^https://")
    price_text: str | None = None
    price_gbp: float | None = None
    availability_text: str | None = None
    rating_text: str | None = None
    description: str | None = None
    source_page: str = Field(pattern=r"^https://")
    fetched_at: str


def fetch_page(url: str, cache_path: Path | None) -> dict:
    """Fetch a page politely, or serve it from cache when a cached copy exists.

    Returns {"status": "fetch"|"cache"|"error", "text", "size", "url"}.
    """
    if cache_path is not None and cache_path.exists():
        text = cache_path.read_text(encoding="utf-8")
        return {"status": "cache", "text": text, "size": len(text.encode()), "url": url}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
            )
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                return {"status": "error", "error": str(exc), "size": 0, "url": url}
            time.sleep(min(2 ** (attempt - 1), 8) + random.uniform(0, 0.5))
            continue

        if response.status_code == 200:
            break
        if response.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES:
            retry_after = response.headers.get("Retry-After")
            try:
                wait = float(retry_after) if retry_after else None
            except ValueError:
                wait = None
            if wait is None:
                wait = min(2 ** (attempt - 1), 8) + random.uniform(0, 0.5)
            time.sleep(wait)
            continue
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


def catalogue_page_url(page_number: int) -> str:
    return f"{SITE_URL}catalogue/page-{page_number}.html"


def discover_catalogue(max_pages: int = 3) -> dict:
    """Follow the catalogue's own 'next' links and collect every book URL.

    Returns {"catalogue_pages", "discovered", "unique_urls", "book_urls",
    "cache_hits", "fetches"}.
    """
    book_urls = []
    cache_hits = 0
    fetches = 0
    page_number = 1

    while page_number <= max_pages:
        url = catalogue_page_url(page_number)
        cache_path = CACHE_DIR / f"catalogue-page-{page_number}.html"
        result = fetch_page(url, cache_path)
        if result["status"] == "cache":
            cache_hits += 1
        elif result["status"] == "fetch":
            fetches += 1
        else:
            break

        soup = BeautifulSoup(result["text"], "lxml")
        for link in soup.select("article.product_pod h3 a"):
            book_urls.append(urljoin(url, link["href"]))

        next_link = soup.select_one("li.next a")
        if next_link is None or page_number >= max_pages:
            break
        page_number += 1
        if result["status"] == "fetch":
            time.sleep(DELAY_SECONDS)

    unique_urls = sorted(set(book_urls))
    return {
        "catalogue_pages": page_number,
        "discovered": len(book_urls),
        "unique_urls": len(unique_urls),
        "book_urls": unique_urls,
        "cache_hits": cache_hits,
        "fetches": fetches,
    }


def extract_book_record(html: str, product_url: str, source_page: str) -> dict:
    """Pull the eight raw fields out of one book page."""
    soup = BeautifulSoup(html, "lxml")
    product = soup.select_one("div.product_main") or soup

    title_tag = product.select_one("h1")
    price_tag = product.select_one("p.price_color")
    availability_tag = product.select_one("p.instock.availability")
    rating_tag = product.select_one("p.star-rating")
    description_tags = soup.select("#product_description ~ p")
    description_tag = description_tags[-1] if description_tags else None

    price_text = price_tag.get_text(" ", strip=True) if price_tag else None
    price_text = re.sub(r"[^\d.]", "", price_text or "")
    price_text = f"£{price_text}" if price_text else None

    availability_text = (
        availability_tag.get_text(" ", strip=True) if availability_tag else None
    )
    rating_text = None
    if rating_tag:
        for cls in rating_tag.get("class", []):
            if cls != "star-rating":
                rating_text = cls
                break

    description = description_tag.get_text(" ", strip=True) if description_tag else None

    return {
        "title": title_tag.get_text(" ", strip=True) if title_tag else None,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def normalize_record(record: dict) -> dict:
    """Turn raw strings into clean values; raw and clean live side by side."""
    normalized = dict(record)
    price_text = record.get("price_text")
    try:
        normalized["price_gbp"] = float(price_text.removeprefix("£")) if price_text else None
    except ValueError:
        normalized["price_gbp"] = None
    return normalized


def validate_and_store(records: list[dict]) -> dict:
    """Validate every record, write books.json (deduped by canonical URL) and errors.json."""
    seen = {}
    errors = []
    for record in records:
        normalized = normalize_record(record)
        try:
            validated = BookRecord.model_validate(normalized)
        except ValidationError as exc:
            errors.append(
                {
                    "product_url": normalized.get("product_url"),
                    "reason": exc.errors(),
                }
            )
            continue
        seen[validated.product_url] = validated.model_dump()

    books = list(seen.values())
    (OUTPUT_DIR / "books.json").write_text(
        json.dumps(books, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUTPUT_DIR / "errors.json").write_text(
        json.dumps(errors, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {"valid": len(books), "invalid": len(errors)}


def export_csv(books: list[dict]) -> None:
    """Produce books.csv from the validated records (extras)."""
    if not books:
        return
    fieldnames = list(books[0].keys())
    with (OUTPUT_DIR / "books.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(books)


def collect_records(book_urls: list[str], source_pages: dict) -> dict:
    """Fetch (or read from cache) every book page and extract its raw record.

    One broken page is logged and skipped; it never kills the run.
    """
    records = []
    failed_pages = []
    cache_hits = 0
    fetches = 0
    for product_url in book_urls:
        slug = product_url.rstrip("/").split("/")[-2]
        cache_path = CACHE_DIR / f"book-{slug}.html"
        result = fetch_page(product_url, cache_path)
        if result["status"] == "cache":
            cache_hits += 1
        elif result["status"] == "fetch":
            fetches += 1
            time.sleep(DELAY_SECONDS)
        else:
            failed_pages.append({"url": product_url, "error": result.get("error")})
            continue
        records.append(
            extract_book_record(
                result["text"], product_url, source_pages.get(product_url, SITE_URL)
            )
        )
    return {
        "records": records,
        "cache_hits": cache_hits,
        "fetches": fetches,
        "failed_pages": failed_pages,
    }


def write_run_report(started: float, discovery: dict, collected: dict, stored: dict) -> None:
    """Write a few honest numbers about the run to output/run-report.json."""
    report = {
        "started_at": datetime.fromtimestamp(started, timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "duration_seconds": round(time.time() - started, 2),
        "catalogue_pages": discovery["catalogue_pages"],
        "discovered_urls": discovery["discovered"],
        "unique_urls": discovery["unique_urls"],
        "pages_fetched": collected["fetches"],
        "cache_hits": collected["cache_hits"],
        "valid_records": stored["valid"],
        "invalid_records": stored["invalid"],
        "failed_pages": len(collected["failed_pages"]),
    }
    (OUTPUT_DIR / "run-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )


def main():
    started = time.time()
    discovery = discover_catalogue()
    # Map each book URL back to the catalogue page it came from.
    book_to_source = {}
    for i in range(1, discovery["catalogue_pages"] + 1):
        cache_path = CACHE_DIR / f"catalogue-page-{i}.html"
        soup = BeautifulSoup(cache_path.read_text(encoding="utf-8"), "lxml")
        page_url = catalogue_page_url(i)
        for link in soup.select("article.product_pod h3 a"):
            book_to_source[urljoin(page_url, link["href"])] = page_url

    collected = collect_records(
        discovery["book_urls"], book_to_source
    )
    stored = validate_and_store(collected["records"])
    books = json.loads((OUTPUT_DIR / "books.json").read_text(encoding="utf-8"))
    export_csv(books)
    write_run_report(started, discovery, collected, stored)
    print(f"stored valid={stored['valid']} invalid={stored['invalid']}")
    print(f"failed_pages={len(collected['failed_pages'])}")
    print(f"detail_pages={len(collected['records'])} "
          f"(cache_hits={collected['cache_hits']}, fetches={collected['fetches']})")
    if collected["records"]:
        print("---- sample raw record ----")
        print(collected["records"][0])
    print(
        f"catalogue_pages={discovery['catalogue_pages']} "
        f"discovered={discovery['discovered']} "
        f"unique_urls={discovery['unique_urls']} "
        f"(cache_hits={discovery['cache_hits']}, fetches={discovery['fetches']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
