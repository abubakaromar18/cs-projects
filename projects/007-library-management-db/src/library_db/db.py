"""Connection handling and schema bootstrap.

SQLite is embedded: the "server" is just a file (or ``:memory:``). A few
settings matter for correctness and are applied on every connection:

* ``PRAGMA foreign_keys = ON`` -- SQLite ships with FK enforcement OFF for
  backwards compatibility, and the setting is per-connection.
* ``row_factory = sqlite3.Row`` -- rows can be read by column name.
* ``isolation_level = None`` -- autocommit mode; we manage transactions
  ourselves with :func:`transaction` so multi-statement operations are atomic.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from typing import Iterator

DEFAULT_DB_PATH = Path("library.db")


def load_schema_sql() -> str:
    """Return the DDL shipped inside the package."""
    return resources.files("library_db").joinpath("schema.sql").read_text("utf-8")


def connect(path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a connection with the settings this app relies on, creating the
    schema if it does not exist yet (all DDL uses IF NOT EXISTS)."""
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(load_schema_sql())
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection, immediate: bool = True) -> Iterator[sqlite3.Connection]:
    """Run a block atomically: COMMIT on success, ROLLBACK on any exception.

    ``BEGIN IMMEDIATE`` takes the write lock up front, so a check-then-write
    sequence (e.g. "is this copy free? then insert a loan") cannot interleave
    with another writer between the check and the write.
    """
    conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
