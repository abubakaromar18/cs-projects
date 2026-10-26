"""Stage 1: loading raw data.

Reads any CSV with (at least) a location, a date and a daily count column.
`OWID_URL` points at Our World in Data's public COVID-19 export, which uses
the same column names this project expects, so it works out of the box with
`--download`. Downloading is opt-in; tests and the demo use the bundled
synthetic sample so they run offline.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

OWID_URL = "https://covid.ourworldindata.org/data/owid-covid-data.csv"

# Only these columns are read from the (very wide) OWID file. Reading a
# subset with `usecols` keeps memory low: the full export has ~67 columns.
WANTED_COLUMNS = [
    "iso_code", "continent", "location", "date",
    "new_cases", "new_deaths", "population",
]


def load_csv(source: str | Path, usecols: list[str] | None = None) -> pd.DataFrame:
    """Load a CSV from a path or URL.

    Columns are matched case-insensitively against `usecols` (default
    WANTED_COLUMNS); missing optional columns are simply absent from the
    result and handled later by `clean`. Everything is read as strings so
    that type coercion — and the bookkeeping of what failed to parse — lives
    in one place (the cleaning stage).
    """
    wanted = {c.lower() for c in (usecols or WANTED_COLUMNS)}
    return pd.read_csv(
        source,
        dtype=str,
        usecols=lambda name: name.strip().lower() in wanted,
        keep_default_na=True,
    )
