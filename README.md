# Amazon Review Scraper

Scrape Amazon product reviews (written reviews) via woot.com's public AJAX API.

**No API key. No login. No browser automation. Pure Python 3 stdlib.**

## How It Works

`woot.com/review/Reviews/{ASIN}` is a public AJAX endpoint that returns Amazon review data as JSON. Each `(star_filter, sort_order)` combination returns up to 100 reviews. By iterating across 5 star ratings x 4 sort orders and deduplicating, we maximize extraction — typically 85-100% of all written reviews.

## Quick Start

```bash
# Clone
git clone https://github.com/mrlong0129/amazon-review-scraper.git
cd amazon-review-scraper

# Scrape (no install needed, just Python 3)
python3 amazon_review_scraper.py B0BLCBRBVZ
```

## Usage

```bash
# Default: max mode (star x sort combos, maximum extraction)
python3 amazon_review_scraper.py B0BLCBRBVZ

# Save to file
python3 amazon_review_scraper.py B0BLCBRBVZ -o reviews.json

# Quick mode (max 100 reviews)
python3 amazon_review_scraper.py B0BLCBRBVZ --mode basic

# Split by star rating (max 500 reviews)
python3 amazon_review_scraper.py B0BLCBRBVZ --mode full

# Only print summary stats
python3 amazon_review_scraper.py B0BLCBRBVZ --summary
```

## Modes

| Mode | Max Reviews | Speed | Best For |
|------|-------------|-------|----------|
| `basic` | 100 | Fast | Quick preview |
| `full` | 500 | Medium | Most products |
| `max` | ~500-700 | Slower | Maximum extraction (default) |

## Output Format

```json
{
  "summary": {
    "asin": "B0BLCBRBVZ",
    "mode": "max",
    "total_reviews": 242,
    "scraped_at": "2026-03-03 10:30:00",
    "star_distribution": {"5": 80, "4": 50, "3": 30, "2": 40, "1": 42},
    "verified_purchases": 230,
    "with_images": 15,
    "with_video": 3
  },
  "reviews": [
    {
      "Author": "John D.",
      "Title": "Great product",
      "Text": "Full review text...",
      "OverallRating": 5,
      "OriginDescription": "Reviewed in the United States on February 21, 2026",
      "IsVerifiedPurchase": true,
      "IsVineReview": false,
      "HelpfulVotes": 12,
      "ImageUrls": [],
      "MediaUrls": []
    }
  ]
}
```

## Coverage

| Product Size | Expected Coverage |
|-------------|-------------------|
| < 100 written reviews | **100%** |
| 100 - 500 | **~95-100%** |
| 500 - 1000 | **~85-95%** |
| > 1000 | **~70-85%** |

### Important: Ratings vs Reviews

Amazon shows "X ratings" which includes **star-only ratings** (no text). This tool only retrieves **written reviews** — typically 10-15% of total ratings. A product with "2,000 ratings" may have ~200-300 written reviews.

## Requirements

- Python 3.6+
- No external dependencies (uses only stdlib: `urllib`, `json`, `argparse`)

## Limitations

- Amazon US (`amazon.com`) only — woot.com proxies US reviews
- Written reviews only, not star-only ratings
- 100 reviews per `(filter, sort)` combination (API hard limit)
- Products with >135 five-star written reviews cannot be fully extracted for that star level

## License

MIT
