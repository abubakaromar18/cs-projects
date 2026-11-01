# Password Generator

`passgen` is a small Rust command-line tool that makes secure random passwords
and diceware-style passphrases. For every result it can also report the exact
**entropy**: the number of bits of randomness behind it, with no rough
guessing. Every random choice is uniform, so no character or word comes up
more often than another, and the randomness comes from the operating system's
cryptographically secure generator (CSPRNG).

```
$ passgen -e
O~\ho2~Z^+:p85K.w$kS
entropy: 130.9 bits (very strong) — brute force at 1e11 guesses/s: longer than the age of the universe
pool: 94 chars from [lowercase, uppercase, digits, symbols]

$ passgen -n 3 -l 12 --no-symbols --no-ambiguous
zjw2GCDmSbD5
fnKi57dJeH6k
KY4znyZSNyLG

$ passgen phrase -e
barber-essay-tamale-juice-adapt-trail
entropy: 61.6 bits (strong) — brute force at 1e11 guesses/s: ~204.3 days
wordlist: 1234 words

$ passgen phrase -w 4 --case title -s ' ' --digit
Star Bamboo Vinyl Ghost9
```

Passwords and passphrases go to **stdout** and reports go to **stderr**, so
`passgen | pbcopy` copies only the password.

## Key CS concepts

| Concept | Where | What it shows |
|---|---|---|
| **CSPRNG vs PRNG** | `src/rng.rs` | `OsRng` gets its randomness from the operating system. `SeededRng` (xorshift64\*) gives repeatable output and is used only in tests and with `--seed`. Both implement the same `RandomSource` trait. |
| **Modulo bias and rejection sampling** | `RandomSource::below` | `x % n` favours small values when `n` doesn't divide 2³². The fix is to throw away draws from the leftover range at the top. A unit test feeds in exactly the value that must be rejected. |
| **Fisher–Yates shuffle** | `RandomSource::shuffle` | Shuffles a list so that every ordering is equally likely. |
| **Uniform sampling with constraints** | `PasswordGenerator::generate` | To require at least one character from each class, it rejects strings that miss a class. The usual "one from each class, then shuffle" method is *biased*. A statistical test checks that each of the 6 valid outputs comes up 1/6 of the time. |
| **Inclusion–exclusion** | `entropy::all_classes_probability` | Computes the exact chance that a random string contains every class. That gives the exact entropy, `L·log₂N + log₂P`, without overflowing on huge numbers like N^L. |
| **Entropy and strength** | `src/entropy.rs` | Strength is measured on the *generator* (log₂ of how many outputs are possible), not on what one password looks like. Also gives a crack-time estimate. |
| **Chi-squared test** | `rng.rs` tests | Checks statistically that `below` spreads its results evenly. |
| **Trait objects and generics** | `main.rs` `DynRng` | `RandomSource` has generic methods, so it can't be used as a trait object directly. A small wrapper trait lets the program choose the generator while it runs. |
| **Fewer dependencies** | `cli.rs` | The command-line parser is written by hand. The only dependency is `getrandom`. |

## Project layout

```
023-password-generator/
├── Cargo.toml
├── src/
│   ├── main.rs        # CLI entry: sends output to stdout/stderr, sets exit codes
│   ├── lib.rs         # library root
│   ├── cli.rs         # argument parser + usage text
│   ├── rng.rs         # OsRng, SeededRng, unbiased below/choose/shuffle
│   ├── charset.rs     # character classes, look-alike filter, exclusions
│   ├── password.rs    # random-character password generator
│   ├── passphrase.rs  # word-based passphrase generator, wordlist parsing
│   ├── entropy.rs     # entropy math, strength labels, crack time
│   └── wordlist.txt   # 1,234 common words, 3–8 letters, built in with include_str!
└── tests/
    └── cli.rs         # end-to-end tests that run the compiled binary
```

## Build, run, test

You need Rust 1.70 or newer (stable).

```bash
cargo build --release
./target/release/passgen --help

cargo run -- -l 32 -n 5            # five 32-character passwords
cargo run -- phrase -w 7 -e        # seven-word passphrase plus entropy report

cargo test                         # 33 unit tests + 7 end-to-end tests
cargo clippy --all-targets         # lint (no warnings)
```

## Options

| Mode | Option | Meaning |
|---|---|---|
| both | `-n, --count N` | how many to generate |
| both | `-e, --entropy` | print entropy, strength and crack time to stderr |
| both | `--seed U64` | repeatable output that is **not secure**, for testing only (prints a warning) |
| password | `-l, --length N` | length (default 20, max 4096) |
| password | `--no-lower/--no-upper/--no-digits/--no-symbols` | turn off a character class |
| password | `--no-ambiguous` | leave out look-alike characters ``Il1\|O0o`'"`` |
| password | `--exclude CHARS` / `--custom CHARS` | remove characters, or add your own class |
| password | `--no-require` | don't require one character from each class |
| phrase | `-w, --words N` | number of words (default 6) |
| phrase | `-s, --separator S` | text between words (default `-`) |
| phrase | `--case lower\|upper\|title` | letter case for the words |
| phrase | `--digit` | add a random digit to one word |
| phrase | `--wordlist FILE` | your own list: one word per line, or the diceware/EFF `11111<TAB>word` format |

The exit code is `0` on success and `2` on bad input. Error messages say what
to change, for example `increase --length or pass --no-require`.

## How the entropy numbers work

* A password of length *L* drawn freely from *N* characters has
  `L · log₂ N` bits of entropy. The default 20 characters from 94 gives
  about 131 bits.
* Requiring every class removes the strings that miss one. The generator
  stays uniform over the strings that remain, so the entropy is exactly
  `log₂(N^L · P)`, where *P* comes from inclusion–exclusion. For 20
  characters this costs less than 0.5 bits.
* A passphrase of *w* words from a list of *W* words has `w · log₂ W` bits.
  The built-in list gives about 10.27 bits per word, so the default 6 words
  give about 61.6 bits. `--digit` adds `log₂(10·w)` bits.
* Crack times assume 10¹¹ guesses per second (a GPU attacking a fast hash)
  and that, on average, an attacker searches half of all possibilities.

## Possible extensions

* `--min-digits`/`--min-symbols` counts (rejection still works; add a
  generalised inclusion–exclusion for the entropy).
* Pronounceable passwords from a Markov chain of letter pairs, with the
  entropy calculated from the chain.
* Copy to the clipboard and clear it after a timeout.
* Wipe secrets from memory with the `zeroize` crate.
* A strength checker for passwords people chose themselves, using
  zxcvbn-style pattern matching (a different problem from rating random ones).
* Compile to WebAssembly for an offline browser page.
