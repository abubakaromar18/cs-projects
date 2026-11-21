import datetime as dt
import sqlite3
from pathlib import Path

import pytest

from sheet2sql.cli import main
from sheet2sql.infer import SqlType as T
from sheet2sql.loader import ImportFailure, load_table
from sheet2sql.readers import ReaderError, read_any, read_csv, read_xlsx
from sheet2sql.schema import build_schema, quote, to_identifier, unique_identifiers
from sheet2sql.infer import ColumnProfile

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "employees.csv"


# --- schema -----------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Employee ID", "employee_id"),
        ("firstName", "first_name"),
        ("Remote?", "remote"),
        ("2024 Sales ($)", "c_2024_sales"),
        ("Café Naïve", "cafe_naive"),
        ("order", "order_"),
        ("!!!", "column_1"),
    ],
)
def test_to_identifier(raw, expected):
    assert to_identifier(raw, "column_1") == expected


def test_unique_identifiers_dedupes_and_fills_blanks():
    assert unique_identifiers(["Name", "name", "NAME", "", ""]) == [
        "name", "name_2", "name_3", "column_4", "column_5",
    ]


def test_quote_escapes_embedded_quotes():
    assert quote('a"b') == '"a""b"'


def test_primary_key_detection():
    def prof(name, t, unique=True, nulls=0):
        p = ColumnProfile(name, t, non_null=3, nulls=nulls)
        p.unique = unique
        return p

    s = build_schema("t", [prof("ID", T.INTEGER), prof("x", T.TEXT)])
    assert s.primary_key == "id"
    s = build_schema("t", [prof("ID", T.INTEGER, unique=False)])
    assert s.primary_key is None
    s = build_schema("t", [prof("ID", T.INTEGER, nulls=1)])
    assert s.primary_key is None
    s = build_schema("t", [prof("ID", T.INTEGER)], detect_pk=False)
    assert s.primary_key is None
    assert "PRIMARY KEY" in build_schema("t", [prof("ID", T.INTEGER)]).create_sql()


# --- CSV end to end ---------------------------------------------------------


def test_example_csv_round_trip():
    conn = sqlite3.connect(":memory:")
    (table,) = read_any(EXAMPLE)
    res = load_table(conn, table)
    assert res.rows == 5 and res.table == "employees"

    cols = {r[1]: r[2] for r in conn.execute("PRAGMA table_info(employees)")}
    assert cols == {
        "employee_id": "INTEGER", "full_name": "TEXT", "department": "TEXT",
        "start_date": "TEXT", "salary": "REAL", "remote": "INTEGER",
        "last_login": "TEXT", "zip_code": "TEXT",
    }
    row = conn.execute(
        "SELECT salary, remote, zip_code, last_login FROM employees WHERE employee_id = 1"
    ).fetchone()
    assert row == (125000.0, 1, "02134", "2026-11-01 09:15:00")
    # Nulls are real NULLs, and SQL date functions work on stored dates.
    assert conn.execute("SELECT COUNT(*) FROM employees WHERE last_login IS NULL").fetchone() == (1,)
    assert conn.execute("SELECT COUNT(*) FROM employees WHERE zip_code IS NULL").fetchone() == (1,)
    assert conn.execute(
        "SELECT full_name FROM employees WHERE start_date < date('2019-01-01') ORDER BY start_date"
    ).fetchall() == [("Barbara Liskov",), ("Alan Turing",)]
    assert conn.execute("SELECT SUM(remote) FROM employees").fetchone() == (3,)


def test_semicolon_csv_is_sniffed(tmp_path):
    f = tmp_path / "eu.csv"
    f.write_text("name;price\nwidget;3.5\ngadget;4\n", encoding="utf-8")
    t = read_csv(f)
    assert t.header == ["name", "price"]
    conn = sqlite3.connect(":memory:")
    load_table(conn, t)
    assert conn.execute("SELECT SUM(price) FROM eu").fetchone() == (7.5,)


def test_bom_and_blank_lines(tmp_path):
    f = tmp_path / "bom.csv"
    f.write_bytes("﻿a,b\n1,2\n\n,\n3,4\n".encode("utf-8"))
    t = read_csv(f)
    assert t.header == ["a", "b"]
    assert list(t.rows()) == [["1", "2"], ["3", "4"]]


