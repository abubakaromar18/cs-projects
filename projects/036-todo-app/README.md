# 036 · Todo App (Elm)

A TodoMVC-style todo list written in Elm: add, edit (double-click), complete,
delete, filter (All / Active / Completed), toggle-all, clear completed, and
persistence to `localStorage` through ports.

## Key CS concepts

- **The Elm Architecture (TEA)** — a single immutable `Model`, a closed set of
  `Msg` values, a pure `update : Msg -> Model -> (Model, Cmd Msg)` and a pure
  `view : Model -> Html Msg`. All state changes flow one way.
- **Pure functional core, imperative shell** — `src/Todo.elm` holds every
  business rule as plain `TodoList -> TodoList` functions; `src/Main.elm` only
  wires them to events. Effects (focusing an input, saving) are described as
  `Cmd` values that the runtime performs.
- **Opaque types for invariants** — `TodoList` hides its constructor, so ids
  stay unique (a monotonic counter, never reused) and titles are always trimmed
  and non-empty.
- **Algebraic data types & exhaustive pattern matching** — `Filter` and `Msg`
  are custom types; the compiler rejects any `case` that forgets a variant.
- **JSON decoders as validation** — stored data is decoded, not trusted. A
  corrupt blob falls back to an empty list; a stale `nextId` is repaired.
- **Ports** — the boundary between Elm and JavaScript is typed and
  message-based; JS never touches Elm state directly.
- **Virtual DOM keyed diffing** — `Html.Keyed` tracks list items by id.

## Layout

```
src/Todo.elm         pure domain model + JSON codecs
src/Main.elm         TEA: Model, Msg, update, view, save port
index.html           host page; reads localStorage into flags, subscribes to the port
style.css            styling (light/dark)
tests/TodoTests.elm  unit + fuzz tests of the domain
tests/MainTests.elm  update and view tests via Test.Html (no browser)
```

## Build, run, test

```bash
npm install          # installs the elm compiler and elm-test locally
npm test             # 27 tests (unit, fuzz, and HTML-query tests)
npm run build        # writes elm.js (optimized)
npm run dev          # build + serve at http://localhost:3000
```

Or with a global toolchain: `elm make src/Main.elm --output=elm.js`, then open
`index.html` directly in a browser — no server needed.

Example test output:

```
elm-test 0.19.1-revision12
--------------------------
Running 27 tests.

TEST RUN PASSED
Passed:   27
Failed:   0
```

## Possible extensions

- Use `Browser.application` and URL routing so `#/active` selects the filter.
- Subscribe to the `storage` event via an incoming port to sync across tabs.
- Drag-to-reorder, due dates, or tags.
- Undo/redo by keeping a history stack of `TodoList` values (cheap thanks to
  immutability).
- Program-level tests with `elm-program-test`.
