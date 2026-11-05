"""Load stage: idempotent storage in SQLite with change history.

Schema
------
* ``books``         – current state, one row per SKU (upserted).
* ``price_history`` – an append-only row each time a SKU's price changes,
                      a tiny slowly-changing-dimension (SCD type 2-ish) log.
* ``runs``          – one row per pipeline run, for observability.

Re-running the pipeline on unchanged data writes no new history rows, so
the load is *idempotent*.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone
from typing import Iterable

from .cleaner import Book

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    sku          TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    url          TEXT,
    price_cents  INTEGER NOT NULL,
    currency     TEXT NOT NULL,
    rating       INTEGER NOT NULL CHECK (rating BETWEEN 0 AND 5),
    in_stock     INTEGER NOT NULL,
    stock_count  INTEGER,
    category     TEXT NOT NULL,
    first_seen   TEXT NOT NULL,
    last_seen    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS price_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sku          TEXT NOT NULL REFERENCES books(sku),
    price_cents  INTEGER NOT NULL,
    observed_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hist_sku ON price_history(sku);
CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    pages        INTEGER DEFAULT 0,
    inserted     INTEGER DEFAULT 0,
    updated      INTEGER DEFAULT 0,
    unchanged    INTEGER DEFAULT 0,
    rejected     INTEGER DEFAULT 0,
    error        TEXT
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # -- runs ----------------------------------------------------------------
    def start_run(self) -> int:
        cur = self.conn.execute("INSERT INTO runs(started_at) VALUES (?)", (utcnow(),))
        self.conn.commit()
        return cur.lastrowid

    def finish_run(self, run_id: int, **stats) -> None:
        cols = ["finished_at"] + list(stats)
        sets = ", ".join(f"{c} = ?" for c in cols)
        self.conn.execute(
            f"UPDATE runs SET {sets} WHERE id = ?", [utcnow(), *stats.values(), run_id]
        )
        self.conn.commit()

    def runs(self, limit: int = 10) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    # -- books ---------------------------------------------------------------
    def upsert(self, books: Iterable[Book], now: str | None = None) -> dict[str, int]:
        """Insert new SKUs, update changed ones, record price changes.

        All writes happen in a single transaction: a crash mid-load leaves the
        database exactly as it was.
        """
        now = now or utcnow()
        stats = {"inserted": 0, "updated": 0, "unchanged": 0}
        fields = ("title", "url", "price_cents", "currency", "rating",
                  "in_stock", "stock_count", "category")
        with self.conn:  # transaction
            for b in books:
                row = self.conn.execute(
                    "SELECT * FROM books WHERE sku = ?", (b.sku,)
                ).fetchone()
                values = (b.title, b.url, b.price_cents, b.currency, b.rating,
                          int(b.in_stock), b.stock_count, b.category)
                if row is None:
                    self.conn.execute(
                        "INSERT INTO books(sku, title, url, price_cents, currency, rating,"
                        " in_stock, stock_count, category, first_seen, last_seen)"
                        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (b.sku, *values, now, now),
                    )
                    self._record_price(b.sku, b.price_cents, now)
                    stats["inserted"] += 1
                    continue
                changed = tuple(row[f] for f in fields) != values
                self.conn.execute(
                    "UPDATE books SET title=?, url=?, price_cents=?, currency=?, rating=?,"
                    " in_stock=?, stock_count=?, category=?, last_seen=? WHERE sku=?",
                    (*values, now, b.sku),
                )
                if row["price_cents"] != b.price_cents:
                    self._record_price(b.sku, b.price_cents, now)
                stats["updated" if changed else "unchanged"] += 1
        return stats

    def _record_price(self, sku: str, cents: int, now: str) -> None:
        self.conn.execute(
            "INSERT INTO price_history(sku, price_cents, observed_at) VALUES (?,?,?)",
            (sku, cents, now),
        )

    # -- queries -------------------------------------------------------------
    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]

    def books(self, category: str | None = None, max_price_cents: int | None = None,
              min_rating: int = 0, order: str = "price") -> list[sqlite3.Row]:
        order_by = {"price": "price_cents", "rating": "rating DESC, price_cents",
                    "title": "title"}.get(order, "price_cents")
        sql, args = "SELECT * FROM books WHERE rating >= ?", [min_rating]
        if category:
            sql += " AND category = ? COLLATE NOCASE"
            args.append(category)
        if max_price_cents is not None:
            sql += " AND price_cents <= ?"
            args.append(max_price_cents)
        return self.conn.execute(f"{sql} ORDER BY {order_by}", args).fetchall()

    def history(self, sku: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT price_cents, observed_at FROM price_history WHERE sku = ? ORDER BY id",
            (sku.upper(),),
        ).fetchall()

    def category_summary(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT category, COUNT(*) AS n, ROUND(AVG(price_cents)/100.0, 2) AS avg_price,"
            " ROUND(AVG(rating), 2) AS avg_rating FROM books GROUP BY category ORDER BY n DESC"
        ).fetchall()

    # -- export --------------------------------------------------------------
    def export(self, path: str) -> int:
        rows = [dict(r) for r in self.books(order="title")]
        if path.endswith(".csv"):
            with open(path, "w", newline="", encoding="utf-8") as f:
                if rows:
                    w = csv.DictWriter(f, fieldnames=list(rows[0]))
                    w.writeheader()
                    w.writerows(rows)
        else:  # JSON Lines
            with open(path, "w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
        return len(rows)
