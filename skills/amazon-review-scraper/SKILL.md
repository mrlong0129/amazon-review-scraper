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

**You MUST produce two markdown file deliverables** (written to disk, not inline chat output).

---

#### Deliverable 1: Full Review Data

**Filename**: `{ASIN}_reviews-data_{YYYY-MM-DD}.md`

**Template**:

```markdown
# {ASIN} Review Data

> Scraped: {YYYY-MM-DD HH:MM} | Mode: {mode} | Coverage: {estimate}

## Overview

| Metric | Value |
|--------|-------|
| Total Reviews | X |
| Star Distribution | 5★: X / 4★: X / 3★: X / 2★: X / 1★: X |
| Verified Purchase | X (X%) |
| Vine Review | X |
| With Images | X |
| With Video | X |
| Date Range | YYYY-MM-DD ~ YYYY-MM-DD |
| Raw JSON | `/tmp/{ASIN}_reviews.json` |

[If date/star filters applied, note filter criteria and filtered count]

## Monthly Distribution

| Month | Count | Avg Rating |
|-------|-------|------------|
| 2026-02 | X | X.X |
| ... | ... | ... |

## 1★ Reviews (X)

### "Review Title"
- **Date**: Month DD, YYYY | **VP**: Yes/No | **Helpful**: X | **Media**: (photo)/(video)
- Full review text here...

### "Review Title 2"
...

## 2★ Reviews (X)
[same format]

## 3★ Reviews (X)
[same format]

## 4★ Reviews (X)
[same format]

## 5★ Reviews (X)
[same format]
```

**Rules**:
- Group by star rating (1★ → 5★), within each group sort by date descending (newest first)
- Include full review text — never truncate
- Mark reviews with images as (photo), with video as (video)

---

#### Deliverable 2: Review Summary & Analysis

**Filename**: `{ASIN}_reviews-summary_{YYYY-MM-DD}.md`

**Template**:

```markdown
# {ASIN} Review Summary

> Based on X written reviews | {YYYY-MM-DD}

## Basic Stats

[same overview table as Deliverable 1]

## Positive Themes (4-5★, X reviews)

| Rank | Theme | Frequency | Representative Quotes |
|------|-------|-----------|----------------------|
| 1 | {clustered theme} | ~X% of positive reviews | "quote 1" / "quote 2" |
| 2 | ... | ... | ... |

## Negative Themes (1-2★, X reviews)

| Theme | Frequency | % of Negative | Severity | Representative Quotes |
|-------|-----------|---------------|----------|-----------------------|
| {clustered pain point} | X times | X% | High/Medium/Low | "quote" |
| ... | ... | ... | ... | ... |

## 3★ Review Signals (X reviews)

[3-star reviews are high-information — extract key pain points and mixed feedback]

## Time Trends

### Review Volume
| Period | Monthly Avg | Characteristics |
|--------|-------------|-----------------|
| YYYY-MM ~ YYYY-MM | X/month | description |

### Rating Trend
| Period | Avg Rating | 5★ % | Notes |
|--------|------------|-------|-------|
| YYYY H1 | X.X | X% | ... |

## Key Findings / Anomalies

### 1. {Finding Title} — Severity: High/Medium/Low
[Description with evidence]

### 2. {Finding Title} — Severity: High/Medium/Low
[Description with evidence]

## Actionable Recommendations

| Priority | Recommendation | Evidence |
|----------|---------------|----------|
| P0 | {specific action} | {based on which finding} |
| P1 | ... | ... |
```

**Rules**:
- Positive/Negative themes must be **semantically clustered** from review content, not simple keyword counting
- Pick 1-2 most representative quotes per theme
- Actionable recommendations must be specific, not generic
- 3★ reviews get their own section — they contain the highest information density

---

#### Delivery Flow

1. Generate Deliverable 1 (data document) — pure data organization, no analysis needed
2. Generate Deliverable 2 (summary) based on Deliverable 1 — requires semantic analysis
3. Report to user: two file paths + brief summary (3-5 sentences highlighting key findings)

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
