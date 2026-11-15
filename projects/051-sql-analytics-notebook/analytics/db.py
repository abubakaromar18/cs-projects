"""Build an SQLite database from the bundled CSVs and run the analysis queries.

Only the standard library is needed for loading and querying; pandas is used
optionally to get DataFrames for the notebook.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SQL_DIR = ROOT / "sql"
QUERY_DIR = SQL_DIR / "queries"

# Column name -> converter applied to each CSV value. "NA" in the source becomes NULL.
_PENGUIN_COLUMNS: dict[str, type] = {
    "species": str,
    "island": str,
    "bill_length_mm": float,
    "bill_depth_mm": float,
    "flipper_length_mm": int,
    "body_mass_g": int,
    "sex": str,
    "year": int,
}

_MISSING = {"", "NA", "NaN"}


def _convert(value: str, kind: type) -> Any:
    """Convert one CSV cell, mapping missing markers to None (SQL NULL)."""
    if value.strip() in _MISSING:
        return None
    return kind(value)


def _read_penguins(path: Path) -> Iterable[tuple]:
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            yield tuple(_convert(row[col], kind) for col, kind in _PENGUIN_COLUMNS.items())


def build_database(path: str | Path = ":memory:") -> sqlite3.Connection:
    """Create the schema and load both CSVs. Returns an open connection.

    Use the default ``":memory:"`` for a throwaway database, or pass a file path
    to persist it (e.g. for the ``sqlite3`` CLI).
    """
    if path != ":memory:":
        Path(path).unlink(missing_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((SQL_DIR / "schema.sql").read_text())

    with (DATA_DIR / "species.csv").open(newline="") as f:
        rows = [(r["species"], r["scientific_name"], r["genus"]) for r in csv.DictReader(f)]
    conn.executemany("INSERT INTO species VALUES (?, ?, ?)", rows)

    cols = ", ".join(_PENGUIN_COLUMNS)
    placeholders = ", ".join("?" * len(_PENGUIN_COLUMNS))
    conn.executemany(
        f"INSERT INTO penguins ({cols}) VALUES ({placeholders})",
        _read_penguins(DATA_DIR / "penguins.csv"),
    )
    conn.commit()
    return conn


def list_queries() -> list[str]:
    """Names (file stems) of all analysis queries, in numeric order."""
    return sorted(p.stem for p in QUERY_DIR.glob("*.sql"))


def load_query(name: str) -> str:
    """Return the SQL text for a query by stem (``"04_heaviest_per_species"``) or number (``"04"``)."""
    matches = [p for p in QUERY_DIR.glob("*.sql") if p.stem == name or p.stem.startswith(f"{name}_")]
    if len(matches) != 1:
        raise KeyError(f"no unique query matching {name!r}; available: {list_queries()}")
    return matches[0].read_text()


def run_query(conn: sqlite3.Connection, name: str, as_frame: bool = False):
    """Run a named query file.

    Returns ``(columns, rows)`` by default, or a pandas DataFrame if ``as_frame``.
    """
    sql = load_query(name)
    if as_frame:
        import pandas as pd  # imported lazily so the core works without pandas

        return pd.read_sql_query(sql, conn)
    cur = conn.execute(sql)
    columns = [d[0] for d in cur.description]
    return columns, cur.fetchall()
