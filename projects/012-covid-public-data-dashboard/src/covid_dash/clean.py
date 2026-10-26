"""Stage 2: cleaning.

Real open datasets are messy. This module turns a raw frame into a tidy,
gap-free daily panel (one row per location per day) and records every fix
it makes in a `CleaningReport`, so the cleaning is auditable rather than
silent.

Problems handled:
  * inconsistent column names ("New Cases ", "new_cases")
  * unparseable dates / numbers ("n/a", "", "1,234")
  * rows with no location or date
  * aggregate rows (OWID's "World", "Europe", ... have iso_code OWID_*)
  * duplicated (location, date) rows
  * negative daily counts (back-dated corrections published as negatives)
  * missing calendar days (reporting gaps)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

import pandas as pd

COUNT_COLUMNS = ["new_cases", "new_deaths"]
REQUIRED = ["location", "date", "new_cases"]


@dataclass
class CleaningReport:
    rows_in: int = 0
    rows_out: int = 0
    dropped_missing_keys: int = 0
    dropped_aggregates: int = 0
    dropped_duplicates: int = 0
    bad_numbers: int = 0
    negative_values_fixed: int = 0
    gap_days_filled: int = 0
    locations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:  # human-readable, used by the CLI
        d = self.as_dict()
        locs = d.pop("locations")
        lines = [f"  {k.replace('_', ' '):<24}{v:>8}" for k, v in d.items()]
        lines.append(f"  {'locations':<24}{len(locs):>8}")
        return "Cleaning report\n" + "\n".join(lines)


def normalize_column(name: str) -> str:
    """'  New Cases ' -> 'new_cases'."""
    return re.sub(r"[^0-9a-z]+", "_", name.strip().lower()).strip("_")


def _to_number(series: pd.Series) -> tuple[pd.Series, int]:
    """Coerce strings like '1,234' to floats; return (numbers, #unparseable).

    Blank/NaN cells are *missing*, not *bad*; only non-empty text that fails
    to parse counts toward the bad-number tally.
    """
    text = series.astype("string").str.replace(",", "", regex=False).str.strip()
    numbers = pd.to_numeric(text, errors="coerce")
    present = text.notna() & (text != "")
    return numbers.astype(float), int((present & numbers.isna()).sum())


def clean(raw: pd.DataFrame, keep_aggregates: bool = False) -> tuple[pd.DataFrame, CleaningReport]:
    """Return (tidy daily panel, report). Does not mutate `raw`."""
    report = CleaningReport(rows_in=len(raw))
    df = raw.rename(columns=normalize_column).copy()

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"input is missing required column(s): {', '.join(missing)}")
    for col in ["new_deaths", "population", "iso_code", "continent"]:
        if col not in df.columns:
            df[col] = pd.NA

    # --- keys: location + date ------------------------------------------
    df["location"] = df["location"].astype("string").str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    keys_ok = df["location"].notna() & (df["location"] != "") & df["date"].notna()
    report.dropped_missing_keys = int((~keys_ok).sum())
    df = df[keys_ok]

    # --- aggregates (continents, income groups, World) --------------------
    if not keep_aggregates:
        is_agg = df["iso_code"].astype("string").str.startswith("OWID_").fillna(False)
        report.dropped_aggregates = int(is_agg.sum())
        df = df[~is_agg]

    # --- numeric coercion -------------------------------------------------
    for col in COUNT_COLUMNS + ["population"]:
        df[col], bad = _to_number(df[col])
        report.bad_numbers += bad

    # --- duplicates: keep the last-reported row for each (location, date) --
    before = len(df)
    df = df.drop_duplicates(subset=["location", "date"], keep="last")
    report.dropped_duplicates = before - len(df)

    # --- negative corrections ---------------------------------------------
    # A negative daily count means "we over-reported earlier". We cannot
    # know which earlier days were wrong, so the defensible fix is to treat
    # the day as zero new events (cumulative totals become a slight
    # over-estimate rather than going backwards).
    for col in COUNT_COLUMNS:
        neg = df[col] < 0
        report.negative_values_fixed += int(neg.sum())
        df.loc[neg, col] = 0.0

    # --- fill calendar gaps per location ----------------------------------
    pieces = []
    for loc, g in df.sort_values("date").groupby("location", sort=True):
        full = pd.date_range(g["date"].min(), g["date"].max(), freq="D")
        g = g.set_index("date").reindex(full)
        report.gap_days_filled += int(g["location"].isna().sum())
        g["location"] = loc
        # Static attributes are carried across gaps in both directions.
        for col in ["iso_code", "continent", "population"]:
            g[col] = g[col].ffill().bfill()
        g[COUNT_COLUMNS] = g[COUNT_COLUMNS].fillna(0.0)
        pieces.append(g.rename_axis("date").reset_index())

    cols = ["location", "iso_code", "continent", "date", "new_cases", "new_deaths", "population"]
    out = (pd.concat(pieces, ignore_index=True)[cols] if pieces
           else pd.DataFrame(columns=cols))
    report.rows_out = len(out)
    report.locations = sorted(out["location"].unique().tolist())
    return out, report
