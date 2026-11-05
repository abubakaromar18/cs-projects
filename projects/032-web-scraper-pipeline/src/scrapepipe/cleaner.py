"""Transform stage: validate and normalise raw strings into typed records.

Every rule is a small pure function so it can be unit-tested in isolation.
Records that fail validation are not silently dropped; they are returned with
a reason so the pipeline can report data-quality problems.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass

RATING_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
CURRENCY_SYMBOLS = {"£": "GBP", "$": "USD", "€": "EUR"}

_ws = re.compile(r"\s+")
_price = re.compile(r"(?P<sym>[£$€])?\s*(?P<num>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)")
_stock_count = re.compile(r"\((\d+)\s+available\)", re.I)


@dataclass(frozen=True)
class Book:
    sku: str
    title: str
    url: str
    price_cents: int
    currency: str
    rating: int
    in_stock: bool
    stock_count: int | None
    category: str

    def to_dict(self) -> dict:
        return asdict(self)


class CleanError(ValueError):
    pass


def normalize_text(s: str) -> str:
    """NFKC-normalise, collapse whitespace, strip."""
    return _ws.sub(" ", unicodedata.normalize("NFKC", s)).strip()


def parse_price(s: str) -> tuple[int, str]:
    """'£51.77' -> (5177, 'GBP'). Integer cents avoid float rounding bugs."""
    m = _price.search(s or "")
    if not m:
        raise CleanError(f"unparseable price {s!r}")
    num = m.group("num").replace(",", "")
    whole, _, frac = num.partition(".")
    cents = int(whole) * 100 + int((frac + "00")[:2])
    currency = CURRENCY_SYMBOLS.get(m.group("sym") or "", "UNK")
    return cents, currency


def parse_rating(s: str) -> int:
    """'Three' / '3' / '3 stars' -> 3, validated to 0..5."""
    t = normalize_text(s).lower()
    if t in RATING_WORDS:
        return RATING_WORDS[t]
    m = re.match(r"(\d)", t)
    if m and 0 <= int(m.group(1)) <= 5:
        return int(m.group(1))
    raise CleanError(f"bad rating {s!r}")


def parse_availability(s: str) -> tuple[bool, int | None]:
    """'In stock (22 available)' -> (True, 22); 'Out of stock' -> (False, 0)."""
    t = normalize_text(s).lower()
    if not t:
        raise CleanError("missing availability")
    if "out of stock" in t or "unavailable" in t:
        return False, 0
    m = _stock_count.search(t)
    count = int(m.group(1)) if m else None
    return ("in stock" in t or (count or 0) > 0), count


def clean_record(raw) -> Book:
    """Convert a ``RawRecord`` into a ``Book`` or raise ``CleanError``."""
    title = normalize_text(raw.title)
    if not title:
        raise CleanError("missing title")
    sku = normalize_text(raw.sku).upper()
    if not sku:
        raise CleanError("missing sku")
    cents, currency = parse_price(raw.price)
    in_stock, count = parse_availability(raw.availability)
    return Book(
        sku=sku,
        title=title,
        url=raw.url.strip(),
        price_cents=cents,
        currency=currency,
        rating=parse_rating(raw.rating),
        in_stock=in_stock,
        stock_count=count,
        category=normalize_text(raw.category) or "Uncategorised",
    )


def clean_all(raws) -> tuple[list[Book], list[tuple[object, str]]]:
    """Clean many records; de-duplicate by SKU (first wins).

    Returns ``(books, rejects)`` where rejects are ``(raw, reason)`` pairs.
    """
    books: list[Book] = []
    rejects: list[tuple[object, str]] = []
    seen: set[str] = set()
    for raw in raws:
        try:
            book = clean_record(raw)
        except CleanError as e:
            rejects.append((raw, str(e)))
            continue
        if book.sku in seen:
            rejects.append((raw, "duplicate sku"))
            continue
        seen.add(book.sku)
        books.append(book)
    return books, rejects
