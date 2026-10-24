from datetime import date

import pytest

from library_db import Library, connect
from library_db.cli import format_table, main
from library_db.seed import BOOKS, is_empty, seed


@pytest.fixture
def dbfile(tmp_path):
    return str(tmp_path / "lib.db")


def cli(dbfile, *args, today="2026-03-01"):
    return main(["--db", dbfile, "--today", today, *args])


def test_full_workflow(dbfile, capsys):
    assert cli(dbfile, "add-book", "978-0-13-235088-4", "Clean Code", "-a", "Robert C. Martin",
               "-y", "2008", "-g", "Software Engineering") == 0
    assert cli(dbfile, "add-copy", "9780132350884", "B-1") == 0
    assert cli(dbfile, "add-member", "Ada", "ada@example.org") == 0
    assert cli(dbfile, "checkout", "B-1", "ada@example.org") == 0
    assert "due 2026-03-15" in capsys.readouterr().out
    assert cli(dbfile, "return", "B-1", today="2026-03-20") == 0
    assert "5 day(s) late, fine $1.25" in capsys.readouterr().out
    assert cli(dbfile, "search", "martin") == 0
    assert "Clean Code" in capsys.readouterr().out


def test_errors_exit_1(dbfile, capsys):
    assert cli(dbfile, "add-copy", "9780132350884", "B-1") == 1
    assert "no book" in capsys.readouterr().err
    assert cli(dbfile, "add-book", "123", "Bad", "-a", "X") == 1
    assert "invalid ISBN" in capsys.readouterr().err


def test_seed_and_reports(dbfile, capsys):
    assert cli(dbfile, "seed") == 0
    assert "books=7" in capsys.readouterr().out
    assert cli(dbfile, "seed") == 0
    assert "already has books" in capsys.readouterr().out
    for cmd in (["catalog"], ["overdue"], ["popular"], ["authors"], ["stats"],
                ["history", "ada@example.org"]):
        assert cli(dbfile, *cmd) == 0
    assert "Introduction to Algorithms" in capsys.readouterr().out


def test_sql_is_read_only(dbfile, capsys):
    cli(dbfile, "seed")
    capsys.readouterr()
    assert cli(dbfile, "sql", "SELECT count(*) AS n FROM members") == 0
    assert "4" in capsys.readouterr().out
    assert cli(dbfile, "sql", "DELETE FROM members") == 1
    assert "readonly" in capsys.readouterr().err
    conn = connect(dbfile)
    assert conn.execute("SELECT count(*) FROM members").fetchone()[0] == 4
    conn.close()


def test_seed_overdue_relative_to_today():
    lib = Library(connect(":memory:"))
    assert is_empty(lib)
    seed(lib, today=date(2026, 6, 1))
    assert len(BOOKS) == lib.stats()["books"]
    assert {r["email"] for r in lib.overdue(today="2026-06-01")} == {"ada@example.org", "alan@example.org"}


def test_format_table():
    out = format_table([{"a": 1, "bb": None}, {"a": 22, "bb": "x"}])
    assert out.splitlines() == ["a   bb", "--  --", "1", "22  x"]
    assert format_table([]) == "(no rows)"
