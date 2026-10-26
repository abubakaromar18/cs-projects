"""Command-line entry point: load -> clean -> analyze -> dashboard."""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from .analyze import add_metrics, filter_frame, summarize, top_n
from .clean import clean
from .dashboard import build_dashboard, write_html
from .load import OWID_URL, load_csv


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="covid-dash",
        description="Clean, analyze and visualize COVID-19 style public time-series data.")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", "-i", help="path or URL of a CSV file")
    src.add_argument("--download", action="store_true",
                     help=f"fetch the Our World in Data export ({OWID_URL})")
    p.add_argument("--countries", "-c", help="comma-separated locations to include")
    p.add_argument("--start", help="first date to show (YYYY-MM-DD)")
    p.add_argument("--end", help="last date to show (YYYY-MM-DD)")
    p.add_argument("--window", type=int, default=7, help="rolling-average window in days (default 7)")
    p.add_argument("--top", type=int, metavar="N",
                   help="when no --countries given, keep only the N locations with most cases per 100k")
    p.add_argument("--out", "-o", default="dashboard.html", help="output HTML file (default dashboard.html)")
    p.add_argument("--offline", action="store_true", help="embed plotly.js in the HTML")
    p.add_argument("--summary", action="store_true", help="print the per-location summary table")
    p.add_argument("--export-clean", metavar="CSV", help="also write the cleaned+enriched data to CSV")
    p.add_argument("--no-html", action="store_true", help="skip writing the dashboard")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    source = OWID_URL if args.download else args.input
    try:
        raw = load_csv(source)
        tidy, report = clean(raw)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(report, file=sys.stderr)

    # Metrics are computed on the full history *before* date filtering so
    # rolling averages and cumulative totals at --start are correct.
    data = add_metrics(tidy, window=args.window)
    locations = [c for c in args.countries.split(",") if c.strip()] if args.countries else None
    data = filter_frame(data, locations=locations, start=args.start, end=args.end)
    if data.empty:
        print("error: no rows left after filtering", file=sys.stderr)
        return 1

    summary = summarize(data)
    if args.top and not locations:
        summary = top_n(summary, "cases_per_100k", args.top)
        data = data[data["location"].isin(summary.index)]

    if args.summary:
        with pd.option_context("display.width", 140, "display.max_columns", 20,
                               "display.float_format", "{:,.2f}".format):
            print(summary.drop(columns=["population"]).to_string())
    if args.export_clean:
        data.to_csv(args.export_clean, index=False)
        print(f"wrote {args.export_clean}", file=sys.stderr)
    if not args.no_html:
        path = write_html(build_dashboard(data, summary), args.out, offline=args.offline)
        print(f"wrote {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
