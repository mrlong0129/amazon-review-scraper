---
name: amazon-review-scraper
description: Dual-source Amazon review collection (Woot scraper + Sorftime MCP), with automatic dedup merge, multi-site support, and variant attributes.
version: v1.3
---

# Amazon Review Scraper (Dual-Source)

Dual-source Amazon review collection: Woot scraper (US, rich metadata) + Sorftime MCP (14 marketplaces, variant attributes), with automatic dedup merge.

## How It Works

### Source 1: Woot Scraper (US only)

`woot.com/review/Reviews/{ASIN}` is a public AJAX endpoint that returns Amazon review data as JSON (text, ratings, images, videos). Each `(star_filter, sort_order)` combination returns up to 100 reviews. By iterating across 5 star ratings x 4 sort orders and deduplicating, we maximize extraction — typically 85-100% of all written reviews.

### Source 2: Sorftime MCP `product_reviews` (14 marketplaces)

Sorftime MCP provides up to 100 recent reviews (within ~1 year) with **variant attributes** (Color, Size, etc.) across 14 Amazon marketplaces.

### Dedup Merge

When both sources are used (US marketplace), reviews are deduplicated:
- Match key: `normalize(title) + normalize(text[:100])`
- Duplicates: keep Woot version (richer metadata) + merge Sorftime's variant attribute
- Source tag: `woot` / `sorftime` / `merged` (deduplicated)

### Multi-Site Routing

| Marketplace | Data Sources | Dedup |
|-------------|-------------|-------|
| US | Woot + Sorftime (dual-source) | Yes, via dedup script |
| GB/DE/FR/JP/CA/IN/ES/IT/MX/AE/AU/BR/SA | Sorftime MCP only | Not needed |

### Data Source Comparison

| Dimension | Woot Scraper | Sorftime MCP |
|-----------|-------------|-------------|
| Marketplaces | US only | 14 marketplaces |
| Review cap | Theoretically unlimited (max mode) | 100 per ASIN / ~1 year |
| Variant attributes | No | Yes |
| Author | Yes | No |
| Verified Purchase / Vine | Yes | No |
| Helpful Votes | Yes | No |
| Images / Video | Yes | No |
| Review filter | star × sort combinations | Positive / Negative / Both |

## When to Use

| User Says | Action |
|-----------|--------|
| "Get all reviews for B0xxx" | Confirm marketplace → run max mode |
| "Recent 3 months reviews" | Max mode + date filter |
| "Show me the bad reviews" | Max mode + filter 1-2 star |
| "Quick look at reviews" | Basic mode (fast, 100 cap) |
| "Get reviews for these 5 ASINs" | Loop max mode per ASIN |
| "Analyze review pain points" | Scrape + generate summary report |
| "Get reviews from UK site" | Sorftime MCP only (non-US) |

## Scrape Modes (Woot)

| Mode | Max Reviews | Speed | Best For |
|------|-------------|-------|----------|
| `basic` | 100 | Fast | Quick preview |
| `full` | 500 | Medium | Most products |
| `max` | ~500-700 | Slower | Maximum extraction (default) |

## Execution Steps

### Step 1: Parse User Intent + Confirm Marketplace

Extract from request:
- **ASIN** (required): 10-character string starting with B0
- **Marketplace** (required): Must be confirmed before proceeding
- **Mode**: "quick" → basic / default → max
- **Date filter** (optional): "recent N months" → compute cutoff date
- **Star filter** (optional): "bad reviews" → 1-2 star / "good reviews" → 4-5 star

**Marketplace Confirmation** (mandatory):
- User specified marketplace → use it directly
- User did NOT specify → **ask which marketplace** (US/GB/DE/FR/JP/CA etc.)
- US → dual-source collection (Woot + Sorftime → dedup merge)
- Non-US → Sorftime MCP only (`product_reviews` with `amzSite` parameter)

### Step 2: Choose Scrape Mode

