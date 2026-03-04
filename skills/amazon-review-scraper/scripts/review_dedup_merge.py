#!/usr/bin/env python3
"""
Review Dedup & Merge v1.0
双源评论去重合并：Woot JSON + Sorftime JSON → 统一格式输出。

用法:
    python3 review_dedup_merge.py --woot /tmp/ASIN_reviews.json --sorftime /tmp/ASIN_sorftime.json -o /tmp/ASIN_merged.json
    python3 review_dedup_merge.py --woot /tmp/ASIN_reviews.json  # 仅 Woot，统一格式
    python3 review_dedup_merge.py --sorftime /tmp/ASIN_sorftime.json  # 仅 Sorftime，统一格式

去重策略:
    - 匹配键: normalize(title) + normalize(text[:100])
    - 重复时保留 Woot 版本（元数据更丰富），合并 Sorftime 的变体属性
"""

import json
import re
import html
import argparse
import sys
from datetime import datetime


def normalize(s):
    """Normalize string for dedup matching: lowercase, strip whitespace/punctuation."""
    s = html.unescape(s or "")
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", s)
    return s


def dedup_key(title, text):
    """Generate dedup key from title + first 100 chars of text."""
    return normalize(title) + "|" + normalize(text[:100])


def parse_woot_date(origin_desc):
    """Parse date from Woot OriginDescription like 'Reviewed in the United States on February 27, 2026'."""
    m = re.search(r"on (\w+ \d+, \d{4})", origin_desc or "")
    if m:
        try:
            return datetime.strptime(m.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def parse_sorftime_date(date_str):
    """Parse date from Sorftime format like '20260228'."""
    if date_str and len(date_str) == 8:
        try:
            return datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def woot_to_unified(r):
    """Convert Woot review to unified format."""
    return {
        "title": html.unescape(r.get("Title", "")),
        "text": r.get("Text", ""),
        "rating": r.get("OverallRating", 0),
        "date": parse_woot_date(r.get("OriginDescription", "")),
        "author": r.get("Author"),
        "variant": None,
        "verified_purchase": r.get("IsVerifiedPurchase"),
        "vine_review": r.get("IsVineReview"),
        "helpful_votes": r.get("HelpfulVotes", 0),
        "image_urls": r.get("ImageUrls", []),
        "media_urls": r.get("MediaUrls", []),
        "source": "woot",
    }


def sorftime_to_unified(r):
    """Convert Sorftime review to unified format."""
    variant = r.get("评论产品的属性", "")
    return {
        "title": r.get("标题", ""),
        "text": r.get("评论", ""),
        "rating": int(r.get("评星", 0)),
        "date": parse_sorftime_date(r.get("评论日期", "")),
        "author": None,
        "variant": variant if variant else None,
        "verified_purchase": None,
        "vine_review": None,
        "helpful_votes": None,
        "image_urls": [],
        "media_urls": [],
        "source": "sorftime",
    }


def merge_reviews(woot_file=None, sorftime_file=None):
    """Merge and deduplicate reviews from both sources."""
    seen = {}
    merged = []
    stats = {"woot_total": 0, "sorftime_total": 0, "overlap": 0, "woot_only": 0, "sorftime_only": 0}

    # Process Woot first (preferred source for duplicates)
    if woot_file:
        with open(woot_file, encoding="utf-8") as f:
            woot_data = json.load(f)
        woot_reviews = woot_data.get("reviews", woot_data if isinstance(woot_data, list) else [])
        stats["woot_total"] = len(woot_reviews)

        for r in woot_reviews:
            unified = woot_to_unified(r)
            k = dedup_key(unified["title"], unified["text"])
            seen[k] = unified
            merged.append(unified)

    # Process Sorftime
    if sorftime_file:
        with open(sorftime_file, encoding="utf-8") as f:
            sf_reviews = json.load(f)
        stats["sorftime_total"] = len(sf_reviews)

        for r in sf_reviews:
            unified = sorftime_to_unified(r)
            k = dedup_key(unified["title"], unified["text"])

            if k in seen:
                # Duplicate: keep Woot version but merge Sorftime's variant
                stats["overlap"] += 1
                existing = seen[k]
                if unified["variant"] and not existing["variant"]:
                    existing["variant"] = unified["variant"]
                    existing["source"] = "merged"
            else:
                seen[k] = unified
                merged.append(unified)

    stats["woot_only"] = stats["woot_total"] - stats["overlap"]
    stats["sorftime_only"] = stats["sorftime_total"] - stats["overlap"]
    stats["merged_total"] = len(merged)

    # Sort by date (newest first), nulls last
    merged.sort(key=lambda r: r["date"] or "0000-00-00", reverse=True)

    return merged, stats


def main():
    parser = argparse.ArgumentParser(description="Review Dedup & Merge - 双源评论去重合并")
    parser.add_argument("--woot", help="Woot JSON file path")
    parser.add_argument("--sorftime", "--sf", help="Sorftime JSON file path")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    args = parser.parse_args()

    if not args.woot and not args.sorftime:
        print("Error: at least one of --woot or --sorftime is required", file=sys.stderr)
        sys.exit(1)

    merged, stats = merge_reviews(args.woot, args.sorftime)

    output = json.dumps({
        "stats": stats,
        "reviews": merged,
    }, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(output)

    # Print stats to stderr
    print(f"\n--- Merge Stats ---", file=sys.stderr)
    print(f"Woot:     {stats['woot_total']} reviews", file=sys.stderr)
    print(f"Sorftime: {stats['sorftime_total']} reviews", file=sys.stderr)
    print(f"Overlap:  {stats['overlap']}", file=sys.stderr)
    print(f"Woot only:    {stats['woot_only']}", file=sys.stderr)
    print(f"SF only:      {stats['sorftime_only']}", file=sys.stderr)
    print(f"Merged total: {stats['merged_total']}", file=sys.stderr)


if __name__ == "__main__":
    main()
