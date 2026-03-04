---
name: amazon-review-scraper
description: Scrape Amazon product reviews (written reviews) via woot.com's public AJAX API. Use when users ask to collect, analyze, or export Amazon product reviews for any ASIN.
---

# Amazon Review Scraper

Scrape Amazon product reviews via woot.com's public AJAX endpoint. No API key, no login, no browser automation. Pure Python 3 stdlib.

## How It Works

`woot.com/review/Reviews/{ASIN}` is a public AJAX endpoint that returns Amazon review data as JSON (text, ratings, images, videos). Each `(star_filter, sort_order)` combination returns up to 100 reviews. By iterating across 5 star ratings x 4 sort orders and deduplicating, we maximize extraction — typically 85-100% of all written reviews.

## When to Use

| User Says | Action |
|-----------|--------|
| "Get all reviews for B0xxx" | Run max mode |
| "Recent 3 months reviews" | Max mode + date filter |
| "Show me the bad reviews" | Max mode + filter 1-2 star |
| "Quick look at reviews" | Basic mode (fast, 100 cap) |
| "Get reviews for these 5 ASINs" | Loop max mode per ASIN |
| "Analyze review pain points" | Scrape + generate summary report |

## Scrape Modes

| Mode | Max Reviews | Speed | Best For |
|------|-------------|-------|----------|
| `basic` | 100 | Fast | Quick preview |
| `full` | 500 | Medium | Most products |
| `max` | ~500-700 | Slower | Maximum extraction (default) |

## Execution Steps

### Step 1: Parse User Intent

Extract from request:
- **ASIN** (required): 10-character string starting with B0
- **Mode**: "quick" → basic / default → max
- **Date filter** (optional): "recent N months" → compute cutoff date
- **Star filter** (optional): "bad reviews" → 1-2 star / "good reviews" → 4-5 star

### Step 2: Run Scraper

```bash
# Max mode (default, maximum extraction)
python3 ${SKILL_DIR}/scripts/amazon_review_scraper.py {ASIN} --mode max -o /tmp/{ASIN}_reviews.json

# Basic mode (quick, 100 cap)
python3 ${SKILL_DIR}/scripts/amazon_review_scraper.py {ASIN} --mode basic -o /tmp/{ASIN}_reviews.json

# Summary only
python3 ${SKILL_DIR}/scripts/amazon_review_scraper.py {ASIN} --summary
```

### Step 3: Post-Processing (if needed)

#### Date Filtering

Review dates are in `OriginDescription`: `"Reviewed in the United States on February 21, 2026"`

```python
import json, re
from datetime import datetime, timedelta

with open("/tmp/{ASIN}_reviews.json") as f:
    data = json.load(f)

reviews = data["reviews"]
cutoff = datetime.now() - timedelta(days=90)  # last 3 months

def parse_date(desc):
    m = re.search(r"on (\w+ \d+, \d{4})", desc)
    if m:
        return datetime.strptime(m.group(1), "%B %d, %Y")
    return None

filtered = [r for r in reviews if (d := parse_date(r.get("OriginDescription", ""))) and d >= cutoff]
```

#### Star Filtering

```python
bad_reviews = [r for r in reviews if r.get("OverallRating", 0) <= 2]
good_reviews = [r for r in reviews if r.get("OverallRating", 0) >= 4]
```

### Step 4: Generate Report

Produce two markdown documents:

#### Document 1: Full Review Data

All reviews organized by star rating (1 star to 5 star), each with:
- Date, Verified Purchase status, Helpful votes, Media indicators
- Full review text (never truncate)

Include summary table: total count, star distribution, verified %, vine %, image/video counts, date range.

#### Document 2: Review Summary & Analysis

- **Positive themes** (4-5 star): Semantic clustering of praise points with frequency and representative quotes
- **Negative themes** (1-2 star): Pain points with frequency, severity, and representative quotes
- **Time trends**: Review volume changes, rating trend shifts
- **Anomalies**: Unusual patterns (review spikes, rating shifts, vine concentration)
- **Actionable insights**: Prioritized recommendations based on findings

## API Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `Author` | string | Reviewer name |
| `Title` | string | Review title |
| `Text` | string | Full review text |
| `OverallRating` | int | Star rating (1-5) |
| `OriginDescription` | string | Review date and region |
| `IsVerifiedPurchase` | bool | Verified Purchase flag |
| `IsVineReview` | bool | Vine review flag |
| `HelpfulVotes` | int | Helpful vote count |
| `ImageUrls` | array | Review image URLs |
| `MediaUrls` | array | Review video URLs (src + poster) |

## Coverage

| Product Size | Expected Coverage |
|-------------|-------------------|
| < 100 written reviews | **100%** |
| 100 - 500 | **~95-100%** |
| 500 - 1000 | **~85-95%** |
| > 1000 | **~70-85%** |

### Important: Ratings vs Reviews

Amazon shows "X ratings" which includes **star-only ratings** (no text). This tool only retrieves **written reviews** — typically 10-15% of total ratings. A product with "2,000 ratings" may have ~200-300 written reviews. Always clarify this distinction to the user.

## Common Pitfalls

| Pitfall | How to Avoid |
|---------|-------------|
| Confusing ratings count with reviews count | Clarify: ratings include star-only, written reviews are a subset |
| Expecting 100% extraction | 5-star reviews cap at ~135 per ASIN |
| Duplicate reviews across runs | Max mode has built-in dedup; don't merge multiple runs |
| Date parsing failures | `OriginDescription` format may vary; implement fallback |
| Rate limiting on bulk ASINs | Add 1-2 second delay between ASINs |
| Non-US marketplaces | Only Amazon US supported (woot.com = amazon.com) |

## Limitations

- Amazon US (`amazon.com`) only
- Written reviews only, not star-only ratings
- 100 reviews per `(filter, sort)` combination (API hard limit)
- Products with >135 five-star written reviews cannot be fully extracted for that star level
- Python 3.6+ required (no external dependencies)