| Condition | Recommended Mode | Reason |
|-----------|-----------------|--------|
| Quick preview / few reviews | `basic` | Fast, 100 cap |
| Need full coverage / <500 reviews | `full` | Split by star, near-complete |
| Many reviews / want maximum | `max` | star × sort maximization (default) |
| Only specific stars (e.g. bad reviews) | `basic` + filter | Single star usually <100 |

### Step 3: Execute Collection

#### 3a: Woot Scraper (US marketplace)

```bash
# Max mode (default, maximum extraction)
python3 ${SKILL_DIR}/scripts/amazon_review_scraper.py {ASIN} --mode max -o /tmp/{ASIN}_woot.json

# Basic mode (quick, 100 cap)
python3 ${SKILL_DIR}/scripts/amazon_review_scraper.py {ASIN} --mode basic -o /tmp/{ASIN}_woot.json

# Summary only
python3 ${SKILL_DIR}/scripts/amazon_review_scraper.py {ASIN} --summary
```

#### 3b: Sorftime MCP (all marketplaces)

```
Sorftime MCP: product_reviews(amzSite="{SITE}", asin="{ASIN}", reviewType="Both")
```

Parameters:
- `amzSite`: US/GB/DE/FR/IN/CA/JP/ES/IT/MX/AE/AU/BR/SA
- `reviewType`: Both (all) / Positive (4-5★) / Negative (1-3★)
- Returns: up to 100 recent reviews (~1 year), with variant attributes

Save Sorftime results as JSON: `/tmp/{ASIN}_sorftime.json`

#### 3c: Dedup Merge (dual-source, US only)

```bash
# Dual-source merge
python3 ${SKILL_DIR}/scripts/review_dedup_merge.py \
  --woot /tmp/{ASIN}_woot.json \
  --sorftime /tmp/{ASIN}_sorftime.json \
  -o /tmp/{ASIN}_merged.json

# Woot only (normalize format)
python3 ${SKILL_DIR}/scripts/review_dedup_merge.py --woot /tmp/{ASIN}_woot.json -o /tmp/{ASIN}_merged.json

# Sorftime only (normalize format, non-US)
python3 ${SKILL_DIR}/scripts/review_dedup_merge.py --sorftime /tmp/{ASIN}_sorftime.json -o /tmp/{ASIN}_merged.json
```

**Dedup strategy**:
- Match key: `normalize(title) + normalize(text[:100])`
- Duplicates: keep Woot version (Author/VP/Vine/Helpful/Media), merge Sorftime's variant attribute
- Source tag: `woot` / `sorftime` / `merged` (deduplicated)

### Step 4: Post-Processing (if needed)

#### Date Filtering

Review dates are in `OriginDescription`. Use the built-in `parse_review_date()` function (supports multiple formats). Do not write your own date parser.

```python
import json, re
from datetime import datetime, timedelta

with open("/tmp/{ASIN}_reviews.json") as f:
    data = json.load(f)

reviews = data["reviews"]
cutoff = datetime.now() - timedelta(days=90)  # last 3 months

def parse_date(desc):
    """Multi-format date parser. Returns None if unparseable (never return partial dates)."""
    if not desc:
        return None
    # Format 1: "on Month DD, YYYY"
    m = re.search(r"on (\w+ \d{1,2},?\s+\d{4})", desc)
    if m:
        date_str = re.sub(r"\s+", " ", m.group(1).replace(",", "").strip())
        try:
            return datetime.strptime(date_str, "%B %d %Y")
        except ValueError:
            pass
    # Format 2: "on DD. Month YYYY" (European)
    m = re.search(r"on (\d{1,2})\.\s*(\w+)\s+(\d{4})", desc)
    if m:
        try:
            return datetime.strptime(f"{m.group(2)} {m.group(1)} {m.group(3)}", "%B %d %Y")
        except ValueError:
            pass
    # Format 3: "Month DD YYYY" anywhere
    m = re.search(r"([A-Z][a-z]+)\s+(\d{1,2}),?\s+(\d{4})", desc)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y")
        except ValueError:
            pass
    return None  # Do NOT return (year, 0) — causes YYYY-00 bug

filtered = [r for r in reviews if (d := parse_date(r.get("OriginDescription", ""))) and d >= cutoff]
```

