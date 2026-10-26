"""Stage 3: analysis.

All metrics are computed per location with `groupby(...).transform`, which
keeps the result aligned with the original rows (no merge back needed).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

PER = 100_000  # rates are expressed "per 100k people"


def add_metrics(df: pd.DataFrame, window: int = 7) -> pd.DataFrame:
    """Add cumulative totals, rolling averages and per-capita rates.

    A `window`-day trailing mean smooths out weekday reporting artefacts
    (many authorities do not report on weekends, then catch up on Monday).
    `min_periods=1` keeps the first few days instead of producing NaNs.
    """
    if window < 1:
        raise ValueError("window must be >= 1")
    out = df.sort_values(["location", "date"]).copy()
    g = out.groupby("location", sort=False)

    out["total_cases"] = g["new_cases"].cumsum()
    out["total_deaths"] = g["new_deaths"].cumsum()
    out["cases_avg"] = g["new_cases"].transform(lambda s: s.rolling(window, min_periods=1).mean())
    out["deaths_avg"] = g["new_deaths"].transform(lambda s: s.rolling(window, min_periods=1).mean())

    pop = out["population"].where(out["population"] > 0)  # avoid /0
    out["cases_avg_per_100k"] = out["cases_avg"] / pop * PER
    out["deaths_avg_per_100k"] = out["deaths_avg"] / pop * PER
    out["total_cases_per_100k"] = out["total_cases"] / pop * PER
    out["total_deaths_per_100k"] = out["total_deaths"] / pop * PER

    # Case fatality ratio so far (deaths / confirmed cases), NaN until a case exists.
    out["cfr_pct"] = (out["total_deaths"] / out["total_cases"].where(out["total_cases"] > 0)) * 100
    return out.reset_index(drop=True)


def weekly_growth(df: pd.DataFrame) -> pd.Series:
    """Week-over-week % change of the 7-day average on each location's last day.

    Positive => cases rising. NaN when last week's average was zero.
    """
    def last_change(g: pd.DataFrame) -> float:
        g = g.sort_values("date")
        if len(g) < 8:
            return np.nan
        now, before = g["cases_avg"].iloc[-1], g["cases_avg"].iloc[-8]
        return np.nan if before == 0 else (now - before) / before * 100

    return df.groupby("location").apply(last_change, include_groups=False).rename("wow_growth_pct")


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """One row per location: totals, rates, CFR, peak of the smoothed curve."""
    last = df.sort_values("date").groupby("location").tail(1).set_index("location")
    peak_idx = df.groupby("location")["cases_avg"].idxmax()
    peaks = df.loc[peak_idx].set_index("location")

    summary = pd.DataFrame({
        "population": last["population"],
        "total_cases": last["total_cases"],
        "total_deaths": last["total_deaths"],
        "cases_per_100k": last["total_cases_per_100k"],
        "deaths_per_100k": last["total_deaths_per_100k"],
        "cfr_pct": last["cfr_pct"],
        "peak_date": peaks["date"].dt.date,
        "peak_cases_avg": peaks["cases_avg"],
        "last_date": last["date"].dt.date,
    })
    summary = summary.join(weekly_growth(df))
    return summary.sort_values("cases_per_100k", ascending=False)


def top_n(summary: pd.DataFrame, metric: str, n: int = 5) -> pd.DataFrame:
    """Largest `n` locations by a summary column."""
    if metric not in summary.columns:
        raise KeyError(f"unknown metric {metric!r}; choose from {list(summary.columns)}")
    return summary.nlargest(n, metric)


def filter_frame(df: pd.DataFrame, locations=None, start=None, end=None) -> pd.DataFrame:
    """Restrict to some locations (case-insensitive) and/or a date range."""
    out = df
    if locations:
        wanted = {l.strip().lower() for l in locations}
        out = out[out["location"].str.lower().isin(wanted)]
    if start is not None:
        out = out[out["date"] >= pd.Timestamp(start)]
    if end is not None:
        out = out[out["date"] <= pd.Timestamp(end)]
    return out
