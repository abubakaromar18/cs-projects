# 042 · Unit Converter

A dependency-free Go CLI that converts between units of **length, mass,
temperature and data size**. It accepts natural queries like `10 km to mi`,
`-40C F` or `5 in in cm`, has an interactive mode, and prints clean,
correctly rounded results.

```
$ convert 10 km to mi
10 km = 6.21371 mi

$ convert -40 C F
-40 C = -40 F

$ convert 5 in in cm          # "in" is both the inch and a separator
5 in = 12.7 cm

$ convert -g 1 TB to bytes
1 TB = 1,000,000,000,000 B

$ convert 100 Mb to MB        # megabits vs megabytes
100 Mb = 12.5 MB

$ convert 1 mb kB
convert: ambiguous unit: "mb" could be MB, Mb
```

Give a value without a target (or pass `-all`) to see it in every unit of its
category:

```
$ convert 0 C
0 C (degree Celsius) =
  273.15  K
      32  F
  491.67  R
```

## Key CS concepts

- **Affine transforms as a uniform model.** Every unit maps onto its
  category's base unit with `base = value·scale + offset`. Linear units
  (km, lb, GiB) have `offset = 0`; temperature scales need the offset. One
  code path converts everything: `to.FromBase(from.ToBase(v))`, so adding a
  unit is O(1) work instead of writing N new pairwise formulas.
- **Floating-point pitfalls.** `0.3048` has no exact binary representation,
  and subtracting a large offset from a nearly equal value causes
  *catastrophic cancellation* (`491.67 °R → °C` gives `5.7e-14` naively).
  The converter snaps sub-epsilon differences to zero and formats output to a
  fixed number of significant digits (`internal/format`).
- **Hash-map lookup with case-sensitive disambiguation.** `Mb`/`MB` and
  `mm`/`Mm` differ only by case. Lookup tries an exact map first, then a
  case-folded map, and accepts the fold only if it is unambiguous.
- **Parsing by search.** A hand-written scanner peels off the leading number
  (sign, fraction, exponent). The rest is tokenised and every separator
  position is tried until both halves resolve to real units, which handles
  multi-word units (`nautical miles`) and the `in`-vs-`in` ambiguity.
- **SI vs IEC prefixes.** `kB = 10³ B` while `KiB = 2¹⁰ B`; bits are ⅛ byte.
- **Testable CLI design.** `main` only calls `run(args, stdin, stdout,
  stderr) int`, so tests drive the whole CLI with in-memory buffers and check
  exit codes.
- **Property and fuzz testing.** Round-tripping through *every pair* of units
  in each category must return the original value, and a Go fuzz target
  checks that the parser never panics.

## Project layout

```
cmd/convert/        CLI entry point, flag handling, REPL (+ tests)
internal/units/     Unit model, registry, built-in catalog, query parser (+ tests, fuzz)
internal/format/    Significant-digit formatting and thousands grouping (+ tests)
```

## Build, run, test

Requires Go 1.22+. No third-party modules.

```sh
make build                 # -> bin/convert
./bin/convert 3 ft to m
make test                  # go test ./...
make cover                 # coverage report
go test -fuzz=FuzzParseQuery -fuzztime=30s ./internal/units
```

### Flags

| Flag | Meaning |
|------|---------|
| `-p N` | significant digits in results (1–17, default 6) |
| `-all` | show the value in every unit of its category |
| `-g` | group thousands with commas |
| `-list [category]` | list units, names and aliases (`length`, `mass`, `temperature`, `data`) |

Run `convert` with no arguments for interactive mode. It reads one query per
line, so it also works with pipes: `printf '1 kg lb\n72 F C\n' | convert`.
Inside the REPL, `list` prints the catalog and `quit` exits.

## Supported units

- **Length:** nm, µm, mm, cm, m, km, in, ft, yd, mi, nmi
- **Mass:** µg, mg, g, kg, t, oz, lb, st, ton (US short ton)
- **Temperature:** K, C, F, R (Rankine). Values below absolute zero are rejected.
- **Data size:** b, B, kB…EB, kb…Eb, KiB…EiB, Kib…Eib

Full names, plurals and common spellings (`kilometers`, `lbs`, `°C`, `micron`)
work too. See `convert -list`.

## Possible extensions

- More categories: volume, area, speed, time, pressure, energy.
- Compound units (`km/h → m/s`) by tracking dimension exponents.
- Temperature *differences* (a 10 °C rise is 18 °F, not 50 °F).
- Arbitrary-precision arithmetic with `math/big.Rat` for exact results.
- Currency conversion with cached exchange rates.
- Shell completion for unit names.
