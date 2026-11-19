# wc Clone

A from-scratch implementation of the Unix `wc` utility in portable C11. It counts lines, words, bytes, UTF-8 characters, and the widest line, for any number of files or standard input. Output alignment and `--total` behaviour match GNU coreutils.

```
$ ./wc src/*.c
  121   450  3322 src/counts.c
  150   664  5113 src/main.c
  107   427  3341 src/options.c
   40   125   965 src/report.c
  418  1666 12741 total

$ printf 'h\303\251llo w\303\266rld\n' | ./wc -cmL
     14      12      11

$ ./wc -l --total=only src/*.c
418
```

## CS concepts demonstrated

- **Streaming finite-state machine.** `counts.c` is a small state machine (`in_word`, current column) fed fixed-size 64 KiB chunks. Memory use stays constant however large the input is. Chunk boundaries are invisible: a word or UTF-8 sequence split across two reads is counted once. A unit test proves this by feeding the same text in every chunk size from 1 byte to the full length.
- **UTF-8 decoding by bit patterns.** Every code point starts with a byte that is *not* `10xxxxxx`. Counting non-continuation bytes counts characters in O(1) per byte with no decoder table. Invalid bytes still count as one character each, so the count is always defined.
- **Locale-independent classification.** Whitespace is tested directly (`' '`, `\t`..`\r`) instead of with `isspace()`, so results don't change with `LC_ALL`.
- **Display-width arithmetic.** `-L` advances tabs to the next multiple of 8 (`col += 8 - col % 8`) and resets the column on `\r` / `\f`.
- **Two-pass output formatting.** All inputs are counted before anything prints, so columns can be right-aligned to the widest total. Pipes and terminals can't be sized in advance (checked with `fstat`/`S_ISREG`), so they get GNU's minimum width of 7.
- **Hand-written argument parser.** Handles clustered short flags (`-lw`), long flags, `--total=WHEN`, `--` to end options, and `-` meaning stdin. It keeps no global state, unlike `getopt`'s `optind`, so the tests can call it repeatedly.
- **Unix error conventions.** A missing file prints `wc: name: strerror` to stderr, the other files still count, and the exit status is 1. Usage errors exit 2.

## Layout

```
src/counts.[ch]    streaming counter state machine
src/options.[ch]   command-line parsing
src/report.[ch]    column formatting
src/main.c         glue: open files, aggregate, align, print
tests/test_unit.c  111 unit checks (counter, chunking, parser, formatter)
tests/cli_test.sh  26 end-to-end checks against the built binary
Makefile
```

## Build, run, test

Requires a C11 compiler (`gcc` or `clang`) and `make`.

```sh
make                 # builds ./wc
./wc -lw file1 file2
cat file | ./wc -m
make test            # unit tests + CLI tests
make valgrind        # optional: leak / memory-error check
make clean
```

Test output:

```
./tests/test_unit
111 checks, 0 failures
sh tests/cli_test.sh ./wc
cli: 26 passed, 0 failed
```

## Options

| Flag | Meaning |
|------|---------|
| `-l`, `--lines` | newline count |
| `-w`, `--words` | words (runs of non-whitespace) |
| `-m`, `--chars` | UTF-8 characters |
| `-c`, `--bytes` | bytes |
| `-L`, `--max-line-length` | widest line in display columns |
| `--total=auto\|always\|only\|never` | when to print the total row |
| `--help`, `--version` | |

With no column flags the default is `-lwc`. Columns always print in the order lines, words, chars, bytes, max-line, whatever order the flags were given in.

**Difference from GNU wc:** `-m` always decodes UTF-8. GNU wc follows the locale, so under `LANG=C` it reports bytes for `-m`. `-L` counts every printable code point as one column. It does not do East Asian wide-character widths.

## Possible extensions

- `--files0-from=F` to read NUL-separated file names (pairs well with `find -print0`).
- A fast path for `-c` on regular files that uses `fstat` instead of reading.
- Wide-character display widths for `-L` (CJK, emoji) using a `wcwidth` table.
- Count large files in parallel by splitting them into chunks. Merging the per-chunk results needs the state at each boundary (in-word or not), which is a nice monoid exercise.
- `mmap` input and SIMD newline counting for very large inputs.
