# Amazon Review Scraper

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that scrapes Amazon product reviews via woot.com's public AJAX API.

**No API key. No login. No browser automation. Pure Python 3 stdlib.**

## Install

```bash
claude install github:mrlong0129/amazon-review-scraper
```

## Usage

Once installed, just ask Claude naturally:

```
"Get all reviews for B0BLCBRBVZ"
"Scrape the bad reviews for B0DPHLWNBG"
"Analyze the reviews for this ASIN: B0BN7M8CH4"
"Get recent 3 months reviews for B0xxx"
```

Claude will automatically:
1. Scrape reviews using the optimal mode
2. Apply any filters (date, star rating)
3. Generate a full review data document and a summary analysis

## How It Works

`woot.com/review/Reviews/{ASIN}` is a public AJAX endpoint that returns Amazon review data as JSON. By iterating across 5 star ratings x 4 sort orders and deduplicating, the scraper extracts 85-100% of all written reviews.

## Modes

| Mode | Max Reviews | Speed | Best For |
|------|-------------|-------|----------|
| `basic` | 100 | Fast | Quick preview |
| `full` | 500 | Medium | Most products |
| `max` | ~500-700 | Slower | Maximum extraction (default) |

## Coverage

| Product Size | Expected Coverage |
|-------------|-------------------|
| < 100 written reviews | **100%** |
| 100 - 500 | **~95-100%** |
| 500 - 1000 | **~85-95%** |
| > 1000 | **~70-85%** |

> **Note**: Amazon "ratings" include star-only ratings (no text). This tool retrieves **written reviews** only — typically 10-15% of total ratings.

## Standalone Usage

You can also use the scraper script directly without Claude Code:

```bash
python3 skills/amazon-review-scraper/scripts/amazon_review_scraper.py B0BLCBRBVZ
python3 skills/amazon-review-scraper/scripts/amazon_review_scraper.py B0BLCBRBVZ -o reviews.json
python3 skills/amazon-review-scraper/scripts/amazon_review_scraper.py B0BLCBRBVZ --mode basic
python3 skills/amazon-review-scraper/scripts/amazon_review_scraper.py B0BLCBRBVZ --summary
```

## Requirements

- Python 3.6+
- No external dependencies (uses only stdlib: `urllib`, `json`, `argparse`)

## Limitations

- Amazon US (`amazon.com`) only
- Written reviews only, not star-only ratings
- 100 reviews per `(filter, sort)` combination (API hard limit)

## License

MIT
