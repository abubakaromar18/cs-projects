import pytest

from scrapepipe.cleaner import (CleanError, clean_all, clean_record, normalize_text,
                                parse_availability, parse_price, parse_rating)
from scrapepipe.parser import RawRecord


@pytest.mark.parametrize("s,expected", [
    ("£51.77", (5177, "GBP")),
    ("$5", (500, "USD")),
    ("€0.5", (50, "EUR")),
    ("£1,204.50", (120450, "GBP")),
    ("  price: £12.345 ", (1234, "GBP")),
    ("12.00", (1200, "UNK")),
])
def test_parse_price(s, expected):
    assert parse_price(s) == expected


@pytest.mark.parametrize("s", ["", "free", "£"])
def test_parse_price_rejects(s):
    with pytest.raises(CleanError):
        parse_price(s)


@pytest.mark.parametrize("s,n", [("Three", 3), ("five", 5), (" 4 stars", 4), ("Zero", 0)])
def test_parse_rating(s, n):
    assert parse_rating(s) == n


@pytest.mark.parametrize("s", ["", "Seven", "9"])
def test_parse_rating_rejects(s):
    with pytest.raises(CleanError):
        parse_rating(s)


def test_parse_availability():
    assert parse_availability("  In stock (22 available) ") == (True, 22)
    assert parse_availability("Out of stock") == (False, 0)
    assert parse_availability("In stock") == (True, None)
    with pytest.raises(CleanError):
        parse_availability("   ")


def test_normalize_text_collapses_whitespace_and_nfkc():
    assert normalize_text("  The   Whitespace\n Edition ") == "The Whitespace Edition"
    assert normalize_text("ﬁne") == "fine"  # ligature -> letters


def raw(**kw):
    base = dict(sku="b1", title="T", url="u", price="£1.00", rating="One",
                availability="In stock (1 available)", category="Poetry")
    base.update(kw)
    return RawRecord(**base)


def test_clean_record():
    b = clean_record(raw(sku=" b9 ", category=""))
    assert b.sku == "B9" and b.price_cents == 100 and b.rating == 1
    assert b.in_stock and b.stock_count == 1 and b.category == "Uncategorised"


def test_clean_all_dedupes_and_reports():
    books, rejects = clean_all([raw(), raw(title="dup"), raw(sku="b2", price=""), raw(sku="b3", title=" ")])
    assert [b.sku for b in books] == ["B1"]
    reasons = [r for _, r in rejects]
    assert reasons[0] == "duplicate sku"
    assert "price" in reasons[1] and reasons[2] == "missing title"
