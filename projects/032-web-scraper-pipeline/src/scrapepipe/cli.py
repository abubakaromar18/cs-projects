"""Command-line interface.

    scrapepipe serve-demo [--port 8000]
    scrapepipe run URL [--db books.db] [--max-pages N] [--delay S]
    scrapepipe schedule URL --every 3600 [--runs N] [--jitter S]
    scrapepipe demo                      # serve + scrape + query, all in one
    scrapepipe query [--category C] [--max-price 20] [--min-rating 4] [--order rating]
    scrapepipe history SKU
    scrapepipe stats
    scrapepipe export out.csv|out.jsonl
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from .demo_site import DemoSite
from .fetcher import Fetcher, RateLimiter
from .pipeline import Pipeline
from .scheduler import Scheduler
from .storage import Store


def money(cents: int) -> str:
    return f"{cents / 100:,.2f}"


def print_books(rows, limit: int = 20) -> None:
    print(f"{'SKU':<6} {'Price':>9}  {'★':<5} {'Stock':<5} {'Category':<9} Title")
    for r in rows[:limit]:
        stock = "yes" if r["in_stock"] else "no"
        print(f"{r['sku']:<6} {money(r['price_cents']):>9}  {'★' * r['rating']:<5} "
              f"{stock:<5} {r['category']:<9} {r['title']}")
    if len(rows) > limit:
        print(f"... {len(rows) - limit} more")


def make_pipeline(args) -> Pipeline:
    fetcher = Fetcher(rate_limiter=RateLimiter(min_interval=args.delay))
    return Pipeline(Store(args.db), fetcher, max_pages=args.max_pages)


def cmd_run(args) -> int:
    result = make_pipeline(args).run(args.url)
    print(result.summary())
    for reason, n in result.reject_reasons.items():
        print(f"  rejected {n}: {reason}")
    return 1 if result.errors and result.pages == 0 else 0


def cmd_schedule(args) -> int:
    pipe = make_pipeline(args)
    sched = Scheduler(job=lambda: pipe.run(args.url).summary(),
                      interval=args.every, jitter=args.jitter)
    print(f"scheduling every {args.every}s (Ctrl-C to stop)")
    sched.run_forever(max_runs=args.runs, install_signals=True)
    print(f"stopped after {sched.runs} runs ({sched.failures} failures)")
    return 0


def cmd_serve(args) -> int:
    site = DemoSite(port=args.port).start()
    print(f"demo site at {site.start_url} (Ctrl-C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        site.stop()
    return 0


def cmd_demo(args) -> int:
    with DemoSite() as site:
        pipe = Pipeline(Store(":memory:"), Fetcher())  # fresh DB each demo
        print(f"scraping {site.start_url}")
        r = pipe.run(site.start_url)
        print(r.summary())
        for reason, n in r.reject_reasons.items():
            print(f"  rejected {n}: {reason}")
        print("\nre-run with unchanged site (idempotent):")
        print(pipe.run(site.start_url).summary())
        site.state["price_shift"] = -2
        print("\nre-run after prices dropped by £2:")
        print(pipe.run(site.start_url).summary())
        print("\nbest-rated books under £20:")
        print_books(pipe.store.books(max_price_cents=2000, min_rating=4, order="rating"), 8)
        print("\nprice history for B001:")
        for h in pipe.store.history("B001"):
            print(f"  {h['observed_at']}  {money(h['price_cents'])}")
    return 0


def cmd_query(args) -> int:
    store = Store(args.db)
    cap = int(round(args.max_price * 100)) if args.max_price is not None else None
    print_books(store.books(args.category, cap, args.min_rating, args.order), args.limit)
    return 0


def cmd_history(args) -> int:
    rows = Store(args.db).history(args.sku)
    if not rows:
        print(f"no history for {args.sku}")
        return 1
    for h in rows:
        print(f"{h['observed_at']}  {money(h['price_cents'])}")
    return 0


def cmd_stats(args) -> int:
    store = Store(args.db)
    print(f"{store.count()} books\n")
    print(f"{'Category':<10} {'N':>3} {'Avg £':>7} {'Avg ★':>6}")
    for r in store.category_summary():
        print(f"{r['category']:<10} {r['n']:>3} {r['avg_price']:>7.2f} {r['avg_rating']:>6.2f}")
    print("\nrecent runs:")
    for r in store.runs(5):
        print(f"  #{r['id']} {r['started_at']} pages={r['pages']} new={r['inserted']} "
              f"upd={r['updated']} same={r['unchanged']} rej={r['rejected']}"
              + (f" ERROR={r['error']}" if r["error"] else ""))
    return 0


def cmd_export(args) -> int:
    n = Store(args.db).export(args.path)
    print(f"wrote {n} rows to {args.path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="scrapepipe", description="Scrape, clean and store book listings.")
    p.add_argument("--db", default="books.db", help="SQLite database path")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    def crawl_opts(sp):
        sp.add_argument("url")
        sp.add_argument("--max-pages", type=int, default=50)
        sp.add_argument("--delay", type=float, default=1.0, help="min seconds between requests")

    sp = sub.add_parser("run", help="run the pipeline once"); crawl_opts(sp); sp.set_defaults(fn=cmd_run)
    sp = sub.add_parser("schedule", help="run the pipeline on an interval"); crawl_opts(sp)
    sp.add_argument("--every", type=float, default=3600.0)
    sp.add_argument("--jitter", type=float, default=0.0)
    sp.add_argument("--runs", type=int, default=None)
    sp.set_defaults(fn=cmd_schedule)
    sp = sub.add_parser("serve-demo", help="serve the demo bookstore on localhost")
    sp.add_argument("--port", type=int, default=8000); sp.set_defaults(fn=cmd_serve)
    sp = sub.add_parser("demo", help="end-to-end demo against the local site"); sp.set_defaults(fn=cmd_demo)
    sp = sub.add_parser("query", help="query stored books")
    sp.add_argument("--category"); sp.add_argument("--max-price", type=float)
    sp.add_argument("--min-rating", type=int, default=0)
    sp.add_argument("--order", choices=["price", "rating", "title"], default="price")
    sp.add_argument("--limit", type=int, default=20); sp.set_defaults(fn=cmd_query)
    sp = sub.add_parser("history", help="price history for a SKU")
    sp.add_argument("sku"); sp.set_defaults(fn=cmd_history)
    sp = sub.add_parser("stats", help="summary and recent runs"); sp.set_defaults(fn=cmd_stats)
    sp = sub.add_parser("export", help="export to .csv or .jsonl")
    sp.add_argument("path"); sp.set_defaults(fn=cmd_export)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(message)s")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
