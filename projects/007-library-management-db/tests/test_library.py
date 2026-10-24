import pytest

from library_db import Conflict, LibraryError, NotFound
from library_db.isbn import InvalidISBN
from library_db.library import FINE_CAP_CENTS, MAX_LOANS, fine_cents


# ---------------------------------------------------------------- catalog / normalization

def test_shared_author_and_publisher_stored_once(lib):
    lib.add_book("9780262033848", "Book One", ["Jane Doe"], "MIT Press")
    lib.add_book("9780132350884", "Book Two", ["Jane Doe", "John Roe"], "MIT Press")
    assert lib.conn.execute("SELECT count(*) FROM authors").fetchone()[0] == 2
    assert lib.conn.execute("SELECT count(*) FROM publishers").fetchone()[0] == 1
    assert lib.conn.execute("SELECT count(*) FROM book_authors").fetchone()[0] == 3


def test_authors_keep_cover_order(lib):
    lib.add_book("9780262033848", "T", ["Zed", "Amy", "Zed"])
    assert lib.catalog()[0]["authors"] == "Zed, Amy"


def test_isbn10_duplicate_of_isbn13_detected(lib):
    lib.add_book("9780262510875", "SICP", ["Abelson"])
    with pytest.raises(Conflict):
        lib.add_book("0-262-51087-1", "SICP again", ["Abelson"])


def test_invalid_isbn_rejected(lib):
    with pytest.raises(InvalidISBN):
        lib.add_book("9780262033849", "Typo", ["X"])
    assert lib.stats()["books"] == 0


def test_book_needs_author(lib):
    with pytest.raises(LibraryError):
        lib.add_book("9780262033848", "Anon", ["  "])


def test_failed_add_book_leaves_no_partial_rows(lib):
    lib.add_book("9780262033848", "First", ["A"])
    with pytest.raises(Conflict):
        lib.add_book("9780262033848", "Dup", ["Brand New Author"], "New Pub")
    names = {r[0] for r in lib.conn.execute("SELECT name FROM authors")}
    assert names == {"A"}
    assert lib.conn.execute("SELECT count(*) FROM publishers").fetchone()[0] == 0


def test_duplicate_barcode(stocked):
    with pytest.raises(Conflict):
        stocked.add_copy("9780132350884", "A-1")


def test_copy_for_unknown_book(lib):
    with pytest.raises(NotFound):
        lib.add_copy("9780262033848", "Z-1")


def test_duplicate_member_email_case_insensitive(stocked):
    with pytest.raises(Conflict):
        stocked.add_member("Ada Again", "ADA@example.org")


def test_search_by_title_author_genre_isbn(stocked):
    assert [b["title"] for b in stocked.search("clean")] == ["Clean Code"]
    assert [b["title"] for b in stocked.search("leiserson")] == ["Introduction to Algorithms"]
    assert [b["title"] for b in stocked.search("software eng")] == ["Clean Code"]
    assert [b["title"] for b in stocked.search("978-0-13-235088-4")] == ["Clean Code"]


def test_search_one_row_per_book_and_escapes_wildcards(stocked):
    assert len(stocked.search("o")) == 2       # matches several authors but no duplicates
    assert stocked.search("%") == []           # literal %, not "match everything"
    assert stocked.search("_") == []


# ---------------------------------------------------------------- circulation

def test_checkout_and_availability(stocked):
    loan = stocked.checkout("A-1", "ada@example.org", today="2026-03-01")
    assert loan["due_on"] == "2026-03-15"
    algo = next(b for b in stocked.catalog() if b["title"].startswith("Intro"))
    assert (algo["available_copies"], algo["total_copies"]) == (1, 2)


def test_double_checkout_rejected(stocked):
    stocked.checkout("A-1", "ada@example.org", today="2026-03-01")
    with pytest.raises(Conflict, match="already on loan"):
        stocked.checkout("A-1", "alan@example.org", today="2026-03-02")


def test_unknown_copy_or_member(stocked):
    with pytest.raises(NotFound):
        stocked.checkout("NOPE", "ada@example.org")
    with pytest.raises(NotFound):
        stocked.checkout("A-1", "ghost@example.org")


def test_loan_limit(lib):
    lib.add_book("9780262033848", "Many", ["A"])
    for i in range(MAX_LOANS + 1):
        lib.add_copy("9780262033848", f"M-{i}")
    lib.add_member("Ada", "ada@example.org")
    for i in range(MAX_LOANS):
        lib.checkout(f"M-{i}", "ada@example.org", today="2026-03-01")
    with pytest.raises(Conflict, match="maximum"):
        lib.checkout(f"M-{MAX_LOANS}", "ada@example.org", today="2026-03-01")


