#!/usr/bin/env python3
"""
Amazon Review Scraper v1.0

Scrape Amazon product reviews (written reviews) via woot.com's public AJAX API.
No API key, no login, no browser automation required. Pure Python 3 stdlib.

Usage:
    python3 amazon_review_scraper.py B0BLCBRBVZ
    python3 amazon_review_scraper.py B0BLCBRBVZ --output reviews.json
    python3 amazon_review_scraper.py B0BLCBRBVZ --mode basic     # Quick, max 100 reviews
    python3 amazon_review_scraper.py B0BLCBRBVZ --mode full      # Split by star rating
    python3 amazon_review_scraper.py B0BLCBRBVZ --mode max       # Star x sort combos, max extraction (default)

How it works:
    woot.com/review/Reviews/{ASIN} is an AJAX endpoint that returns Amazon review JSON.
    Each (filter, sort) combination returns up to 100 reviews.
    By iterating 5 star ratings x 4 sort orders and deduplicating, we maximize extraction.

Limits:
    - Max 100 reviews per (filter, sort) combination (API hard limit)
    - Products with >135 five-star reviews cannot be fully extracted
    - Products with <500 written reviews can typically be fully extracted
    - Only retrieves written reviews, not star-only ratings
    - Amazon US (amazon.com) only
"""

import json
import urllib.request
import urllib.parse
import sys
import time
import argparse
from datetime import datetime


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

BASE_URL = "https://www.woot.com/review/Reviews/"


def fetch_reviews(asin, filter_val=0, sort_val=0, delay=0.2):
    """Fetch reviews for a single (filter, sort) combination. Max 100 reviews."""
    url_base = BASE_URL + asin
    reviews = []
    paging_next = None
    page_num = 0

    while True:
        page_num += 1
        params = {
            "filter": str(filter_val),
            "isVerified": "false",
            "sort": str(sort_val),
        }

        if paging_next:
            params["pagingNext"] = paging_next
        else:
            params["page"] = "1"

        url = url_base + "?" + urllib.parse.urlencode(params)
        headers = {**HEADERS, "Referer": f"https://www.woot.com/review/{asin}"}
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"  Error (filter={filter_val}, sort={sort_val}, page={page_num}): {e}", file=sys.stderr)
            break

        batch = data.get("Reviews", [])
        if not batch:
            break

        reviews.extend(batch)

        paging_next = data.get("PagingNext", "")
        if not paging_next:
            break

        time.sleep(delay)

    return reviews


def review_key(r):
    """Generate a deduplication key for a review."""
    author = r.get("Author", "")
    title = r.get("Title", "")
    text = r.get("Text", "")[:80]
    return (author, title, text)


def scrape_basic(asin):
    """Basic mode: filter=0, sort=0, max 100 reviews."""
    print(f"[basic] Scraping {asin} ...", file=sys.stderr)
    reviews = fetch_reviews(asin, filter_val=0, sort_val=0)
    print(f"[basic] Got {len(reviews)} reviews", file=sys.stderr)
    return reviews


def scrape_full(asin):
    """Full mode: split by star rating, max 100 per star."""
    print(f"[full] Scraping {asin} by star rating ...", file=sys.stderr)
    seen = set()
    unique = []

    for star in [5, 4, 3, 2, 1]:
        revs = fetch_reviews(asin, filter_val=star, sort_val=0)
        new_count = 0
        for r in revs:
            k = review_key(r)
            if k not in seen:
                seen.add(k)
                unique.append(r)
                new_count += 1
        print(f"  {star}★: {len(revs)} fetched, {new_count} new (total: {len(unique)})", file=sys.stderr)

    print(f"[full] Total unique: {len(unique)}", file=sys.stderr)
    return unique


def scrape_max(asin):
    """Max mode: 5 star ratings x 4 sort orders, deduplicated for maximum extraction."""
    print(f"[max] Scraping {asin} (star x sort combinations) ...", file=sys.stderr)
    seen = set()
    unique = []
    sort_names = {0: "Top", 1: "Recent", 2: "Sort2", 3: "Sort3"}

    for star in [5, 4, 3, 2, 1]:
        star_before = len(unique)
        for sort_val in [0, 1, 2, 3]:
            revs = fetch_reviews(asin, filter_val=star, sort_val=sort_val, delay=0.15)
            new_count = 0
            for r in revs:
                k = review_key(r)
                if k not in seen:
                    seen.add(k)
                    unique.append(r)
                    new_count += 1
            if revs:
                print(f"  {star}★ sort={sort_val}({sort_names[sort_val]}): "
                      f"{len(revs)} fetched, +{new_count} new", file=sys.stderr)
        star_total = len(unique) - star_before
        print(f"  {star}★ subtotal: {star_total}", file=sys.stderr)

    print(f"[max] Total unique: {len(unique)}", file=sys.stderr)
    return unique


def build_summary(asin, reviews, mode):
    """Build summary statistics."""
    star_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    verified = 0
    with_images = 0
    with_video = 0

    for r in reviews:
        rating = r.get("OverallRating", 0)
        if rating in star_counts:
            star_counts[rating] += 1
        if r.get("IsVerifiedPurchase"):
            verified += 1
        if r.get("ImageUrls"):
            with_images += 1
        if r.get("MediaUrls"):
            with_video += 1

    return {
        "asin": asin,
        "mode": mode,
        "total_reviews": len(reviews),
        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "star_distribution": star_counts,
        "verified_purchases": verified,
        "with_images": with_images,
        "with_video": with_video,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Amazon Review Scraper - Scrape Amazon reviews via woot.com AJAX API"
    )
    parser.add_argument("asin", help="Amazon ASIN (e.g. B0BLCBRBVZ)")
    parser.add_argument("--mode", choices=["basic", "full", "max"], default="max",
                        help="Scrape mode: basic (100 cap) / full (by star) / max (star x sort, default)")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--summary", action="store_true", help="Only output summary statistics")

    args = parser.parse_args()

    # Scrape
    if args.mode == "basic":
        reviews = scrape_basic(args.asin)
    elif args.mode == "full":
        reviews = scrape_full(args.asin)
    else:
        reviews = scrape_max(args.asin)

    # Build output
    summary = build_summary(args.asin, reviews, args.mode)

    if args.summary:
        output = json.dumps(summary, ensure_ascii=False, indent=2)
    else:
        output = json.dumps({
            "summary": summary,
            "reviews": reviews,
        }, ensure_ascii=False, indent=2)

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\nSaved to {args.output}", file=sys.stderr)
    else:
        print(output)

    # Print summary to stderr
    print(f"\n--- Summary ---", file=sys.stderr)
    print(f"ASIN: {args.asin}", file=sys.stderr)
    print(f"Mode: {args.mode}", file=sys.stderr)
    print(f"Total: {summary['total_reviews']} reviews", file=sys.stderr)
    print(f"Stars: {summary['star_distribution']}", file=sys.stderr)
    print(f"Verified: {summary['verified_purchases']}", file=sys.stderr)
    print(f"With images: {summary['with_images']}", file=sys.stderr)
    print(f"With video: {summary['with_video']}", file=sys.stderr)


if __name__ == "__main__":
    main()
