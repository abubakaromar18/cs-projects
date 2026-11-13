# Pebble — a tiny esoteric language

Pebble is a small stack-based esoteric language, designed from scratch
and implemented in Python with a hand-written **lexer**, a
**recursive-descent parser**, and a **tree-walking interpreter**. Almost
every instruction is one character, so programs look like line noise,
but the language has enough to write FizzBuzz, recursive factorial,
prime sieves and input filters.

```
"Hello, World!\n" [,] $
```

## Key CS concepts

- **Language design**: choosing a minimal instruction set that is still
  Turing-complete (a stack, unbounded integers, and a while loop are enough).
- **Lexical analysis**: a single-pass scanner with one character of
  lookahead, grouping multi-character tokens (numbers, strings, char
  literals, register names) and tracking line and column for every token.
- **Formal grammar and parsing**: the grammar is LL(1), so the parser
  is a set of small recursive-descent methods, one per rule. It
  checks bracket matching and catches undefined words before the
  program runs.
- **Abstract syntax trees**: loops, conditionals and definitions become
  nested nodes, and `--ast` prints the tree.
- **Interpretation**: a tree-walking evaluator with a data stack,
  registers and a dispatch table of instructions.
- **Name resolution and hoisting**: words can be called before they
  are defined, and recursion works.
- **Safety limits**: the step limit and call-depth limit turn infinite
  loops and runaway recursion into clean Pebble errors instead of hangs
  or Python crashes.
- **Error reporting**: syntax and runtime errors give the `line:col`
  where they happened.

## The language

The machine has one stack of unbounded integers, 26 registers `a`–`z`
(all starting at 0), and up to 26 user-defined words `A`–`Z`.

| Syntax | Effect (stack: before → after) |
|---|---|
| `123` | push the integer 123 |
| `'c` | push the character code of `c` (`'\n` also works) |
| `"text"` | push `0`, then the characters in reverse, so the first char is on top |
| `+ - * / %` | `a b → a∘b` (floor division and modulo; dividing by zero is an error) |
| `= < >` | `a b → 1` if the comparison is true, else `0` |
| `!` | logical not: `0 → 1`, anything else `→ 0` |
| `:` `$` `\` | dup `a → a a`, drop `a →`, swap `a b → b a` |
| `@` `^` | rot `a b c → b c a`, over `a b → a b a` |
| `.` `,` | pop and print as a number / as a character |
| `?` | read one character (`-1` at end of input) |
| `&` | read an integer, skipping whitespace (`-1` at end of input) |
| `~x` | pop into register `x` |
| `x` | push the value of register `x` |
| `[ … ]` | **while** the top of the stack is non-zero (it is checked, not popped), run the body |
| `{ … }` | **if**: pop; run the body once if the value was non-zero |
| `(F … )` | define word `F` (top level only) |
| `F` | call word `F` |
| `# …` | comment to the end of the line |

### Idioms

- **Print a string**: `"hi\n" [,] $`. The loop prints characters until
  it reaches the 0 terminator, and `$` drops the terminator.
- **Counting loop**: keep the condition on top of the stack. Drop it
  at the start of the body and recompute it at the end:
  `1~i i 11 < [ $ i . i 1 + ~i i 11 < ] $`
- **if/else**: `cond : { $ then… 1 } ! { $ else… }`. The "then" branch
  leaves a 1, and `!` turns it into 0, so the "else" branch is skipped.

## Build, run, test

Requires Python 3.10+. There are no runtime dependencies.

```bash
make dev                         # pip install -e '.[dev]'  (installs `pebble` + pytest)
make test                        # run the test suite (73 tests)
make demo                        # run every example

pebble examples/fizzbuzz.pbl     # run a file
pebble -e '6 7 * .'              # run inline code
pebble -e '1 2 3' --stack        # show the final stack
pebble examples/primes.pbl --ast # print the syntax tree
pebble --tokens -e "'A ,"        # print the token stream
pebble                           # REPL (state persists between lines)
echo "3 4 5" | pebble examples/sum.pbl
```

You can run it without installing: `PYTHONPATH=src python3 -m pebble …`.

## Example output

```
$ pebble examples/factorial.pbl
0! = 1
1! = 1
2! = 2
...
10! = 3628800

$ pebble examples/primes.pbl
2 3 5 7 11 13 17 19 23 29 31 37 41 43 47

$ pebble -e '1 2 3 + + 0 /'
<eval>: runtime error at 1:13: division by zero

$ pebble -e '[ 1'
<eval>: syntax error at 1:1: '[' is never closed (expected ']')
```

Recursive factorial (`examples/factorial.pbl`):

```
(F : 1 > : { $ : 1 - F * 1 } ! { $ 1 })
```

## Layout

```
src/pebble/
  lexer.py        source text → tokens (with line/col)
  parser.py       tokens → AST, recursive descent + static checks
  ast.py          node classes and the --ast pretty-printer
  interpreter.py  tree-walking evaluator, instruction table, limits
  errors.py       PebbleSyntaxError / PebbleRuntimeError
  cli.py          file / -e / --tokens / --ast / REPL front end
examples/         hello, fizzbuzz, factorial, fibonacci, primes, cat, sum
tests/            lexer, parser, interpreter, examples + CLI tests
```

## Possible extensions

- Compile the AST to a flat bytecode with jump instructions and run it
  on a loop-based VM. This removes Python recursion and is faster.
- Add local variables or a return stack so words don't share global
  registers.
- Write a Brainfuck-to-Pebble translator to show that Pebble is
  Turing-complete.
- Add a step debugger (`--trace`) that prints each instruction and the stack.
- Add an optimiser pass that folds constants (`2 3 +` → `5`) and removes
  dead `0 { … }` blocks.
- Make it two-dimensional, like Befunge, where `>` `<` `^` `v` steer the
  instruction pointer.
