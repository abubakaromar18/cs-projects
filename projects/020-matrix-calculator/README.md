# Matrix Calculator

A command-line matrix calculator that **shows its work**. It computes
determinants, inverses, reduced row echelon form, rank and solutions to
linear systems, and with `--steps` it prints every elementary row operation
the way you would write it on paper. All arithmetic is **exact**: entries are
rational numbers, so you get `3/2`, never `1.4999999999999998`.

Pure Python standard library; no NumPy.

```
$ matcalc det "0 2 1; 1 1 0; 2 0 3" --steps --check
Step 1: Start
⎡ 0 2 1 ⎤
⎢ 1 1 0 ⎥
⎣ 2 0 3 ⎦

Step 2: R1 <-> R2
⎡ 1 1 0 ⎤
⎢ 0 2 1 ⎥
⎣ 2 0 3 ⎦

Step 3: R3 <- R3 - 2R1
⎡ 1  1 0 ⎤
⎢ 0  2 1 ⎥
⎣ 0 -2 3 ⎦

Step 4: R3 <- R3 + R2
⎡ 1 1 0 ⎤
⎢ 0 2 1 ⎥
⎣ 0 0 4 ⎦

Upper-triangular after 1 row swap(s); det = -(1 * 2 * 4) = -8
Cofactor expansion gives -8 (agrees)
det = -8
```

```
$ matcalc inv "1 2; 3 4" --steps
Step 1: Start with [A | I]
⎡ 1 2 | 1 0 ⎤
⎣ 3 4 | 0 1 ⎦

Step 2: R2 <- R2 - 3R1
⎡ 1  2 |  1 0 ⎤
⎣ 0 -2 | -3 1 ⎦

Step 3: R2 <- (-1/2)R2
⎡ 1 2 |   1    0 ⎤
⎣ 0 1 | 3/2 -1/2 ⎦

Step 4: R1 <- R1 - 2R2
⎡ 1 0 |  -2    1 ⎤
⎣ 0 1 | 3/2 -1/2 ⎦

A^-1 =
⎡  -2    1 ⎤
⎣ 3/2 -1/2 ⎦
```

```
$ matcalc solve "1 2 3; 2 4 6" "6 12"
Infinitely many solutions (2 free variable(s)):
  x1 = 6 - 2t2 - 3t3
  x2 = t2  (free)
  x3 = t3  (free)
```

## Features

| Command | What it does |
|---|---|
| `det A [--steps] [--check]` | Determinant by elimination; `--check` re-computes it by cofactor expansion |
| `inv A [--steps] [--check]` | Inverse by row-reducing `[A \| I]`; `--check` verifies `A·A⁻¹ = I` |
| `rref A [--steps]` | Reduced row echelon form, rank and pivot columns |
| `rank A` | Rank only |
| `solve A b [--steps]` | Solves `Ax = b`: unique, infinitely many (parametric form) or none |
| `mul A B`, `transpose A`, `pow A n` | Products, transpose, integer powers (negative `n` uses the inverse) |

Matrices can be typed in several formats; entries may be integers, decimals or
fractions:

```
"1 2 3; 4 5 6"            # MATLAB style
"[[1, 2, 3], [4, 5, 6]]"  # Python / JSON style
"1/2 -0.25; 3 -7/3"       # fractions and decimals
@matrix.txt               # one row per line, from a file ('#' comments allowed)
-                         # read from standard input
```

## CS and math concepts

- **Gauss–Jordan elimination**: the three elementary row operations (swap,
  scale, add a multiple) and how they reach the unique RREF of a matrix.
  Pivot columns give the rank; non-pivot columns are free variables.
- **Determinant bookkeeping**: a swap negates the determinant and adding a
  multiple of a row leaves it unchanged, so after reducing to upper-triangular
  form `det(A) = (-1)^swaps · ∏ diagonal`. That is O(n³), compared with the
  O(n!) Laplace (cofactor) expansion, which is kept as an independent check.
- **Inverse via `[A | I]`**: the row operations that turn `A` into `I` are
  exactly `A⁻¹`, so applying them to `I` produces it. A missing pivot means
  `A` is singular.
- **Consistency of linear systems**: a row `[0 … 0 | c]` with `c ≠ 0` means
  no solution; free variables mean infinitely many.
- **Exact rational arithmetic** with `fractions.Fraction`: why floating point
  is the wrong tool for a step-by-step teaching calculator, and why exact
  arithmetic lets pivot choice favor readability (±1 pivots) instead of
  numerical stability (partial pivoting).
- **Exponentiation by squaring** for `pow`, e.g. Fibonacci numbers from
  `[[1,1],[1,0]]^n` in O(log n) multiplications.
- **Property-based testing ideas**: the tests check algebraic identities on
  random matrices (`det(AB) = det(A)·det(B)`, `det(Aᵀ) = det(A)`,
  `A·A⁻¹ = I`, RREF idempotence) rather than only hand-picked examples.

## Project layout

```
src/matcalc/
  matrix.py      immutable Matrix of Fractions: arithmetic, transpose, power, pretty printing
  steps.py       StepLog: applies row operations and records a snapshot after each
  operations.py  rref, determinant (+ cofactor), inverse, solve
  parser.py      text -> Matrix for the supported input formats
  cli.py         argparse front end
tests/           pytest suite (50 tests)
```

## Build, run, test

Requires Python 3.10+.

```bash
make dev                      # editable install + pytest
make test                     # run the tests
make demo                     # rref, det and inverse of a sample matrix, with steps

# or run from source without installing
PYTHONPATH=src python3 -m matcalc rref "2 1 -1 8; -3 -1 2 -11; -2 1 2 -3" --steps
```

After `make install` (or `pip install .`) the `matcalc` command is on your PATH.

It also works as a library:

```python
from matcalc import Matrix, determinant, inverse, rref

a = Matrix([[2, 1], [1, 3]])
print(determinant(a).value)     # 5
print(inverse(a))               # exact fractions
print(rref(a).steps.render())   # the full worked solution
```

## Possible extensions

- LU and QR decompositions, shown step by step
- Eigenvalues of 2×2 and 3×3 matrices via the characteristic polynomial
- Null space and column space bases from the RREF
- LaTeX output of the steps for pasting into homework or notes
- An interactive REPL with named variables (`A = ...`, `inv(A) @ B`)
- A web front end that animates each row operation
