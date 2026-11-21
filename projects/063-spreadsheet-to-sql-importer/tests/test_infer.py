import datetime as dt

import pytest

from sheet2sql.infer import SqlType as T, classify, convert, join, profile_columns


@pytest.mark.parametrize(
    "value, expected",
    [
        ("", T.NULL), ("  ", T.NULL), ("NULL", T.NULL), ("n/a", T.NULL), (None, T.NULL),
        ("true", T.BOOLEAN), ("No", T.BOOLEAN), ("y", T.BOOLEAN),
        ("42", T.INTEGER), ("-7", T.INTEGER), ("1,234,567", T.INTEGER), ("0", T.INTEGER),
        ("3.14", T.REAL), ("-0.5", T.REAL), (".5", T.REAL), ("1e10", T.REAL), ("12,000.75", T.REAL),
        ("02134", T.TEXT),  # leading zero: keep as text (ZIP codes, IDs)
        ("007.5", T.TEXT),
        ("2024-02-29", T.DATE), ("03/15/2024", T.DATE),
        ("2024-02-29 13:45:00", T.DATETIME), ("2024-02-29T13:45", T.DATETIME),
        ("2024-02-30", T.TEXT),  # not a real date
        ("hello", T.TEXT), ("1,23", T.TEXT),
        # Native XLSX values
        (True, T.BOOLEAN), (5, T.INTEGER), (5.0, T.INTEGER), (5.5, T.REAL),
        (dt.date(2024, 1, 1), T.DATE), (dt.datetime(2024, 1, 1), T.DATE),
        (dt.datetime(2024, 1, 1, 8, 30), T.DATETIME), (float("nan"), T.NULL),
    ],
)
def test_classify(value, expected):
    assert classify(value) is expected


@pytest.mark.parametrize(
    "a, b, expected",
    [
        (T.NULL, T.INTEGER, T.INTEGER),
        (T.BOOLEAN, T.INTEGER, T.INTEGER),
        (T.INTEGER, T.REAL, T.REAL),
        (T.BOOLEAN, T.REAL, T.REAL),
        (T.DATE, T.DATETIME, T.DATETIME),
        (T.INTEGER, T.DATE, T.TEXT),
        (T.REAL, T.TEXT, T.TEXT),
        (T.NULL, T.NULL, T.NULL),
    ],
)
def test_join_is_least_upper_bound(a, b, expected):
    assert join(a, b) is expected
    assert join(b, a) is expected  # commutative


def test_join_is_idempotent_and_associative():
    types = list(T)
    for a in types:
        assert join(a, a) is a
        for b in types:
            for c in types:
                assert join(join(a, b), c) is join(a, join(b, c))


def test_convert_values():
    assert convert("1,234", T.INTEGER) == 1234
    assert convert("yes", T.INTEGER) == 1
    assert convert("12,000.5", T.REAL) == 12000.5
    assert convert("7", T.REAL) == 7.0
    assert convert("No", T.BOOLEAN) == 0
    assert convert("03/15/2024", T.DATE) == "2024-03-15"
    assert convert("2024-03-15", T.DATETIME) == "2024-03-15 00:00:00"
    assert convert(dt.datetime(2024, 3, 15, 9, 5), T.DATETIME) == "2024-03-15 09:05:00"
    assert convert(5.0, T.TEXT) == "5"
    assert convert("  padded ", T.TEXT) == "padded"
    assert convert("", T.INTEGER) is None
    with pytest.raises(ValueError):
        convert("abc", T.INTEGER)


def test_profile_columns_widens_and_tracks_nulls_and_uniqueness():
    header = ["id", "score", "when", "tag", "empty"]
    rows = [
        ["1", "10", "2024-01-01", "a", ""],
        ["2", "10.5", "2024-01-02 10:00", "b"],  # short row -> missing cells are null
        ["3", "", "2024-01-03", "a", ""],
    ]
    p = {c.name: c for c in profile_columns(header, rows)}
    assert p["id"].final_type is T.INTEGER and p["id"].unique and not p["id"].nullable
    assert p["score"].final_type is T.REAL and p["score"].nullable
    assert p["when"].final_type is T.DATETIME
    assert p["tag"].final_type is T.TEXT and not p["tag"].unique
    assert p["empty"].final_type is T.TEXT and p["empty"].nullable  # no evidence -> TEXT


def test_profile_respects_sample():
    rows = [["1"], ["2"], ["oops"]]
    (p,) = profile_columns(["x"], rows, sample=2)
    assert p.final_type is T.INTEGER
