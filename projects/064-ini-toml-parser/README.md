# 064 · INI/TOML Parser

A dependency-free Rust library and CLI (`confparse`) that parses **TOML** (a practical
subset) and classic **INI** files into a typed document tree, with **rustc-style error
messages** that point at the exact line and column.

```
$ confparse examples/broken.toml
error: duplicate key `port`
  --> examples/broken.toml:4:1
  |
4 | port = 8080
  | ^
  = note: first defined on line 3
```

## Features

**TOML**
- Bare, quoted (`"a b"`, `'lit'`) and dotted keys (`a.b.c = 1`)
- `[tables]`, `[nested.tables]` and `[[arrays.of.tables]]`
- Basic strings with all escapes (`\n`, `\t`, `\"`, `\uXXXX`, `\UXXXXXXXX`, …), literal
  strings, and both multi-line forms (`"""` with line-ending backslash, `'''`)
- Integers (`1_000`, `0xff`, `0o17`, `0b101`) with overflow detection, floats
  (`3.14`, `6.02e23`, `inf`, `nan`), booleans
- Arrays (mixed types, multi-line, comments, trailing commas) and inline tables
- CRLF line endings and a leading BOM

**INI**
- `[section]` headers, `key = value` or `key: value`, `;` and `#` comments
- Keys may contain spaces; quoted values keep surrounding whitespace
- Inline comments only after whitespace, so `url = http://x/#frag` survives

**Errors detected** (each with position, a source excerpt, a caret, and often a note):
duplicate keys, redefined tables, values used as tables, unterminated strings, newlines
in single-line strings, invalid escapes, malformed or overflowing numbers, unquoted
strings (with a "did you mean `"hello"`" hint), missing `=`, trailing garbage, unclosed
arrays/inline tables, multi-line inline tables.

## CS concepts demonstrated

- **Recursive-descent parsing** of a context-sensitive grammar without a separate lexer
  (`1979` is an integer as a value but a bare key on the left of `=`).
- **Source-position tracking**: errors carry a character offset that is mapped back to a
  1-based line/column and rendered with tab-aware caret alignment.
- **Semantic validation during construction**: a symbol table of defined tables and keys
  (with array-of-table indices in their identity) catches redefinitions and reports
  where the first definition was.
- **Tree navigation with mutable borrows** in Rust (walking and creating nested tables).
- **Lexical validation of numeric literals** (digit grouping, leading zeros, radix prefixes,
  exponent syntax) and checked conversion to `i64`.
- A small **JSON serializer** for the resulting tree.

## Layout

```
src/
  lib.rs      public API: parse_toml, parse_ini, parse, dialect_for_path
  parser.rs   the recursive-descent parser for both dialects (+ number unit tests)
  value.rs    Value / Table model, typed accessors, dotted-path lookup, JSON output
  error.rs    ErrorKind, ParseError and the rustc-style renderer
  main.rs     CLI front end
tests/
  integration.rs   parsing + exact error position/message tests
  cli.rs           runs the compiled binary
examples/          app.toml, legacy.ini, broken.toml
```

## Build, run, test

Requires a Rust toolchain (edition 2021, no external crates).

```sh
cargo build --release
cargo run -- examples/app.toml              # print as JSON
cargo run -- --get server.port examples/app.toml
cargo run -- examples/legacy.ini            # dialect guessed from extension
cargo run -- --ini --check some.conf        # validate only
cat config.toml | cargo run -- -            # read stdin
cargo test                                  # 29 tests: unit, integration, CLI, doctest
```

Exit codes: `0` success, `1` parse error or missing key, `2` usage / I/O error.

### Library usage

```rust
use confparse::{parse_toml, Value};

let doc = Value::Table(parse_toml("[server]\nport = 8080\n")?);
assert_eq!(doc.get_path("server.port").and_then(Value::as_integer), Some(8080));
```

### Example output

```
$ confparse --get database examples/app.toml
{
  "pool": {
    "max": 10,
    "min": 1
  },
  "url": "postgres://localhost/demo"
}

$ echo 'name = hello' | confparse -
error: unexpected character `h`, expected a value
  --> <stdin>:1:8
  |
1 | name = hello
  |        ^
  = note: strings must be quoted, e.g. "hello"
```

## Limitations / possible extensions

- TOML date-times (`1979-05-27T07:32:00Z`) are not supported yet — add a `Datetime` value.
- TOML forbids re-opening a table created implicitly by dotted keys with a `[header]`;
  this parser accepts it.
- Collect *multiple* errors per run (error recovery by skipping to the next line).
- A serializer back to TOML/INI that preserves comments and ordering (a "lossless" CST).
- Run the official `toml-test` suite and a `cargo fuzz` target against the parser.
- INI extensions: `${var}` interpolation, multi-line continuation values.
