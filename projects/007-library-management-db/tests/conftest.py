import pytest

from library_db import Library, connect

TODAY = "2026-03-01"


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


@pytest.fixture
def lib(conn):
    return Library(conn)


@pytest.fixture
def stocked(lib):
    """A library with two books, three copies and two members."""
    lib.add_book("9780262033848", "Introduction to Algorithms",
                 ["Thomas H. Cormen", "Charles E. Leiserson"], "MIT Press", 2009, ["Algorithms"])
    lib.add_book("9780132350884", "Clean Code", ["Robert C. Martin"], "Prentice Hall", 2008,
                 ["Software Engineering"])
    lib.add_copy("9780262033848", "A-1", "2025-01-01")
    lib.add_copy("9780262033848", "A-2", "2025-01-01")
    lib.add_copy("9780132350884", "B-1", "2025-01-01")
    lib.add_member("Ada Lovelace", "ada@example.org", "2025-01-01")
    lib.add_member("Alan Turing", "alan@example.org", "2025-01-01")
    return lib