#### Star Filtering

```python
bad_reviews = [r for r in reviews if r.get("OverallRating", 0) <= 2]
good_reviews = [r for r in reviews if r.get("OverallRating", 0) >= 4]
```

### Step 5: Generate Report

**You MUST produce two markdown file deliverables** (written to disk, not inline chat output).

**Privacy rules (mandatory)**:
- **Do NOT mention data source names** in reports (no "Woot", "Sorftime", "scraper" etc.)
- **Do NOT include a "Data Source" row** in overview tables
- Reports should present review data only, without exposing collection methods

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

[If date/star filters applied, note filter criteria and filtered count]

## Monthly Distribution

> Use `summary.monthly_distribution` from JSON output (pre-computed by script).
> Only display months with successfully parsed dates. Never show "YYYY-00" format.

| Month | Count | Avg Rating |
|-------|-------|------------|
| 2026-02 | X | X.X |
| ... | ... | ... |

## 1★ Reviews (X)

### "Review Title"
- **Date**: Month DD, YYYY | **VP**: Yes/No | **Helpful**: X | **Media**: (photo)/(video)
- Full review text here...

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

## Negative Themes (1-2★, X reviews)

| Theme | Frequency | % of Negative | Severity | Representative Quotes |
|-------|-----------|---------------|----------|-----------------------|
| {clustered pain point} | X times | X% | High/Medium/Low | "quote" |

## 3★ Review Signals (X reviews)

[3-star reviews are high-information — extract key pain points and mixed feedback]

## Time Trends

- Review volume changes (which months have more/fewer reviews)
- Whether negative reviews cluster in specific periods
- Rating trend (improving/deteriorating)

## Key Findings / Anomalies

- [Finding 1: e.g. Vine review ratio unusually high]
- [Finding 2: e.g. negative reviews spiked in specific month]

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

---

#### Delivery Flow

1. Generate Deliverable 1 (data document) — pure data organization, no analysis needed
2. Generate Deliverable 2 (summary) based on Deliverable 1 — requires semantic analysis
3. Report to user: two file paths + brief summary (3-5 sentences highlighting key findings)

## API Response Fields (Woot)

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

## Coverage (Woot)

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
| Forgetting to dedup dual-source | Always use `review_dedup_merge.py` when combining Woot + Sorftime |
| Merging without dedup | Duplicate reviews will appear twice without the dedup script |
| Woot Title HTML entities | Woot returns `&amp;` etc. — dedup script handles `html.unescape` |
| Date parsing failures | `OriginDescription` format may vary; implement fallback |
| Rate limiting on bulk ASINs | Add 1-2 second delay between ASINs |
| Non-US marketplaces with Woot | Woot only supports US — use Sorftime MCP for other sites |

## Limitations

- Woot: Amazon US only. Sorftime: 14 marketplaces (100 reviews/~1 year cap)
- Written reviews only, not star-only ratings
- 100 reviews per `(filter, sort)` combination (Woot API hard limit)
- Products with >135 five-star written reviews cannot be fully extracted for that star level
- Sorftime has no Author/VP/Vine/Helpful/Media metadata
- Python 3.6+ required (no external dependencies)

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.3 | 2026-03-04 | Bug fix: monthly distribution "YYYY-00" date parsing (script pre-computes) + privacy rules (reports don't expose data source) |
| v1.2 | 2026-03-04 | Dual-source: added Sorftime MCP + dedup merge script + multi-site routing + variant attributes + marketplace confirmation |
| v1.1 | 2026-03-03 | Added two-document delivery spec (full data + summary analysis) |
| v1.0 | 2026-03-03 | Initial: basic/full/max modes, date/star filtering, coverage notes |

---

*Dependencies: Python 3, `scripts/amazon_review_scraper.py`, `scripts/review_dedup_merge.py`, Sorftime MCP*
*Woot limits: US only, written reviews only, 5★ cap ~135 | Sorftime limits: 100 reviews/~1 year, 14 marketplaces*