def test_overdue_member_blocked(stocked):
    stocked.checkout("A-1", "ada@example.org", today="2026-01-01")
    with pytest.raises(Conflict, match="overdue"):
        stocked.checkout("B-1", "ada@example.org", today="2026-02-01")


def test_return_on_time_and_late(stocked):
    stocked.checkout("A-1", "ada@example.org", today="2026-03-01")
    assert stocked.return_copy("A-1", today="2026-03-10")["fine_cents"] == 0
    stocked.checkout("A-1", "ada@example.org", today="2026-03-11")      # due 03-25
    r = stocked.return_copy("A-1", today="2026-03-29")
    assert (r["days_late"], r["fine_cents"]) == (4, 100)


def test_return_not_on_loan(stocked):
    with pytest.raises(Conflict):
        stocked.return_copy("A-1")


def test_return_before_loan_date_rejected(stocked):
    stocked.checkout("A-1", "ada@example.org", today="2026-03-10")
    with pytest.raises(LibraryError):
        stocked.return_copy("A-1", today="2026-03-01")


def test_renew_rules(stocked):
    stocked.checkout("A-1", "ada@example.org", today="2026-03-01")
    assert stocked.renew("A-1", today="2026-03-10")["due_on"] == "2026-03-29"
    with pytest.raises(Conflict, match="already renewed"):
        stocked.renew("A-1", today="2026-03-11")


def test_cannot_renew_overdue(stocked):
    stocked.checkout("A-1", "ada@example.org", today="2026-03-01")
    with pytest.raises(Conflict, match="overdue"):
        stocked.renew("A-1", today="2026-04-01")


def test_fine_formula():
    assert fine_cents(-3) == 0
    assert fine_cents(0) == 0
    assert fine_cents(2) == 50
    assert fine_cents(10_000) == FINE_CAP_CENTS


def test_bad_date_rejected(stocked):
    with pytest.raises(ValueError):
        stocked.checkout("A-1", "ada@example.org", today="03/01/2026")


# ---------------------------------------------------------------- reports

def test_overdue_report(stocked):
    stocked.checkout("A-1", "ada@example.org", today="2026-01-01")   # due 01-15
    stocked.checkout("B-1", "alan@example.org", today="2026-01-20")  # due 02-03
    stocked.checkout("A-2", "alan@example.org", today="2026-01-30")  # due 02-13, not overdue
    rows = stocked.overdue(today="2026-02-10")
    assert [(r["barcode"], r["days_overdue"], r["fine_cents"]) for r in rows] == [
        ("A-1", 26, 650), ("B-1", 7, 175)]


def test_popular_ranks_ties(stocked):
    for day in ("2026-01-01", "2026-01-05"):
        stocked.checkout("A-1", "ada@example.org", today=day)
        stocked.return_copy("A-1", today=day)
    stocked.checkout("A-2", "alan@example.org", today="2026-01-02")  # same book, other copy
    stocked.checkout("B-1", "ada@example.org", today="2026-01-06")
    rows = stocked.popular()
    assert [(r["rank"], r["title"], r["loans"]) for r in rows] == [
        (1, "Introduction to Algorithms", 3), (2, "Clean Code", 1)]


def test_author_report_counts_distinct(stocked):
    stocked.checkout("A-1", "ada@example.org", today="2026-01-01")
    by_author = {r["author"]: r for r in stocked.author_report()}
    assert by_author["Thomas H. Cormen"]["copies"] == 2
    assert by_author["Thomas H. Cormen"]["loans"] == 1
    assert by_author["Robert C. Martin"]["loans"] == 0


def test_member_history_newest_first(stocked):
    stocked.checkout("A-1", "ada@example.org", today="2026-01-01")
    stocked.return_copy("A-1", today="2026-01-05")
    stocked.checkout("B-1", "ada@example.org", today="2026-02-01")
    hist = stocked.member_history("ada@example.org")
    assert [h["barcode"] for h in hist] == ["B-1", "A-1"]
    assert hist[0]["returned_on"] is None


def test_stats(stocked):
    stocked.checkout("A-1", "ada@example.org", today="2026-01-01")
    assert stocked.stats() == {"books": 2, "copies": 3, "members": 2, "open_loans": 1, "total_loans": 1}
