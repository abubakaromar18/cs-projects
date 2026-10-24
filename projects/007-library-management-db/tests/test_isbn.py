import pytest

from library_db import isbn


@pytest.mark.parametrize("value", ["9780262033848", "978-0-13-235088-4", "0262510871", "080442957X", "080442957x"])
def test_valid(value):
    assert isbn.validate(value) == isbn.normalize(value)


@pytest.mark.parametrize("value", ["9780262033849", "0262510872", "12345", "abcdefghij", "", "97802620338X8"])
def test_invalid(value):
    with pytest.raises(isbn.InvalidISBN):
        isbn.validate(value)


def test_isbn10_to_13():
    assert isbn.to_isbn13("0-262-51087-1") == "9780262510875"
    assert isbn.to_isbn13("9780262510875") == "9780262510875"


def test_converted_isbn13_is_valid():
    assert isbn.isbn13_valid(isbn.to_isbn13("080442957X"))
