"""The CSV → SQLite load must be faithful: right row count, NULLs, constraints."""

import sqlite3

import pytest

from analytics import build_database


def test_row_counts(conn):
    assert conn.execute("SELECT COUNT(*) FROM penguins").fetchone()[0] == 344
    assert conn.execute("SELECT COUNT(*) FROM species").fetchone()[0] == 3


def test_na_becomes_null(conn):
    # Rows 4 and 272 in the source have no measurements at all.
    null_rows = conn.execute(
        "SELECT id FROM penguins WHERE body_mass_g IS NULL ORDER BY id"
    ).fetchall()
    assert [r[0] for r in null_rows] == [4, 272]
    assert conn.execute("SELECT COUNT(*) FROM penguins WHERE sex = 'NA'").fetchone()[0] == 0


def test_types_are_numeric(conn):
    t = conn.execute(
        "SELECT typeof(bill_length_mm), typeof(body_mass_g) FROM penguins WHERE id = 1"
    ).fetchone()
    assert t == ("real", "integer")


def test_foreign_key_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO penguins (species, island, year) VALUES ('Emperor', 'Dream', 2008)")


def test_check_constraint_on_year(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO penguins (species, island, year) VALUES ('Adelie', 'Dream', 1999)")


def test_build_to_file(tmp_path):
    db = tmp_path / "p.sqlite"
    build_database(db).close()
    again = sqlite3.connect(db)
    assert again.execute("SELECT COUNT(*) FROM penguins").fetchone()[0] == 344
    # Rebuilding over an existing file must not duplicate rows.
    build_database(db).close()
    assert again.execute("SELECT COUNT(*) FROM penguins").fetchone()[0] == 344
