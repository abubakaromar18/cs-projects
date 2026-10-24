# Calculator Parser

A command-line calculator built from scratch on a **hand-written lexer** and a
**recursive descent parser**. It turns text like `-2^2 + 3! * max(1, 4)` into
an abstract syntax tree, then evaluates it with a tree-walking interpreter. It
handles operator precedence, associativity, variables, functions and error
messages that point at the problem.

No parsing libraries and no `eval()`: every stage is written out in plain Python.

## Features

- Operators: `+ - * / // %`, exponent `^` (or `**`), postfix factorial `!`, unary `+`/`-`, parentheses
- Variables and chained assignment: `x = y = 2`, plus `ans` for the last result
- Built-in functions: `sqrt abs sin cos tan asin acos atan ln log exp floor ceil round min max`
- Constants: `pi`, `e`, `tau`
- Error messages with a caret under the bad position, for lex, parse and runtime errors
- REPL commands to inspect the pipeline: `:tokens`, `:ast`, `:vars`
- Hostile input is rejected with an error instead of crashing (a nesting limit and recursion guards)

## CS concepts demonstrated

| Concept | Where |
|---|---|
| Lexical analysis (a scanner that builds tokens) | `src/calc/lexer.py` |
| Context-free grammar written in EBNF | docstring of `src/calc/parser.py` |
| Recursive descent parsing, one method per grammar rule | `Parser` in `parser.py` |
| Precedence that comes from how the rules nest | `additive → multiplicative → unary → power → postfix → primary` |
| Left associativity with loops instead of left recursion | `additive`, `multiplicative` |
| Right associativity with recursion | `power` (`2^3^2 = 512`), `assignment` |
| One-token lookahead (LL(1)) | `assignment` decides between `x = …` and an expression |
| Abstract syntax trees made of immutable nodes | `src/calc/ast.py` |
| Tree-walking interpretation (post-order traversal) | `src/calc/evaluator.py` |
| Structural pattern matching over AST nodes | `match` in `eval_node` / `to_sexpr` |
| Environments for keeping state between lines | `Evaluator.variables` |
| Error reporting with source positions | `src/calc/errors.py` |

### The grammar

```
statement      := assignment EOF
assignment     := IDENT "=" assignment | additive
additive       := multiplicative (("+" | "-") multiplicative)*
multiplicative := unary (("*" | "/" | "//" | "%") unary)*
unary          := ("+" | "-") unary | power
power          := postfix ("^" unary)?
postfix        := primary "!"*
primary        := NUMBER | IDENT "(" arguments? ")" | IDENT | "(" assignment ")"
arguments      := assignment ("," assignment)*
```

The deeper a rule sits, the tighter it binds. Placing `unary` *above* `power`
is what makes `-2^2` equal `-4` (as in maths and Python). Making the right
operand of `^` a `unary` lets `2^-1` work, and makes `^` right-associative.

## Build, run, test

Requires Python 3.10+ (it uses `match`). There are no runtime dependencies.

```bash
make dev                    # editable install + pytest
make test                   # run the test suite (97 tests)
make run ARGS="2+3*4"       # run from source without installing
calc                        # start the REPL (after install)
calc --ast "1 + 2 * 3"      # print the parse tree and the result
```

Without `make`: `pip install -e '.[dev]'`, then `python -m pytest`, or
`PYTHONPATH=src python -m calc`.

## Example session

```
$ calc --ast "-2^2 + 3! * max(1, 4)"
(+ (neg (^ 2 2)) (* (! 3) (max 1 4)))
20

$ calc "sqrt(2) * (1 + 2"
sqrt(2) * (1 + 2
                ^
Parse error: expected ')', found end of input

$ calc
calc — type :help for help, :quit to exit
> r = 3
3
> pi * r^2
28.2743338823
> :tokens 2**x!
NUMBER(2) CARET(**) IDENT(x) BANG(!) EOF
> :ast a = b = 2^3^2
(= a (= b (^ 2 (^ 3 2))))
> 1 / (r - 3)
1 / (r - 3)
  ^
Eval error: division by zero
```

## Tests

- `test_lexer.py`: number formats (`.5`, `1e3`, `2.5E-2`), two-character operators, positions, bad characters
- `test_parser.py`: about 20 tree shapes checked as S-expressions (precedence, associativity, unary vs power, factorial), syntax error positions, the nesting limit
- `test_evaluator.py`: values, a randomized check against Python's own `+ - *` precedence, variables, every runtime error path
- `test_cli.py`: one-shot mode, the `--ast` flag, exit codes, REPL commands and a scripted REPL session

## Possible extensions

- User-defined functions: `f(x) = x^2 + 1` (store an AST plus a parameter list as a closure)
- Implicit multiplication (`2x`, `3(4+1)`), which needs care in the grammar to stay unambiguous
- Rewrite the expression levels as a **Pratt parser** (precedence climbing) and compare it with this one
- Constant folding and algebraic simplification passes over the AST
- Compile the AST to bytecode for a small stack VM instead of walking the tree
- Exact rational arithmetic with `fractions.Fraction`, or arbitrary precision with `decimal`
- Symbolic differentiation: `d/dx` as a recursive transform over the AST
