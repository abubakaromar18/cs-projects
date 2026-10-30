---
title: How This Blog Renders Markdown
date: 2026-10-12
summary: A tiny, safe Markdown renderer built as a line-by-line state machine.
tags: [parsing, security]
---

Instead of pulling in a large library, this blog uses a ~150-line renderer.

## Blocks are a state machine

Each line either *continues* the current block (a paragraph, list or quote) or
*closes* it and opens a new one. Fenced code is a special state where nothing is
interpreted until the closing fence:

```ts
if (code) {
  if (/^```\s*$/.test(line)) emitCodeBlock();
  else code.lines.push(line);
  continue;
}
```

## Escape first, then format

> Never build HTML out of untrusted text without escaping it.

Every line is HTML-escaped *before* inline rules like `**bold**` run, and links
are only allowed for `http(s)`, `mailto` and relative URLs. That makes
`<script>` tags and `javascript:` links inert.

1. Extract code spans
2. Escape everything else
3. Apply inline formatting
4. Re-insert code spans
