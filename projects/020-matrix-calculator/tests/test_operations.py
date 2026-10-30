import random
from fractions import Fraction

import pytest

from matcalc import (
    Matrix,
    SingularMatrixError,
    determinant,
    determinant_cofactor,
    inverse,
    inverse_with_steps,
    rank,
    rref,
    solve,
)


def random_matrix(rng, n, m=None, lo=-5, hi=5):
    return Matrix([[rng.randint(lo, hi) for _ in range(m or n)] for _ in range(n)])


# ---- RREF ----------------------------------------------------------------
def test_rref_classic_system():
    r = rref(Matrix([[2, 1, -1, 8], [-3, -1, 2, -11], [-2, 1, 2, -3]]))
    assert r.matrix == Matrix([[1, 0, 0, 2], [0, 1, 0, 3], [0, 0, 1, -1]])
    assert r.pivots == (0, 1, 2)
    assert r.rank == 3


def test_rref_rank_deficient():
    r = rref(Matrix([[1, 2, 3], [4, 5, 6], [7, 8, 9]]))
    assert r.matrix == Matrix([[1, 0, -1], [0, 1, 2], [0, 0, 0]])
    assert r.rank == 2
    assert rank(Matrix([[0, 0], [0, 0]])) == 0


def test_rref_is_idempotent_and_canonical():
    rng = random.Random(1)
    for _ in range(50):
        m = random_matrix(rng, rng.randint(1, 4), rng.randint(1, 5))
        r = rref(m, steps=False).matrix
        assert rref(r, steps=False).matrix == r
        # Each pivot is 1 and is the only non-zero in its column.
        for i, c in enumerate(rref(m, steps=False).pivots):
            column = [r[k, c] for k in range(r.rows)]
            assert column[i] == 1 and sum(1 for x in column if x) == 1


def test_steps_record_each_operation_and_end_at_result():
    r = rref(Matrix([[0, 2], [1, 3]]))
    descriptions = [s.description for s in r.steps]
    assert descriptions[0] == "Start"
    assert descriptions[1] == "R1 <-> R2"
    assert any(d.startswith("R2 <- (1/2)R2") for d in descriptions)
    assert Matrix(r.steps.steps[-1].snapshot) == r.matrix


def test_steps_can_be_disabled():
    assert len(rref(Matrix([[1, 2], [3, 4]]), steps=False).steps) == 0


# ---- Determinant ---------------------------------------------------------
@pytest.mark.parametrize(
    "rows, expected",
    [
        ([[7]], 7),
        ([[1, 2], [3, 4]], -2),
        ([[2, 1, -1], [-3, -1, 2], [-2, 1, 2]], -1),
        ([[0, 1], [1, 0]], -1),  # needs a swap
        ([[1, 2, 3], [4, 5, 6], [7, 8, 9]], 0),
        ([["1/2", "1/3"], ["1/4", "1/5"]], Fraction(1, 10) - Fraction(1, 12)),
    ],
)
def test_determinant_known_values(rows, expected):
    m = Matrix(rows)
    assert determinant(m).value == expected
    assert determinant_cofactor(m) == expected


def test_determinant_matches_cofactor_on_random_matrices():
    rng = random.Random(42)
    for _ in range(100):
        m = random_matrix(rng, rng.randint(1, 5))
        assert determinant(m, steps=False).value == determinant_cofactor(m)


def test_determinant_is_multiplicative_and_transpose_invariant():
    rng = random.Random(7)
    for _ in range(30):
        n = rng.randint(1, 4)
        a, b = random_matrix(rng, n), random_matrix(rng, n)
        da = determinant(a, steps=False).value
        assert determinant(a @ b, steps=False).value == da * determinant(b, steps=False).value
        assert determinant(a.T, steps=False).value == da


def test_determinant_requires_square():
    with pytest.raises(ValueError):
        determinant(Matrix([[1, 2, 3]]))
    with pytest.raises(ValueError):
        determinant_cofactor(Matrix([[1, 2, 3]]))


def test_determinant_explanation_mentions_swaps():
    res = determinant(Matrix([[0, 1], [1, 0]]))
    assert "1 row swap" in res.explanation


# ---- Inverse -------------------------------------------------------------
def test_inverse_known():
    assert inverse(Matrix([[4, 7], [2, 6]])) == Matrix([["3/5", "-7/10"], ["-1/5", "2/5"]])


def test_inverse_round_trip_random():
    rng = random.Random(3)
    checked = 0
    while checked < 40:
        n = rng.randint(1, 5)
        m = random_matrix(rng, n)
        if determinant_cofactor(m) == 0:
            with pytest.raises(SingularMatrixError):
                inverse(m)
            continue
        inv = inverse(m)
        assert m @ inv == Matrix.identity(n)
        assert inv @ m == Matrix.identity(n)
        checked += 1


def test_inverse_steps_show_augmented_divider():
    res = inverse_with_steps(Matrix([[1, 2], [3, 4]]))
    assert res.steps.steps[0].divider == 2
    assert "|" in str(res.steps.steps[0])


def test_inverse_singular_and_nonsquare():
    with pytest.raises(SingularMatrixError):
        inverse(Matrix([[1, 2], [2, 4]]))
    with pytest.raises(ValueError):
        inverse(Matrix([[1, 2, 3], [4, 5, 6]]))


# ---- Solve ---------------------------------------------------------------
def test_solve_unique():
    sol = solve(Matrix([[2, 1, -1], [-3, -1, 2], [-2, 1, 2]]), Matrix([[8], [-11], [-3]]))
    assert sol.kind == "unique"
    assert sol.particular == (2, 3, -1)
    assert "x1 = 2" in sol.describe()


def test_solve_infinite():
    a = Matrix([[1, 2, 3], [2, 4, 6]])
    sol = solve(a, Matrix([[6], [12]]))
    assert sol.kind == "infinite"
    assert sol.free_vars == (1, 2)
    x = Matrix([[v] for v in sol.particular])
    assert a @ x == Matrix([[6], [12]])
    assert "x1 = 6 - 2t2 - 3t3" in sol.describe()


def test_solve_inconsistent():
    sol = solve(Matrix([[1, 1], [1, 1]]), Matrix([[1], [2]]))
    assert sol.kind == "none"
    assert "inconsistent" in sol.describe()


def test_solve_bad_shapes():
    with pytest.raises(ValueError):
        solve(Matrix([[1, 2]]), Matrix([[1], [2]]))
