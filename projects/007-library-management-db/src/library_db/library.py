"""Service layer: the library's business rules on top of the schema.

All SQL uses ``?`` placeholders (parameter binding), never string formatting,
so user input can't change the shape of a query (no SQL injection).

Rules enforced here (the schema enforces the structural ones):

* a member may hold at most ``MAX_LOANS`` copies at once;
* a member with an overdue loan can't borrow more until it's returned;
* a loan can be renewed ``MAX_RENEWALS`` times, and only while not overdue;
* late returns accrue a fine of ``FINE_PER_DAY_CENTS`` per day, capped.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any, Iterable

from . import isbn as isbn_mod
from .db import transaction

MAX_LOANS = 5
LOAN_DAYS = 14
MAX_RENEWALS = 1
FINE_PER_DAY_CENTS = 25
FINE_CAP_CENTS = 2000


# --------------------------------------------------------------------------- errors


class LibraryError(Exception):
    """Base class for rule violations the CLI should report cleanly."""


class NotFound(LibraryError):
    pass


class Conflict(LibraryError):
    pass


# --------------------------------------------------------------------------- helpers


def _today(today: date | str | None) -> str:
    if today is None:
        return date.today().isoformat()
    if isinstance(today, date):
        return today.isoformat()
    return date.fromisoformat(today).isoformat()  # validates the format


def fine_cents(days_late: int) -> int:
    """Fine for a loan returned ``days_late`` days after its due date."""
    return min(max(days_late, 0) * FINE_PER_DAY_CENTS, FINE_CAP_CENTS)


def _rows(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    return [dict(r) for r in cur.fetchall()]


class Library:
    """Thin object wrapper around one SQLite connection."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ------------------------------------------------------------ lookup tables

    def _get_or_create(self, table: str, name: str) -> int:
        """Return the id for ``name`` in a (id, name UNIQUE) lookup table.

        ``table`` comes from our own code, never from user input, so it is
        safe to interpolate; ``name`` is always bound as a parameter.
        """
        id_col = {"authors": "author_id", "publishers": "publisher_id", "genres": "genre_id"}[table]
        name = name.strip()
        self.conn.execute(f"INSERT INTO {table}(name) VALUES (?) ON CONFLICT(name) DO NOTHING", (name,))
        row = self.conn.execute(f"SELECT {id_col} FROM {table} WHERE name = ?", (name,)).fetchone()
        return row[0]

    # ------------------------------------------------------------ catalog

    def add_book(
        self,
        isbn: str,
        title: str,
        authors: Iterable[str],
        publisher: str | None = None,
        year: int | None = None,
        genres: Iterable[str] = (),
    ) -> int:
        """Insert a book and its author/genre links in one transaction.

        ISBNs are stored in canonical ISBN-13 form, so entering the ISBN-10 of a
        book that's already in the catalog is detected as a duplicate.
        """
        canonical = isbn_mod.to_isbn13(isbn)
        authors = [a for a in (a.strip() for a in authors) if a]
        if not authors:
            raise LibraryError("a book needs at least one author")
        with transaction(self.conn):
            pub_id = self._get_or_create("publishers", publisher) if publisher else None
            try:
                cur = self.conn.execute(
                    "INSERT INTO books(isbn, title, publisher_id, published_year) VALUES (?, ?, ?, ?)",
                    (canonical, title.strip(), pub_id, year),
                )
            except sqlite3.IntegrityError as e:
                if "UNIQUE" in str(e):
                    raise Conflict(f"a book with ISBN {canonical} already exists") from e
                raise LibraryError(f"invalid book data: {e}") from e
            book_id = cur.lastrowid
            for pos, name in enumerate(dict.fromkeys(authors), start=1):  # dedupe, keep order
                self.conn.execute(
                    "INSERT INTO book_authors(book_id, author_id, position) VALUES (?, ?, ?)",
                    (book_id, self._get_or_create("authors", name), pos),
                )
            for g in {g.strip() for g in genres if g.strip()}:
                self.conn.execute(
                    "INSERT OR IGNORE INTO book_genres(book_id, genre_id) VALUES (?, ?)",
                    (book_id, self._get_or_create("genres", g)),
                )
        return book_id

    def book_id_for_isbn(self, isbn: str) -> int:
        row = self.conn.execute(
            "SELECT book_id FROM books WHERE isbn = ?", (isbn_mod.to_isbn13(isbn),)
        ).fetchone()
        if row is None:
            raise NotFound(f"no book with ISBN {isbn}")
        return row[0]

    def add_copy(self, isbn: str, barcode: str, acquired_on: date | str | None = None) -> int:
        book_id = self.book_id_for_isbn(isbn)
        try:
            cur = self.conn.execute(
                "INSERT INTO copies(book_id, barcode, acquired_on) VALUES (?, ?, ?)",
                (book_id, barcode.strip(), _today(acquired_on)),
            )
        except sqlite3.IntegrityError as e:
            raise Conflict(f"barcode {barcode!r} is already in use") from e
        return cur.lastrowid

    def catalog(self) -> list[dict[str, Any]]:
        return _rows(self.conn.execute("SELECT * FROM v_book_catalog ORDER BY title COLLATE NOCASE"))

    def search(self, text: str) -> list[dict[str, Any]]:
        """Case-insensitive substring search across title, author and genre.

        ``EXISTS`` subqueries avoid the duplicate rows a plain JOIN would give
        for books with several matching authors or genres.
        """
        like = "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        sql = """
            SELECT cat.* FROM v_book_catalog cat
            WHERE cat.title LIKE :q ESCAPE '\\'
               OR cat.isbn = :exact
               OR EXISTS (SELECT 1 FROM book_authors ba JOIN authors a USING (author_id)
                          WHERE ba.book_id = cat.book_id AND a.name LIKE :q ESCAPE '\\')
               OR EXISTS (SELECT 1 FROM book_genres bg JOIN genres g USING (genre_id)
                          WHERE bg.book_id = cat.book_id AND g.name LIKE :q ESCAPE '\\')
            ORDER BY cat.title COLLATE NOCASE
        """
        return _rows(self.conn.execute(sql, {"q": like, "exact": isbn_mod.normalize(text)}))

    # ------------------------------------------------------------ members

    def add_member(self, name: str, email: str, joined_on: date | str | None = None) -> int:
        try:
            cur = self.conn.execute(
                "INSERT INTO members(name, email, joined_on) VALUES (?, ?, ?)",
                (name.strip(), email.strip(), _today(joined_on)),
            )
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):
                raise Conflict(f"a member with email {email} already exists") from e
            raise LibraryError(f"invalid member data: {e}") from e
        return cur.lastrowid

    def member_id_for_email(self, email: str) -> int:
        row = self.conn.execute("SELECT member_id FROM members WHERE email = ?", (email.strip(),)).fetchone()
        if row is None:
            raise NotFound(f"no member with email {email}")
        return row[0]

    def member_history(self, email: str) -> list[dict[str, Any]]:
        member_id = self.member_id_for_email(email)
        sql = """
            SELECT l.loan_id, b.title, c.barcode, l.loaned_on, l.due_on, l.returned_on, l.renewals
            FROM loans l
            JOIN copies c USING (copy_id)
            JOIN books  b USING (book_id)
            WHERE l.member_id = ?
            ORDER BY l.loaned_on DESC, l.loan_id DESC
        """
        return _rows(self.conn.execute(sql, (member_id,)))

    # ------------------------------------------------------------ circulation

    def _copy_id(self, barcode: str) -> int:
        row = self.conn.execute("SELECT copy_id FROM copies WHERE barcode = ?", (barcode.strip(),)).fetchone()
        if row is None:
            raise NotFound(f"no copy with barcode {barcode}")
        return row[0]

    def checkout(
        self,
        barcode: str,
        email: str,
        today: date | str | None = None,
        loan_days: int = LOAN_DAYS,
    ) -> dict[str, Any]:
        """Lend a copy to a member. Returns the new loan's id and due date."""
        day = _today(today)
        due = (date.fromisoformat(day) + timedelta(days=loan_days)).isoformat()
        with transaction(self.conn):
            copy_id = self._copy_id(barcode)
            member_id = self.member_id_for_email(email)

            open_count, overdue_count = self.conn.execute(
                """SELECT count(*), coalesce(sum(due_on < ?), 0)
                   FROM loans WHERE member_id = ? AND returned_on IS NULL""",
                (day, member_id),
            ).fetchone()
            if overdue_count:
                raise Conflict(f"{email} has {overdue_count} overdue loan(s); return them first")
            if open_count >= MAX_LOANS:
                raise Conflict(f"{email} already has the maximum of {MAX_LOANS} loans")

            try:
                cur = self.conn.execute(
                    "INSERT INTO loans(copy_id, member_id, loaned_on, due_on) VALUES (?, ?, ?, ?)",
                    (copy_id, member_id, day, due),
                )
            except sqlite3.IntegrityError as e:
                # The partial unique index rejects a second open loan for a copy.
                raise Conflict(f"copy {barcode} is already on loan") from e
        return {"loan_id": cur.lastrowid, "barcode": barcode, "email": email, "due_on": due}

    def _open_loan(self, barcode: str) -> sqlite3.Row:
        row = self.conn.execute(
            "SELECT * FROM loans WHERE copy_id = ? AND returned_on IS NULL", (self._copy_id(barcode),)
        ).fetchone()
        if row is None:
            raise Conflict(f"copy {barcode} is not on loan")
        return row

    def return_copy(self, barcode: str, today: date | str | None = None) -> dict[str, Any]:
        """Close the open loan for a copy and report any fine owed."""
        day = _today(today)
        with transaction(self.conn):
            loan = self._open_loan(barcode)
            if day < loan["loaned_on"]:
                raise LibraryError("return date is before the loan date")
            self.conn.execute("UPDATE loans SET returned_on = ? WHERE loan_id = ?", (day, loan["loan_id"]))
        days_late = (date.fromisoformat(day) - date.fromisoformat(loan["due_on"])).days
        return {
            "loan_id": loan["loan_id"],
            "barcode": barcode,
            "days_late": max(days_late, 0),
            "fine_cents": fine_cents(days_late),
        }

    def renew(self, barcode: str, today: date | str | None = None, loan_days: int = LOAN_DAYS) -> dict[str, Any]:
        """Extend an open loan by ``loan_days`` from its current due date."""
        day = _today(today)
        with transaction(self.conn):
            loan = self._open_loan(barcode)
            if loan["due_on"] < day:
                raise Conflict("overdue loans can't be renewed")
            if loan["renewals"] >= MAX_RENEWALS:
                raise Conflict(f"loan already renewed {MAX_RENEWALS} time(s)")
            new_due = (date.fromisoformat(loan["due_on"]) + timedelta(days=loan_days)).isoformat()
            self.conn.execute(
                "UPDATE loans SET due_on = ?, renewals = renewals + 1 WHERE loan_id = ?",
                (new_due, loan["loan_id"]),
            )
        return {"loan_id": loan["loan_id"], "barcode": barcode, "due_on": new_due}

    # ------------------------------------------------------------ reports

    def overdue(self, today: date | str | None = None) -> list[dict[str, Any]]:
        """Open loans past their due date, most overdue first, with the fine so far.

        ``julianday`` turns ISO dates into day numbers so SQL can subtract them.
        """
        sql = """
            SELECT member, email, title, barcode, due_on,
                   CAST(julianday(:today) - julianday(due_on) AS INTEGER) AS days_overdue,
                   min(CAST(julianday(:today) - julianday(due_on) AS INTEGER) * :rate, :cap) AS fine_cents
            FROM v_open_loans
            WHERE due_on < :today
            ORDER BY days_overdue DESC, member
        """
        params = {"today": _today(today), "rate": FINE_PER_DAY_CENTS, "cap": FINE_CAP_CENTS}
        return _rows(self.conn.execute(sql, params))

    def popular(self, limit: int = 10) -> list[dict[str, Any]]:
        """Books ranked by total loans, using a window function for ties.

        ``RANK()`` gives equal counts the same rank (1, 2, 2, 4, ...).
        """
        sql = """
            WITH counts AS (
                SELECT b.book_id, b.title, count(l.loan_id) AS loans
                FROM books b
                LEFT JOIN copies c ON c.book_id = b.book_id
                LEFT JOIN loans  l ON l.copy_id = c.copy_id
                GROUP BY b.book_id
            )
            SELECT RANK() OVER (ORDER BY loans DESC) AS rank, title, loans
            FROM counts
            WHERE loans > 0
            ORDER BY rank, title
            LIMIT ?
        """
        return _rows(self.conn.execute(sql, (limit,)))

    def author_report(self) -> list[dict[str, Any]]:
        """Per-author totals: books written, copies held, loans to date."""
        sql = """
            SELECT a.name AS author,
                   count(DISTINCT ba.book_id) AS books,
                   count(DISTINCT c.copy_id)  AS copies,
                   count(DISTINCT l.loan_id)  AS loans
            FROM authors a
            JOIN book_authors ba ON ba.author_id = a.author_id
            LEFT JOIN copies c   ON c.book_id = ba.book_id
            LEFT JOIN loans  l   ON l.copy_id = c.copy_id
            GROUP BY a.author_id
            ORDER BY loans DESC, a.name
        """
        return _rows(self.conn.execute(sql))

    def stats(self) -> dict[str, int]:
        q = lambda sql: self.conn.execute(sql).fetchone()[0]  # noqa: E731
        return {
            "books": q("SELECT count(*) FROM books"),
            "copies": q("SELECT count(*) FROM copies"),
            "members": q("SELECT count(*) FROM members"),
            "open_loans": q("SELECT count(*) FROM loans WHERE returned_on IS NULL"),
            "total_loans": q("SELECT count(*) FROM loans"),
        }
