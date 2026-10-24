"""The database itself must reject bad data, independent of the Python layer."""

import sqlite3

import pytest

from library_db.db import transaction


def test_all_tables_and_views_exist(conn):
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    assert {"authors", "publishers", "genres", "books", "book_authors", "book_genres",
            "copies", "members", "loans", "v_book_catalog", "v_open_loans"} <= names


def test_foreign_keys_enforced(conn):
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO copies(book_id, barcode) VALUES (999, 'X')")


def test_one_open_loan_per_copy_at_db_level(stocked):
    conn = stocked.conn
    copy_id = conn.execute("SELECT copy_id FROM copies WHERE barcode='A-1'").fetchone()[0]
    insert = "INSERT INTO loans(copy_id, member_id, loaned_on, due_on, returned_on) VALUES (?, ?, ?, ?, ?)"
    conn.execute(insert, (copy_id, 1, "2026-01-01", "2026-01-15", "2026-01-10"))  # closed loan
    conn.execute(insert, (copy_id, 1, "2026-02-01", "2026-02-15", None))  # open loan: ok
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(insert, (copy_id, 2, "2026-02-02", "2026-02-16", None))  # second open loan


@pytest.mark.parametrize("sql", [
    "INSERT INTO books(isbn, title) VALUES ('123', 'Short ISBN')",
    "INSERT INTO books(isbn, title) VALUES ('9780000000002', '   ')",
    "INSERT INTO members(name, email) VALUES ('No At', 'nobody')",
    "INSERT INTO books(isbn, title, published_year) VALUES ('9780000000002', 'T', 3000)",
])
def test_check_constraints(conn, sql):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(sql)


def test_due_before_loan_rejected(stocked):
    with pytest.raises(sqlite3.IntegrityError):
        stocked.conn.execute(
            "INSERT INTO loans(copy_id, member_id, loaned_on, due_on) VALUES (1, 1, '2026-02-10', '2026-02-01')")


def test_cannot_delete_book_with_copies(stocked):
    with pytest.raises(sqlite3.IntegrityError):
        stocked.conn.execute("DELETE FROM books WHERE isbn = '9780262033848'")


def test_deleting_book_cascades_to_junctions(lib):
    bid = lib.add_book("9780132350884", "Clean Code", ["Robert C. Martin"], genres=["SE"])
    lib.conn.execute("DELETE FROM books WHERE book_id = ?", (bid,))
    assert lib.conn.execute("SELECT count(*) FROM book_authors").fetchone()[0] == 0
    assert lib.conn.execute("SELECT count(*) FROM book_genres").fetchone()[0] == 0
    # the author row itself survives: it's an independent entity
    assert lib.conn.execute("SELECT count(*) FROM authors").fetchone()[0] == 1


def test_transaction_rolls_back(conn):
    with pytest.raises(RuntimeError):
        with transaction(conn):
            conn.execute("INSERT INTO authors(name) VALUES ('Temp')")
            raise RuntimeError
    assert conn.execute("SELECT count(*) FROM authors").fetchone()[0] == 0


def test_schema_is_idempotent(tmp_path):
    from library_db import connect
    path = tmp_path / "x.db"
    connect(path).close()
    connect(path).close()  # IF NOT EXISTS everywhere: second run is a no-op
