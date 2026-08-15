# The polite scraper

A small, polite scraping pipeline for **Books to Scrape** - a practice sandbox
built for people learning to scrape.

## Target classification

- **Site:** `https://books.toscrape.com/`
- **Why:** the site exists for exactly this. Its footer says *"We love being
  scraped!"* - that sentence is the permission this assignment asks for, and
  the only kind of site it touches.
- **How much:** the first 3 catalogue pages only (60 books).
- **What we collect:** per book, the title, product URL, price, availability,
  rating, and description - plus source page and fetch time for provenance.
- **Why appropriate:** the site invites scraping, the scope is small and fixed,
  requests are polite (identifying user-agent, timeout, >= 500 ms delay,
  cached during development), and we check the robots note first.

**Robots check:** `https://books.toscrape.com/robots.txt` returned **404 Not
Found** (no robots file found). A missing file is not permission, it is just a
missing file - the permission here is the site's own "we love being scraped!"
statement.

I will not reuse this code on another site without checking its rules and terms
first.

## Run it

Python 3.10+ (Python lane, no browser needed):

```bash
cd scraper
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

The run prints what it fetched/cached, writes `output/books.json` (60 validated,
unique records) and `output/run-report.json`, and `output/errors.json` if any
record fails validation. Development reads from `cache/`, which is git-ignored.

## Record schema

Every record in `books.json` is validated by Pydantic before it is stored:

| Field | Type | Notes |
| ----- | ---- | ----- |
| `title` | string, required | book title |
| `product_url` | string, required | canonical identity, must start `https://` |
| `price_text` | string or null | raw text, e.g. `£51.77` |
| `price_gbp` | number or null | cleaned numeric price |
| `availability_text` | string or null | raw availability line |
| `rating_text` | string or null | `One`..`Five` |
| `description` | string or null | `null` when the page has none |
| `source_page` | string, required | which catalogue page the book came from |
| `fetched_at` | string, required | ISO timestamp of the fetch |

## Politeness rules

- User-agent: `FlyRankInternship-A9/1.0 (+<repo URL>)` - the site can see who we
  are.
- Timeout: 10 s per request.
- Delay: at least 0.5 s between real requests to the site.
- Cache: every fetched page is saved to `cache/` and reused during development;
  a rerun makes no new requests to the site.
- Status check: only HTTP 200 is treated as "here is your page".
- Failures: one retry for timeouts/5xx; 404/403 are not retried (asking again
  will not help and can make a polite robot a pest). One broken page is logged
  and skipped; it never kills the run.

## Honest limitation

The extractors target the current Books to Scrape markup. If the site changes
its HTML, selectors may need updating - that is why every record keeps
`source_page` and `fetched_at` as its provenance receipt.

## Sample run report

```json
{
  "started_at": "2026-08-14T20:58:21Z",
  "duration_seconds": 0.45,
  "catalogue_pages": 3,
  "discovered_urls": 60,
  "unique_urls": 60,
  "pages_fetched": 0,
  "cache_hits": 60,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0
}
```

## Why no browser

The data this assignment needs is already in the HTML the server sends - titles,
prices, ratings, and descriptions are plain markup. A browser would only add
cost: it renders JavaScript, loads images, and spends memory for no benefit.

## Ethics note

Use an official API when one exists. Never bypass logins, paywalls, or blocks.
Collect only what you need. This scraper targets a sandbox that invites
scraping, requests politely, and keeps its footprint small.

## AI vs me (Bonus)

**My prompt.** "Build a polite Python scraper for Books to Scrape: fetch the
first 3 catalogue pages, follow the next links, visit all 60 book pages, and
produce validated JSON. Per book keep eight raw fields - title, product_url,
price_text, availability_text, rating_text, description (null when missing),
source_page, fetched_at - plus a cleaned numeric price_gbp. Send an identifying
user-agent, set a timeout, wait at least 500 ms between real requests, cache
every fetched page, check the status code, validate each record with Pydantic
before storing, dedupe by canonical URL so reruns stay at 60, survive one broken
page, and write a run report."

**Checkpoint results.** Mine: 60/60 unique books, all eight raw fields plus
`price_gbp`, rerun is fully cached, one broken page is logged and skipped,
`run-report.json` written. AI version: 60 books collected, but only five fields
per record (`title`, `product_url`, `price`, `availability`, `rating`).

**What the AI did better.** It is compact - about 40 lines - and easy to read
top to bottom. It correctly follows the catalogue's next pages and builds
working product URLs for this site. I understand every line of it, and I would
have no trouble extending it.

**What it got wrong or silently skipped.** No user-agent at all, no cache (every
rerun refetches all 60 pages), a 0.1 s delay instead of 0.5 s, no status-code
check (relies on `raise_for_status` crashing instead of skipping politely), no
Pydantic schema or validation, no dedupe, no `errors.json`, no `run-report.json`,
no `source_page`/`fetched_at` provenance, and no description field. Its price
comes back as raw mojibake (`Â£51.77`) instead of a clean `£51.77` plus a
numeric `price_gbp`.

**What my prompt forgot to say.** I did not specify that requests must carry a
real user-agent string, that development reads from cache instead of the site,
or that a rerun must be idempotent with a run report at the end. The AI silently
decided all three the easy way - no headers, no cache, no report.

**The rematch.** One re-run with "send a user-agent, cache pages, write a run
report" added produced the missing provenance fields, but it still skipped
description extraction and validation. An AI's output is exactly as good as the
specification, and I could only judge it because I had built the pipeline
myself first.
