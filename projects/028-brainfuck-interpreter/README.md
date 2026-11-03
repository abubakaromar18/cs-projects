# Brainfuck Interpreter (C)

A small, fast Brainfuck interpreter written in C11. It compiles source code into a compact **intermediate representation (IR)**, runs an **optimizing pass** over it, and executes the result on a bounds-checked virtual machine. A differential fuzz test checks that every optimization level behaves exactly like the naive interpreter.

```
source.bf ──lex──▶ tokens ──match [ ]──▶ IR ──optimize──▶ IR' ──VM──▶ output
```

## Features

- All 8 commands. Everything else is a comment.
- Three optimization levels:

| Level | What it does | Example |
|---|---|---|
| `-O0` | One IR op per command. This is the reference interpreter. | `+++` → `ADD 1, ADD 1, ADD 1` |
| `-O1` | Run-length folding. Runs that cancel out disappear. | `+++--` → `ADD +1`, `>><` → `MOVE 1` |
| `-O2` | Rewrites loop idioms into constant-time ops. | `[-]` → `SET 0`, `[>]` → `SCAN 1`, `[->++>+<<]` → `MULADD [+1]*2, MULADD [+2]*1, SET 0` |

- Jumps are linked ahead of time, so `[` and `]` are O(1) and don't scan for the matching bracket.
- Compile errors give line and column, for example `prog.bf:3:14: error: unmatched ']'`.
- Runtime safety: the tape is bounds-checked, there's an optional step limit, and output errors are reported.
- Configurable tape size and **EOF behaviour**: store 0, store 255 (−1), or leave the cell unchanged.
- `--dump` prints the compiled IR, with loop bodies indented.
- I/O goes through a callback struct, so the engine also runs against in-memory buffers. The tests use this.

## CS concepts demonstrated

- **Compiler pipeline**: lexing, then syntax checking (bracket matching with a stack), then IR generation and back-patching jump targets.
- **Intermediate representations**: a richer instruction set (`SET`, `SCAN`, `MULADD`) than the source language. This is the same idea that real compilers use.
- **Peephole and idiom optimization**: run-length folding, and pattern-matching loop bodies. A balanced loop whose loop cell changes by ±1 runs exactly `cell` (or `256 − cell`) times. That makes its effect on every other cell a multiplication, so the whole loop collapses to a few ops.
- **Modular arithmetic**: cells are bytes, and the multiply rewrite depends on wrap-around mod 256. An incrementing loop cell flips the factor's sign.
- **Virtual machines**: a fetch–decode–execute loop over an op array.
- **Semantics preservation and differential testing**: thousands of random programs, weighted toward optimizable idioms, run at all three levels and must produce byte-identical output and final pointer positions.

## Layout

```
include/bf.h      public API: compile, run, dump, I/O helpers
src/compile.c     lexer, bracket matcher, IR emitter + optimizer
src/vm.c          interpreter loop, file and memory I/O adapters
src/main.c        command-line front end
tests/test_bf.c   unit tests + differential fuzzing
tests/cli_test.sh end-to-end tests of the bf binary
examples/         hello.bf, reverse.bf, bench.bf
```

## Build, run, test

Requirements: a C11 compiler and `make`. Linux and macOS both work. The CLI uses `getopt_long`.

```sh
make                      # builds build/bf
make test                 # unit + fuzz tests, then CLI tests
make sanitize             # tests under AddressSanitizer + UBSan
make valgrind             # leak check
make examples             # run the example programs
make bench                # compare -O0 / -O1 / -O2
```

Usage:

```
bf [options] [FILE]
  -e, --expr CODE     program text given on the command line
  -O, --opt LEVEL     optimization level 0, 1 or 2 (default 2)
  -t, --tape CELLS    tape size in cells (default 30000)
      --eof MODE      ',' at end of input: zero | neg | keep (default zero)
  -m, --max-steps N   abort after N instructions
  -d, --dump          print the compiled IR and exit
  -s, --stats         print instruction counts to stderr
```

## Example output

```
$ ./build/bf examples/hello.bf
Hello World!

$ echo hello | ./build/bf examples/reverse.bf

olleh

$ ./build/bf -e '+]'
<expr>:1:2: error: unmatched ']'

$ ./build/bf -d examples/hello.bf | head -9
    0  ADD    +8
    1  JZ     -> 20
    2    MOVE   1
    3    ADD    +4
    4    MULADD [+1] += cell * 2
    5    MULADD [+2] += cell * 3
    6    MULADD [+3] += cell * 3
    7    MULADD [+4] += cell * 1
    8    SET    0
```

The benchmark has three nested 255-iteration loops. Its innermost `[>+<-]` becomes a single `MULADD`:

```
$ make bench
bf: -O0  68 ops  83298852 steps executed
real    0m0.131s
bf: -O1  37 ops  83298758 steps executed
real    0m0.101s
bf: -O2  27 ops  456719 steps executed
real    0m0.002s
```

On "Hello World!", `-O2` runs 183 instructions where `-O0` runs 906.

## Design notes

- **Bounds checks at `-O1` and above apply to net movement.** `-O0` faults on a transient excursion like `<<>>` at cell 0. Folded code moves only by the net amount (here zero), so it does not fault. Folded code never faults where `-O0` doesn't, and when `-O0` succeeds every level produces identical results. The fuzz test checks exactly this.
- `MULADD` does nothing when the loop cell is 0. The original loop wouldn't have run in that case, so it can't touch (or fault on) the target cell either.
- Multiply loops may reach at most ±64 cells. Larger bodies, and any loop containing I/O or a nested loop, are compiled normally.

## Possible extensions

- **Offset addressing**: fold `>+>+<<` into `ADD [+1], ADD [+2]` with no pointer movement at all.
- **Computed-goto dispatch**: GCC's `&&label` threads the dispatch for a faster VM.
- **JIT or ahead-of-time backends**: emit C or x86-64 machine code from the same IR.
- **Debugger**: breakpoints with `#`, single-stepping, and a tape viewer.
- **Constant propagation**: track known cell values at program start, which are all zero, and drop dead loops.
