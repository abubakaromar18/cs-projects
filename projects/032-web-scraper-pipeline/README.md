# 032 · Web Scraper Pipeline

A small but complete **ETL pipeline** for web scraping, written in pure Python
(standard library only). It **fetches** paginated listing pages politely,
**parses** them into records, **cleans** and validates the data, **stores** it
idempotently in SQLite with price-change history, and can **run on a schedule**.

It ships with a demo bookstore that runs on `127.0.0.1`, so everything works
offline and nothing is scraped from third-party sites.

```
$ scrapepipe demo
scraping http://127.0.0.1:43903/catalogue/page-1.html
run #1: 5 pages, 44 new, 0 updated, 0 unchanged, 2 rejected
  rejected 1: unparseable price
  rejected 1: duplicate sku

re-run with unchanged site (idempotent):
run #2: 5 pages, 0 new, 0 updated, 44 unchanged, 2 rejected

re-run after prices dropped by £2:
run #3: 5 pages, 0 new, 44 updated, 0 unchanged, 2 rejected

best-rated books under £20:
SKU        Price  ★     Stock Category  Title
B005        8.67  ★★★★★ no    Travel    The Ember Lantern
B034       14.70  ★★★★★ yes   Mystery   The Shadow Cipher Winter Compass
B037       12.48  ★★★★  no    Fantasy   The Tide Silent
B026       14.00  ★★★★  no    Science   The Atlas Winter Tide Meridian

price history for B001:
  2026-11-05T14:46:09+00:00  25.11
  2026-11-05T14:46:09+00:00  23.11
```

## Architecture

```
            ┌──────────┐   HTML   ┌──────────┐  RawRecord  ┌──────────┐   Book   ┌──────────┐
 start URL ─▶  fetcher  ├─────────▶  parser   ├────────────▶  cleaner  ├─────────▶ storage  │ SQLite
            └────▲─────┘          └────┬─────┘             └────┬─────┘          └──────────┘
                 │      next-page URL  │              rejects   │ (reported per run)
                 └─────────────────────┘                        ▼
                     pipeline.py (crawl loop)              RunResult
                            ▲
                    scheduler.py (every N seconds)
```

| Module | Stage | What it does |
|---|---|---|
| `fetcher.py` | Extract | `urllib` GETs with per-host rate limiting, retries with exponential backoff on 429/5xx, no retry on 4xx, robots.txt checks |
| `parser.py` | Extract | Event-driven `HTMLParser` state machine that pulls fields out of `<article class="product">` and finds the `next` link |
| `cleaner.py` | Transform | Pure validators: prices to integer cents, ratings to 0–5, stock parsing, Unicode/whitespace normalisation, de-duplication, reject reasons |
| `storage.py` | Load | SQLite schema with constraints, transactional upsert, price-history log, run log, queries, CSV/JSONL export |
| `pipeline.py` | Orchestrate | Pagination crawl with a visited set, page cap and same-host restriction; keeps partial results when a fetch fails |
| `scheduler.py` | Schedule | Fixed-rate interval scheduler with drift correction, skipped missed slots, jitter, backoff and graceful SIGINT/SIGTERM |
| `demo_site.py` | — | Local `ThreadingHTTPServer` bookstore with deliberately dirty data, a `robots.txt`, a redirect, and failure injection |

## CS concepts

- **ETL / data pipelines**: separate extract, transform and load stages with typed hand-offs (`RawRecord` → `Book`).
- **Parsing with a state machine**: SAX-style tokenizer events and nesting-depth tracking instead of fragile regexes over HTML.
- **Graph traversal**: pagination is BFS over "next" edges, with a visited set so cyclic links still terminate.
- **Idempotency and change data capture**: re-running on unchanged data writes nothing new; only real price changes add history rows.
- **ACID transactions**: a batch upsert is all-or-nothing (there's a test for the rollback).
- **Fixed-point money**: integer cents, never floats.
- **Rate limiting, retries and exponential backoff**: being polite to servers and resilient to transient failures.
- **Scheduling**: fixed-rate vs fixed-delay timing, clock drift, and jitter to avoid the thundering herd.
- **Testability through dependency injection**: clock, sleep, RNG and opener are all injectable, so time-based tests run instantly.

## Build, run, test

Requires Python 3.10+. No runtime dependencies.

```bash
make test                  # 44 tests; spins up the demo site on 127.0.0.1
make demo                  # end-to-end demo (in-memory DB)

# or install the CLI
make dev                   # pip install -e '.[dev]'
scrapepipe serve-demo --port 8000 &          # terminal 1
scrapepipe run http://127.0.0.1:8000/ --delay 0.5
scrapepipe query --category poetry --max-price 30 --order rating
scrapepipe history B001
scrapepipe stats
scrapepipe export books.csv          # or books.jsonl
scrapepipe schedule http://127.0.0.1:8000/ --every 3600 --jitter 60
```

`--db PATH` (before the sub-command) selects the SQLite file; it defaults to `books.db`.

Sample `stats` output:

```
44 books

Category     N   Avg £  Avg ★
History     10   38.34   2.50
Fantasy     10   32.52   2.50
Mystery      7   30.91   3.29
Science      6  228.90   4.00
Poetry       6   36.30   3.50
Travel       5   45.95   2.60

recent runs:
  #1 2026-11-05T14:46:58+00:00 pages=5 new=44 upd=0 same=0 rej=2
```

### Scheduling in production

The built-in scheduler suits a long-running process. For a one-shot job,
cron works too:

```cron
0 * * * *  cd /path/to/project && scrapepipe --db books.db run http://127.0.0.1:8000/ >> scrape.log 2>&1
```

## Responsible use

Only point this at sites you own or that explicitly allow scraping. It honours
`robots.txt` by default, rate-limits each host (1 request/second by default),
identifies itself with a descriptive User-Agent, and stays on the start URL's
host.

## Possible extensions

- Follow each book's detail page to collect descriptions (a two-level crawl with a work queue).
- Support CSS selectors through a config file so new sites need no code changes.
- Use `asyncio` with a bounded concurrency semaphore for faster crawls.
- Use conditional requests (`ETag` / `If-Modified-Since`) to skip unchanged pages.
- Add alerts when a tracked SKU drops below a target price.
- Add schema migrations and a Parquet export for analytics.
- Add a cron-expression parser to the scheduler.
