import pytest

from matcalc import Matrix, parse_matrix

EXPECTED = Matrix([[1, 2, 3], [4, 5, 6]])


@pytest.mark.parametrize(
    "text",
    [
        "1 2 3; 4 5 6",
        "[[1, 2, 3], [4, 5, 6]]",
        "1,2,3\n4,5,6\n",
        "# comment line\n1 2 3\n\n4 5 6",
        "  1, 2, 3 ;4 5 6  ",
    ],
)
def test_formats(text):
    assert parse_matrix(text) == EXPECTED


def test_fractions_and_decimals():
    m = parse_matrix("1/2 -0.25; 3 -7/3")
    assert m == Matrix([["1/2", "-1/4"], [3, "-7/3"]])


def test_single_row_vector():
    assert parse_matrix("[1, 2, 3]") == Matrix([[1, 2, 3]])


@pytest.mark.parametrize("bad", ["", "1 2; 3", "[[1,2],[3,4]", "[[1,2] x [3,4]]", "1 two"])
def test_errors(bad):
    with pytest.raises(ValueError):
        parse_matrix(bad)
