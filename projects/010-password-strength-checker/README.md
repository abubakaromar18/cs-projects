# 010 · Password Strength Checker

A small, dependency-free Python CLI that estimates how hard a password is to
guess. It shows the gap between the naive "charset × length" entropy most
strength meters use and a **pattern-aware** estimate that charges only what an
informed attacker would actually need. It also checks the password against
breach lists, offline by default and optionally via Have I Been Pwned using
k-anonymity.

> Defensive and educational. Check your own passwords only. The tool never
> echoes the password and never accepts it as a command-line argument, so it
> stays out of shell history.

## Key CS concepts

- **Information entropy**: `H = L · log2(N)` for a uniformly random string,
  and why human-chosen passwords are far from uniform.
- **Pattern matching**: detectors for dictionary and leet-speak words,
  repeats (regex back-references), alphabet and digit sequences, keyboard
  walks, and years.
- **Dynamic programming**: weighted-interval scheduling picks the
  non-overlapping set of matches that explains the password most cheaply
  (`entropy._select_non_overlapping`).
- **Cryptographic hashing and k-anonymity**: breach lookups compare SHA-1
  digests. The HIBP range API receives only the first 5 hex characters, and
  the match happens locally.
- **Threat modelling**: crack time under an online, throttled attacker
  (100 guesses/s) vs. an offline GPU attack on a fast hash (10¹⁰ guesses/s).
- **Dependency injection for testability**: the HTTP fetcher is a parameter,
  so the tests never touch the network.

## Layout

```
src/password_checker/
  patterns.py   # pattern detectors -> Match(kind, span, bits)
  entropy.py    # naive + pattern-aware entropy, DP match selection
  breach.py     # local SHA-1 breach list + optional HIBP k-anonymity lookup
  scoring.py    # 0-4 score, crack times, feedback
  cli.py        # getpass / stdin input, text or JSON output
  data/         # small bundled common-password and dictionary lists
tests/          # pytest suite (38 tests)
```

## Build, run, test

Requires Python 3.10+. There are no runtime dependencies.

```bash
make dev                 # pip install -e '.[dev]'
make test                # python -m pytest
pwcheck                  # prompts for a password (no echo)
echo 'P4$$w0rd2024' | pwcheck --stdin
pwcheck --stdin --json < my-test-passwords.txt
pwcheck --breach-list company-banned.txt     # extra list, plaintext or SHA-1 hex
pwcheck --online                             # also query HIBP (5 hash chars only)
```

You can also run it without installing: `make run ARGS="--stdin"`.

The exit code is `0` when every password scores at least 3/4 and `1`
otherwise, so you can use the tool in scripts and pre-commit checks.

## Example output

```
$ echo 'P4$$w0rd2024' | pwcheck --stdin
Strength : █     0/4 (very weak)
Length   : 12
Entropy  : 15.2 bits effective (naive charset estimate: 78.8 bits)
Crack    : 3 minutes online (100/s), instant offline (10^10/s)
Breached : not found
Patterns : common-password (leet) 'P4$$w0rd', year '2024'
  - Avoid common words and passwords, even with l33t substitutions.
  - Avoid years and dates; they are easy to guess.

$ echo 'xK9#mQ2$vLp7!zR4' | pwcheck --stdin
Strength : █████ 4/4 (very strong)
Length   : 16
Entropy  : 105.1 bits effective (naive charset estimate: 105.1 bits)
Crack    : centuries online (100/s), centuries offline (10^10/s)
Breached : not found
```

The first password looks strong to a naive meter (78.8 bits). The pattern
estimate shows it is a leet-speak variant of "password" plus a year.

## How scoring works

1. Each detector proposes matches. A dictionary match costs
   `log2(rank+1)`, plus about 1 bit per leet substitution and some bits for
   capitalisation.
2. The DP chooses non-overlapping matches that save the most bits.
   Characters left uncovered are charged at brute-force cost.
3. The effective bits map to a score: <28 → 0, <36 → 1, <60 → 2, <80 → 3,
   otherwise 4. Any breach-list hit forces the score to 0.

## Limitations and possible extensions

- The bundled word lists are deliberately tiny (about 150 passwords and
  80 words). Point `--breach-list` at a larger list, or extend `data/`.
- Add L33t-aware keyboard walks, diagonal keyboard patterns, dates such as
  `12/05/98`, and name lists.
- Use a full guess-enumeration model like zxcvbn, or a Markov model trained
  on leaked passwords.
- Build a small web UI that runs the same logic client-side.
- Add a passphrase generator (diceware) to pair with the checker.
