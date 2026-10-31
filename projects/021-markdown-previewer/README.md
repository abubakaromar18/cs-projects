# 021 · Markdown Previewer

A live, split-pane Markdown editor built with **React**. Type on the left and the
rendered document updates on the right. You can export a standalone `.html`
page, copy the HTML, or open and save `.md` files.

The Markdown engine is **written from scratch** (no `marked` or `remark`). It is a
small parser for a sizeable subset of CommonMark plus GitHub Flavored Markdown, with
a renderer that escapes all output.

## Features

- Live preview with three layouts: **Split**, **Editor** and **Preview**. Stacks vertically on narrow screens.
- Toolbar and shortcuts: **Ctrl/⌘+B** bold, **Ctrl/⌘+I** italic, **Ctrl/⌘+K** link, **Tab / Shift+Tab** indent.
  Formatting toggles, so pressing it again removes it.
- **Export HTML**: downloads a self-contained page with embedded CSS, named after the first `# heading`.
- **Copy HTML**, **Open .md**, **Save .md** and **Reset** to the sample document.
- Autosaves to `localStorage` (debounced). Still works if storage is blocked.
- Proportional scroll sync between the panes.
- Word count, character count and reading time.
- Light and dark themes that follow the system setting.

### Supported Markdown

| Blocks | Inline |
| --- | --- |
| ATX (`#`) and setext (`===`) headings with unique `id`s | `*em*`, `**strong**`, `***both***`, `_under_` |
| Paragraphs, hard breaks (two spaces or `\`) | `~~strikethrough~~` (GFM) |
| Fenced (```` ``` ```` / `~~~`) and indented code blocks | `` `code spans` `` with any backtick count |
| Nested block quotes with lazy continuation | `[links](url "title")`, `<autolinks>`, `<emails@x.y>` |
| Bullet and ordered lists (nested, tight or loose, custom start) | `![images](src)` |
| GFM task lists `- [x]` and tables with alignment | Backslash escapes |
| Thematic breaks (`---`, `***`, `___`) | |

Raw HTML is **intentionally not supported**. It is shown as text.

## CS concepts demonstrated

- **Two-phase parsing.** `parseMarkdown` (block structure) → AST → `renderHtml`. The
  AST is a real intermediate representation, so one parse feeds the preview, the
  export title and the stats.
- **Recursive descent over lines.** Container blocks (quotes, list items) strip their
  prefix and call `parseBlocks` again on the remaining lines. Nesting to any depth
  comes from the recursion. List items use column arithmetic (`contentOffset`) to
  decide what belongs to them.
- **The CommonMark delimiter algorithm.** Emphasis is resolved in a second pass
  over a list of *delimiter runs*. Each run is classified as left-/right-flanking,
  and each closer is paired with the nearest compatible opener, including the
  "rule of 3". This handles cases like `*a **b** c*` and `**foo*` correctly, which
  regex-based converters usually get wrong.
- **Scanners with balanced matching.** Code spans need equal-length backtick runs.
  Link labels need nested brackets and link destinations need balanced parentheses.
- **Output encoding as a security boundary.** Every text node is HTML-escaped, and
  every URL goes through an allow-list of schemes. Control characters are stripped
  first, so `java\tscript:` cannot bypass the check. That is what makes
  `dangerouslySetInnerHTML` safe here. `tests/security.test.js` contains XSS payloads.
- **React rendering model.** Controlled inputs, `useMemo` to avoid re-parsing, and
  `useDeferredValue` so typing stays responsive while the preview re-renders at
  lower priority. `useLayoutEffect` restores the text selection after a
  programmatic edit. There is also a custom `useLocalStorage` hook.
- **Pure functions for editing.** Toolbar actions (`toggleWrap`, `toggleLinePrefix`,
  `insertLink`) are pure `(text, selection) → (text, selection)` transforms, kept
  separate from the DOM so they can be unit-tested.

## Project structure

```
src/
  markdown/
    block.js      block parser (lines → block AST)
    inline.js     inline scanner + emphasis delimiter algorithm
    render.js     AST → HTML, heading slugger
    escape.js     escapeHtml, sanitizeUrl
    index.js      public API: markdownToHtml, extractTitle, documentStats
  lib/
    editing.js    pure text-editing transforms
    exportHtml.js standalone document builder, file download/read helpers
  hooks/useLocalStorage.js
  components/     Toolbar, Editor, Preview, StatusBar
  App.jsx         state, wiring, scroll sync
tests/            Vitest + Testing Library (98 tests)
```

## Build, run and test

Requires Node 18.18+.

```bash
npm install
npm run dev       # http://localhost:5173
npm test          # run the test suite once
npm run build     # production build in dist/
npm run preview   # serve the production build
```

Example test output:

```
 ✓ tests/blocks.test.js (28 tests)
 ✓ tests/inline.test.js (29 tests)
 ✓ tests/security.test.js (20 tests)
 ✓ tests/lib.test.js (11 tests)
 ✓ tests/App.test.jsx (10 tests)
 Test Files  5 passed (5)
      Tests  98 passed (98)
```

## Example

```js
import { markdownToHtml } from './src/markdown/index.js';

markdownToHtml('# Hi\n\n- [x] *done*\n- [ ] [link](https://example.com)');
```

```html
<h1 id="hi">Hi</h1>
<ul class="contains-task-list">
<li class="task-list-item"><input type="checkbox" disabled checked /> <em>done</em></li>
<li class="task-list-item"><input type="checkbox" disabled /> <a href="https://example.com">link</a></li>
</ul>
```

## Possible extensions

- Syntax highlighting for fenced code (a small tokenizer per language, or Prism).
- Reference-style links (`[text][ref]` plus definitions) and footnotes.
- A table-of-contents sidebar built from the heading AST.
- Incremental re-parsing: re-parse only the blocks touched by an edit.
- Opt-in raw HTML using an allow-list sanitizer.
- Scroll sync by source line instead of by proportion (store line numbers in the AST).
- Run the CommonMark spec test suite and track the pass rate.
