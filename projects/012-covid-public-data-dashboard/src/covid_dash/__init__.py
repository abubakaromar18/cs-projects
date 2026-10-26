"""covid_dash — a small Pandas + Plotly pipeline for public-health time series.

The pipeline has four stages, each in its own module:

    load      -> read a CSV (local file or the Our World in Data export)
    clean     -> normalise schema, fix types, drop aggregates/duplicates,
                 repair negative "corrections", fill calendar gaps
    analyze   -> rolling averages, per-capita rates, growth, summaries
    dashboard -> an interactive, self-contained Plotly HTML report
"""

from .load import load_csv, OWID_URL
from .clean import clean, CleaningReport
from .analyze import add_metrics, summarize, top_n, weekly_growth
from .dashboard import build_dashboard

__all__ = [
    "load_csv", "OWID_URL", "clean", "CleaningReport", "add_metrics",
    "summarize", "top_n", "weekly_growth", "build_dashboard",
]
__version__ = "1.0.0"
