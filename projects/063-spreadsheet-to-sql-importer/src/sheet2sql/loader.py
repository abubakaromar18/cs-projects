"""Load a Table into SQLite using an inferred Schema.

The import is a two-pass algorithm:

1. **Profile** – stream the rows once, inferring a type per column.
2. **Load**    – stream again, converting each cell and inserting in
   batches with ``executemany`` inside a single transaction.

A single transaction means an import is atomic: either every row lands or
(on error) none do, and the table is never left half-written.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from itertools import islice
from typing import Any, Iterator

from .infer import SqlType, convert, profile_columns
from .readers import Table
from .schema import Schema, build_schema, quote

IF_EXISTS = ("fail", "replace", "append")


class ImportFailure(Exception):
    pass


@dataclass
class ImportResult:
    table: str
    rows: int
    schema: Schema
    coerced: int = 0  # cells kept as raw text because they didn't fit
    warnings: list[str] = field(default_factory=list)


def infer_schema(table: Table, sample: int | None = None, detect_pk: bool = True) -> Schema:
    profiles = profile_columns(table.header, table.rows(), sample)
    return build_schema(table.name, profiles, detect_pk)


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _converted_rows(
    table: Table, schema: Schema, strict: bool, result: ImportResult
) -> Iterator[tuple[Any, ...]]:
    width = len(schema.columns)
    for line, row in enumerate(table.rows(), start=2):  # line 1 is the header
        if len(row) > width and any(str(c).strip() for c in row[width:] if c is not None):
            result.warnings.append(f"row {line}: {len(row) - width} extra cell(s) ignored")
        out = []
        for col, raw in zip(schema.columns, list(row) + [None] * (width - len(row))):
            try:
                out.append(convert(raw, col.type))
            except (ValueError, AssertionError):
                # Only reachable when inference used a sample that missed
                # this value. SQLite's flexible typing lets us keep it.
                if strict:
                    raise ImportFailure(
                        f"row {line}, column {col.name!r}: {raw!r} is not {col.type.value}"
                    ) from None
                result.coerced += 1
                out.append(str(raw))
        yield tuple(out)


def load_table(
    conn: sqlite3.Connection,
    table: Table,
    *,
    table_name: str | None = None,
    if_exists: str = "fail",
    sample: int | None = None,
    batch_size: int = 1000,
    strict: bool = False,
    detect_pk: bool = True,
) -> ImportResult:
    """Infer a schema for ``table`` and insert all its rows into ``conn``."""
    if if_exists not in IF_EXISTS:
        raise ValueError(f"if_exists must be one of {IF_EXISTS}")

    schema = infer_schema(table, sample, detect_pk)
    if table_name:
        schema.table = table_name
    result = ImportResult(schema.table, 0, schema)

    exists = _table_exists(conn, schema.table)
    if exists and if_exists == "fail":
        raise ImportFailure(f"table {schema.table!r} already exists (use --if-exists)")

    try:
        # Python's sqlite3 only opens transactions implicitly before DML, so
        # DDL (CREATE/DROP) would autocommit. An explicit BEGIN makes the
        # whole import -- schema change included -- one atomic unit.
        if not conn.in_transaction:
            conn.execute("BEGIN")
        with conn:  # commit on success, rollback on any exception
            if exists and if_exists == "replace":
                conn.execute(f"DROP TABLE {quote(schema.table)}")
            if not exists or if_exists == "replace":
                conn.execute(schema.create_sql())
            sql = schema.insert_sql()
            rows = _converted_rows(table, schema, strict, result)
            while batch := list(islice(rows, batch_size)):
                conn.executemany(sql, batch)
                result.rows += len(batch)
    except sqlite3.IntegrityError as e:
        raise ImportFailure(f"constraint violated while loading: {e}") from None
    return result


def describe(result: ImportResult) -> str:
    lines = [f"{result.table}: {result.rows} row(s)"]
    for c in result.schema.columns:
        flags = []
        if c.name == result.schema.primary_key:
            flags.append("PK")
        if not c.nullable:
            flags.append("NOT NULL")
        if c.unique:
            flags.append("unique")
        src = f"  (from {c.source!r})" if c.source != c.name else ""
        lines.append(f"  {c.name:<20} {c.type.value:<9} {' '.join(flags)}{src}")
    if result.coerced:
        lines.append(f"  ! {result.coerced} cell(s) did not match the inferred type; stored as text")
    return "\n".join(lines)


__all__ = ["ImportFailure", "ImportResult", "infer_schema", "load_table", "describe", "SqlType"]
