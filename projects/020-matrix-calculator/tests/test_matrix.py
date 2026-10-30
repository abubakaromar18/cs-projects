from fractions import Fraction

import pytest

from matcalc import Matrix
from matcalc.matrix import to_fraction


def test_entries_are_exact_fractions():
    m = Matrix([["1/3", 0.1], [2, "-1.5"]])
    assert m[0, 0] == Fraction(1, 3)
    assert m[0, 1] == Fraction(1, 10)
    assert m[1, 1] == Fraction(-3, 2)


def test_rejects_ragged_and_empty():
    with pytest.raises(ValueError):
        Matrix([[1, 2], [3]])
    with pytest.raises(ValueError):
        Matrix([])
    with pytest.raises(ValueError):
        to_fraction("abc")
    with pytest.raises(TypeError):
        to_fraction(True)


def test_arithmetic():
    a = Matrix([[1, 2], [3, 4]])
    b = Matrix([[5, 6], [7, 8]])
    assert a + b == Matrix([[6, 8], [10, 12]])
    assert b - a == Matrix([[4, 4], [4, 4]])
    assert a @ b == Matrix([[19, 22], [43, 50]])
    assert 2 * a == a * 2 == Matrix([[2, 4], [6, 8]])
    assert -a == Matrix([[-1, -2], [-3, -4]])
    assert a.trace() == 5


def test_matmul_shape_check():
    with pytest.raises(ValueError):
        Matrix([[1, 2]]) @ Matrix([[1, 2]])
    assert (Matrix([[1, 2]]) @ Matrix([[3], [4]])) == Matrix([[11]])


def test_transpose_and_minor():
    m = Matrix([[1, 2, 3], [4, 5, 6]])
    assert m.T == Matrix([[1, 4], [2, 5], [3, 6]])
    assert m.T.T == m
    assert Matrix([[1, 2, 3], [4, 5, 6], [7, 8, 9]]).minor(1, 1) == Matrix([[1, 3], [7, 9]])


def test_power_including_negative():
    fib = Matrix([[1, 1], [1, 0]])
    assert (fib ** 10)[0, 1] == 55  # Fibonacci via fast exponentiation
    assert fib ** 0 == Matrix.identity(2)
    a = Matrix([[2, 0], [0, 4]])
    assert a ** -1 == Matrix([["1/2", 0], [0, "1/4"]])


def test_str_renders_fractions():
    text = str(Matrix([["1/2", -3], [10, 0]]))
    assert "1/2" in text and "-3" in text
    assert len(text.splitlines()) == 2
