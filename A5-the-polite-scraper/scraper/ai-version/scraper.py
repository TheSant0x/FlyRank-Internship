"""AI-generated polite scraper (quarantined for review)."""

import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUT = Path("output")
OUT.mkdir(exist_ok=True)


def get(url):
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.text


def scrape():
    books = []
    for page in range(1, 4):
        html = get(f"https://books.toscrape.com/catalogue/page-{page}.html")
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("h3 a"):
            url = "https://books.toscrape.com/catalogue/" + a["href"]
            detail = get(url)
            ds = BeautifulSoup(detail, "html.parser")
            title = ds.select_one("h1").text.strip()
            price = ds.select_one("p.price_color").text.strip()
            books.append(
                {
                    "title": title,
                    "product_url": url,
                    "price": price,
                    "availability": ds.select_one("p.instock").text.strip(),
                    "rating": ds.select_one("p.star-rating").get("class")[1],
                }
            )
            time.sleep(0.1)
    (OUT / "books.json").write_text(json.dumps(books, indent=2), encoding="utf-8")
    print(f"wrote {len(books)} books")


if __name__ == "__main__":
    scrape()
