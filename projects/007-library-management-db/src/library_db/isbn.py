"""ISBN normalization and check-digit validation.

ISBN-10 uses a weighted sum mod 11 (weights 10..1, 'X' = 10).
ISBN-13 uses alternating weights 1,3 mod 10, the same scheme as EAN-13 barcodes.
Validating in the application catches typos before they reach the database,
whose CHECK constraint only verifies the length.
"""

from __future__ import annotations


class InvalidISBN(ValueError):
    pass


def normalize(raw: str) -> str:
    """Strip hyphens/spaces and upper-case a trailing x."""
    return "".join(ch for ch in raw if ch not in "- ").upper()


def isbn10_valid(isbn: str) -> bool:
    if len(isbn) != 10 or not isbn[:9].isdigit() or not (isbn[9].isdigit() or isbn[9] == "X"):
        return False
    digits = [int(c) for c in isbn[:9]] + [10 if isbn[9] == "X" else int(isbn[9])]
    return sum(d * w for d, w in zip(digits, range(10, 0, -1))) % 11 == 0


def isbn13_valid(isbn: str) -> bool:
    if len(isbn) != 13 or not isbn.isdigit():
        return False
    total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(isbn))
    return total % 10 == 0


def validate(raw: str) -> str:
    """Return the normalized ISBN or raise :class:`InvalidISBN`."""
    isbn = normalize(raw)
    if isbn10_valid(isbn) or isbn13_valid(isbn):
        return isbn
    raise InvalidISBN(f"invalid ISBN: {raw!r}")


def to_isbn13(isbn10: str) -> str:
    """Convert a valid ISBN-10 to its ISBN-13 form (prefix 978, new check digit)."""
    isbn10 = validate(isbn10)
    if len(isbn10) == 13:
        return isbn10
    core = "978" + isbn10[:9]
    total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(core))
    return core + str((10 - total % 10) % 10)
