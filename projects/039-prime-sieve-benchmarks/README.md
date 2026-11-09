# Prime Sieve Benchmarks

A small C11 library and command-line tool that implements four prime sieves and
times them against each other. It also answers count, list, and range queries,
including ranges far above 2^32 that a whole-range sieve could not hold in memory.

## Algorithms

| Name | Approach | Time | Memory |
| --- | --- | --- | --- |
| `eratosthenes` | Classic sieve, one byte per integer | O(n log log n) | O(n) |
| `odd-bitset` | Eratosthenes, one bit per odd integer | O(n log log n) | O(n), 16x smaller |
| `atkin` | Parity of solutions to quadratic forms | O(n) arithmetic steps in the full version | O(n) |
| `segmented` | Eratosthenes in 32 KiB blocks | O(n log log n) | O(sqrt n) |

## Key CS concepts

- **Memory hierarchy.** All the Eratosthenes variants do similar work, yet the
  segmented sieve wins easily because each block fits in the L1 cache.
- **Space/time trade-offs.** Bit packing and skipping even numbers cut memory.
- **Number theory in algorithms.** Atkin classifies candidates using residues
  mod 12 and binary quadratic forms.
- **Asymptotics versus constants.** This Atkin implementation is the simple
  variant, which loops over every (x, y) pair. It has a better growth rate on
  paper than Eratosthenes but does not beat the tuned sieves here.
- **Callback-based API.** Primes stream to the caller, so counting needs no
  result storage.

## Build, run, test

Requires a C11 compiler and `make`.

```sh
make            # builds build/primes
make test       # runs the test suite
make sanitize   # runs the tests under AddressSanitizer and UBSan
make bench      # runs the default benchmark
```

## Usage

```
primes bench [--limit N] [--reps R]   compare every algorithm
primes count [--algo NAME] N          count primes <= N
primes list  [--algo NAME] N          print primes <= N
primes range LO HI                    print primes in [LO, HI]
primes algos                          list algorithm names
```

`count` and `list` default to the segmented sieve. Limits are 4×10^9 for the
whole-range algorithms and 10^14 for the segmented one.

### Example

```
$ build/primes bench --limit 100000000 --reps 3
limit = 100000000, best of 3 run(s)

algorithm              primes      seconds  notes
eratosthenes          5761455       0.8157  classic, one byte per integer
odd-bitset            5761455       0.2794  Eratosthenes, one bit per odd integer
atkin                 5761455       0.8517  quadratic forms, one byte per integer
segmented             5761455       0.1770  Eratosthenes in 32 KiB blocks

$ build/primes range 90 110
97
101
103
107
109
```

Timings come from one run in a shared cloud sandbox and will differ on your machine.

## Tests

`tests/test_sieve.c` has no dependencies and checks:

- every algorithm against trial division for every limit from 0 to 2000;
- agreement across segment boundaries;
- published values of π(x) up to 10^7 for all algorithms, and π(10^9) for the
  segmented sieve;
- range queries, including empty ranges, single values, and ranges above 10^12;
- bound checking and exact integer square roots up to 2^64 − 1.

## Project layout

```
include/sieve.h      public API
src/eratosthenes.c   classic and odd-only bitset sieves
src/atkin.c          Sieve of Atkin
src/segmented.c      segmented sieve and range queries
src/sieve.c          algorithm registry and shared helpers
src/main.c           command-line tool
tests/test_sieve.c   test suite
```

## Possible extensions

- Add a wheel (mod 30) to skip multiples of 2, 3, and 5.
- Sieve segments in parallel with threads.
- Replace the Atkin loops with the enumeration from the original paper, which
  achieves the sublinear memory and O(n / log log n) operations.
- Measure cache misses with `perf stat` and report them next to the timings.
- Vary the segment size to find the L1/L2 sweet spot on a given CPU.
