"""Parser tests: no network needed, pure functions only."""

import sys
from pathlib import Path
from urllib.parse import urljoin

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from main import (  # noqa: E402
    extract_book_record,
    normalize_record,
    validate_and_store,
)


BOOK_HTML = """
<html><body>
  <div class="product_main">
    <h1>Test Book</h1>
    <p class="price_color">\u00a351.77</p>
    <p class="instock availability">In stock (22 available)</p>
    <p class="star-rating Three"></p>
  </div>
  <div id="product_description" class="sub-header"><h2>Product Description</h2></div>
  <p>A real description.</p>
</body></html>
"""


def test_price_normalization():
    record = extract_book_record(BOOK_HTML, "https://x/book/1/", "https://x/page-1")
    normalized = normalize_record(record)
    assert normalized["price_text"] == "\u00a351.77"
    assert normalized["price_gbp"] == 51.77
    assert isinstance(normalized["price_gbp"], float)


def test_relative_to_absolute_url():
    page_url = "https://books.toscrape.com/catalogue/page-1.html"
    href = "a-light-in-the-attic_1000/index.html"
    absolute = urljoin(page_url, href)
    assert absolute == "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"


def test_missing_description_is_null():
    html = BOOK_HTML.replace(
        '<div id="product_description" class="sub-header"><h2>Product Description</h2></div>',
        "",
    )
    record = extract_book_record(html, "https://x/book/2/", "https://x/page-1")
    assert record["description"] is None


def test_duplicate_urls_count_once():
    records = [
        extract_book_record(BOOK_HTML, "https://x/book/1/", "https://x/page-1"),
        extract_book_record(BOOK_HTML, "https://x/book/1/", "https://x/page-2"),
    ]
    result = validate_and_store(records)
    assert result["valid"] == 1
    assert result["invalid"] == 0


def test_malformed_fixture_rejected():
    html = "<html><body><div class='product_main'><h1></h1></div></body></html>"
    record = extract_book_record(html, "https://x/book/3/", "https://x/page-1")
    record["title"] = ""
    result = validate_and_store([record])
    assert result["valid"] == 0
    assert result["invalid"] == 1


def test_all_eight_raw_keys_present():
    record = extract_book_record(BOOK_HTML, "https://x/book/1/", "https://x/page-1")
    assert set(record.keys()) == {
        "title",
        "product_url",
        "price_text",
        "availability_text",
        "rating_text",
        "description",
        "source_page",
        "fetched_at",
    }
