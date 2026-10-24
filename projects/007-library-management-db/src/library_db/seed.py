"""Sample data so the CLI has something to show right away.

Loans are dated relative to ``today`` so that ``overdue`` always has results.
"""

from __future__ import annotations

from datetime import date, timedelta

from .library import Library

BOOKS = [
    # isbn, title, authors, publisher, year, genres
    ("9780262033848", "Introduction to Algorithms", ["Thomas H. Cormen", "Charles E. Leiserson",
     "Ronald L. Rivest", "Clifford Stein"], "MIT Press", 2009, ["Computer Science", "Algorithms"]),
    ("9780201633610", "Design Patterns", ["Erich Gamma", "Richard Helm", "Ralph Johnson",
     "John Vlissides"], "Addison-Wesley", 1994, ["Computer Science", "Software Engineering"]),
    ("9780132350884", "Clean Code", ["Robert C. Martin"], "Prentice Hall", 2008, ["Software Engineering"]),
    ("0262510871", "Structure and Interpretation of Computer Programs", ["Harold Abelson",
     "Gerald Jay Sussman"], "MIT Press", 1996, ["Computer Science", "Programming Languages"]),
    ("9780131103627", "The C Programming Language", ["Brian W. Kernighan", "Dennis M. Ritchie"],
     "Prentice Hall", 1988, ["Programming Languages"]),
    ("9781449373320", "Designing Data-Intensive Applications", ["Martin Kleppmann"], "O'Reilly Media",
     2017, ["Databases", "Distributed Systems"]),
    ("9780596517748", "JavaScript: The Good Parts", ["Douglas Crockford"], "O'Reilly Media", 2008,
     ["Programming Languages"]),
]

MEMBERS = [
    ("Ada Lovelace", "ada@example.org"),
    ("Alan Turing", "alan@example.org"),
    ("Grace Hopper", "grace@example.org"),
    ("Edsger Dijkstra", "edsger@example.org"),
]


def seed(lib: Library, today: date | None = None) -> None:
    today = today or date.today()
    d = lambda days_ago: (today - timedelta(days=days_ago)).isoformat()  # noqa: E731

    for i, (isbn, title, authors, pub, year, genres) in enumerate(BOOKS, start=1):
        lib.add_book(isbn, title, authors, pub, year, genres)
        n_copies = 2 if i <= 3 else 1
        for c in range(1, n_copies + 1):
            lib.add_copy(isbn, f"C{i:03d}-{c}", acquired_on=d(400))

    for name, email in MEMBERS:
        lib.add_member(name, email, joined_on=d(365))

    # Historic loans (already returned): drives the "popular" report.
    history = [
        ("C001-1", "ada@example.org", 120, 110),
        ("C001-2", "alan@example.org", 100, 95),
        ("C001-1", "grace@example.org", 90, 70),
        ("C003-1", "edsger@example.org", 80, 60),
        ("C002-1", "ada@example.org", 75, 65),
        ("C006-1", "alan@example.org", 50, 40),
        ("C006-1", "grace@example.org", 38, 30),
    ]
    for barcode, email, out_ago, back_ago in history:
        lib.checkout(barcode, email, today=d(out_ago))
        lib.return_copy(barcode, today=d(back_ago))

    # Current loans: two are overdue (borrowed 20 and 30 days ago, 14-day term).
    lib.checkout("C001-1", "ada@example.org", today=d(30))
    lib.checkout("C004-1", "alan@example.org", today=d(20))
    lib.checkout("C002-2", "grace@example.org", today=d(5))
    lib.checkout("C006-1", "edsger@example.org", today=d(2))


def is_empty(lib: Library) -> bool:
    return lib.conn.execute("SELECT NOT EXISTS (SELECT 1 FROM books)").fetchone()[0] == 1


__all__ = ["seed", "is_empty", "BOOKS", "MEMBERS"]