def test_if_exists_modes(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text("x\n1\n2\n")
    conn = sqlite3.connect(":memory:")
    (t,) = read_any(f)
    load_table(conn, t)
    with pytest.raises(ImportFailure):
        load_table(conn, t)
    load_table(conn, t, if_exists="append")
    assert conn.execute("SELECT COUNT(*) FROM t").fetchone() == (4,)
    load_table(conn, t, if_exists="replace")
    assert conn.execute("SELECT COUNT(*) FROM t").fetchone() == (2,)


def test_sampling_coerces_or_fails_strictly(tmp_path):
    f = tmp_path / "s.csv"
    f.write_text("n\n1\n2\nthree\n")
    (t,) = read_any(f)
    conn = sqlite3.connect(":memory:")
    res = load_table(conn, t, sample=2)
    assert res.coerced == 1
    assert conn.execute("SELECT n FROM s ORDER BY rowid").fetchall() == [(1,), (2,), ("three",)]

    conn2 = sqlite3.connect(":memory:")
    with pytest.raises(ImportFailure, match="row 4"):
        load_table(conn2, t, sample=2, strict=True)
    # Atomic: the failed import left no table behind.
    assert conn2.execute("SELECT name FROM sqlite_master").fetchall() == []


def test_duplicate_pk_in_append_is_reported_and_rolled_back(tmp_path):
    f = tmp_path / "p.csv"
    f.write_text("id,v\n1,a\n2,b\n")
    (t,) = read_any(f)
    conn = sqlite3.connect(":memory:")
    load_table(conn, t)
    with pytest.raises(ImportFailure, match="constraint"):
        load_table(conn, t, if_exists="append")
    assert conn.execute("SELECT COUNT(*) FROM p").fetchone() == (2,)


def test_short_and_long_rows(tmp_path):
    f = tmp_path / "r.csv"
    f.write_text("a,b\n1\n2,3,extra\n")
    (t,) = read_any(f)
    conn = sqlite3.connect(":memory:")
    res = load_table(conn, t)
    assert conn.execute("SELECT a, b FROM r ORDER BY a").fetchall() == [(1, None), (2, 3)]
    assert any("extra" in w for w in res.warnings)


def test_hostile_headers_are_safe(tmp_path):
    f = tmp_path / "evil.csv"
    f.write_text('"x""); DROP TABLE t; --",select\n1,2\n')
    (t,) = read_any(f)
    conn = sqlite3.connect(":memory:")
    res = load_table(conn, t)
    names = [c.name for c in res.schema.columns]
    assert names == ["x_drop_table_t", "select_"]
    assert conn.execute("SELECT * FROM evil").fetchall() == [(1, 2)]


def test_reader_errors(tmp_path):
    with pytest.raises(ReaderError):
        read_any(tmp_path / "missing.csv")
    (tmp_path / "e.csv").write_text("")
    with pytest.raises(ReaderError):
        read_any(tmp_path / "e.csv")
    (tmp_path / "x.json").write_text("{}")
    with pytest.raises(ReaderError):
        read_any(tmp_path / "x.json")


# --- XLSX -------------------------------------------------------------------

openpyxl = pytest.importorskip("openpyxl")


@pytest.fixture
def workbook(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Orders"
    ws.append(["Order ID", "Placed", "Amount", "Paid", "Note"])
    ws.append([100, dt.datetime(2026, 1, 5), 19.99, True, None])
    ws.append([101, dt.datetime(2026, 1, 6, 14, 30), 5, False, "rush"])
    ws.append([None, None, None, None, None])  # blank row is skipped
    ws.append([102, dt.date(2026, 1, 7), 42.0, True, "gift"])
    ws2 = wb.create_sheet("Customers")
    ws2.append(["name", "vip"])
    ws2.append(["Ada", "yes"])
    wb.create_sheet("Empty")
    path = tmp_path / "shop.xlsx"
    wb.save(path)
    return path


def test_xlsx_reads_all_sheets_with_native_types(workbook):
    tables = read_xlsx(workbook)
    assert [t.name for t in tables] == ["Orders", "Customers"]
    conn = sqlite3.connect(":memory:")
    res = load_table(conn, tables[0])
    types = {c.name: c.type for c in res.schema.columns}
    assert types == {
        "order_id": T.INTEGER, "placed": T.DATETIME, "amount": T.REAL,
        "paid": T.BOOLEAN, "note": T.TEXT,
    }
    assert res.schema.primary_key == "order_id"
    assert conn.execute("SELECT * FROM orders ORDER BY order_id").fetchall() == [
        (100, "2026-01-05 00:00:00", 19.99, 1, None),
        (101, "2026-01-06 14:30:00", 5.0, 0, "rush"),
        (102, "2026-01-07 00:00:00", 42.0, 1, "gift"),
    ]


def test_xlsx_single_sheet_and_bad_sheet(workbook):
    assert [t.name for t in read_any(workbook, sheet="Customers")] == ["Customers"]
    with pytest.raises(ReaderError, match="available"):
        read_xlsx(workbook, sheet="Nope")


# --- CLI --------------------------------------------------------------------


def test_cli_load_and_dry_run(tmp_path, capsys, workbook):
    db = tmp_path / "out.db"
    assert main([str(EXAMPLE), str(workbook), "--db", str(db)]) == 0
    out = capsys.readouterr().out
    assert "employees: 5 row(s)" in out and "orders: 3 row(s)" in out
    conn = sqlite3.connect(db)
    assert {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")} == {
        "employees", "orders", "customers",
    }
    conn.close()

    assert main([str(EXAMPLE), "--db", str(db)]) == 1  # exists -> fail
    assert "already exists" in capsys.readouterr().err

    assert main([str(EXAMPLE), "--dry-run", "-t", "staff"]) == 0
    assert 'CREATE TABLE "staff"' in capsys.readouterr().out


def test_cli_errors(tmp_path, capsys, workbook):
    assert main([str(tmp_path / "nope.csv")]) == 2
    assert main([str(workbook), "-t", "x"]) == 2  # two sheets, one table name
    assert "exactly one" in capsys.readouterr().err
