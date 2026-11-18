# Code Snippet Manager

A personal code snippet library built with **Next.js (App Router) + TypeScript**. Save snippets with tags, find them instantly with ranked search-as-you-type, and read them with syntax highlighting. The highlighter and search engine are written from scratch, with no libraries.

![Level: Starter](https://img.shields.io/badge/level-starter-green) ![Area: Full-Stack Apps](https://img.shields.io/badge/area-full--stack-blue)

## Features

- **CRUD** for snippets (title, description, language, code, tags) via pages and a JSON REST API
- **Tags**: normalized (`"Data Structures"` → `data-structures`), shown as a tag cloud with counts, multi-select filtering (AND)
- **Search**: TF-IDF ranking with field weights, prefix matching on the word you're typing, camelCase-aware (`debounce` finds `useDebounce`)
- **Syntax highlighting** for JavaScript, TypeScript, Python, Go, Rust, Bash, SQL and JSON, with line numbers and light/dark themes
- Copy-to-clipboard, a live preview while editing, Tab-to-indent in the editor, and filters that are kept in the URL so views can be bookmarked

## CS concepts demonstrated

| Concept | Where |
| --- | --- |
| **Lexical analysis**: a regex-driven lexer with ordered rules and sticky (`/y`) regexes; lossless tokenization | `lib/highlight.ts` |
| **Inverted index**: term → postings (doc → weighted term frequency) | `lib/search.ts` `buildIndex` |
| **TF-IDF ranking** with per-field weights (title 5, tags 4, description 2, code 1) | `lib/search.ts` `search` |
| **Binary search** over a sorted term list for O(log T) prefix expansion | `lib/search.ts` `expandPrefix` |
| **Atomic writes** (write temp file → `rename`) and an **async mutex** that prevents lost updates | `lib/store.ts` |
| **Input validation** at the trust boundary, collecting all errors | `lib/validation.ts` |
| **XSS safety**: tokens render as React text nodes, never as `innerHTML` | `components/CodeBlock.tsx` |
| Server vs. Client Components, dynamic route params, Route Handlers | `app/` |

## Project layout

```
app/
  page.tsx                  # list + search (server loads data, client filters)
  new/page.tsx              # create form
  snippets/[id]/page.tsx    # detail view
  snippets/[id]/edit/       # edit form
  api/snippets/route.ts     # GET (search) / POST
  api/snippets/[id]/route.ts# GET / PUT / DELETE
components/                 # CodeBlock, SnippetBrowser, SnippetForm, buttons
lib/                        # highlight, search, tags, validation, store, seed
tests/                      # Vitest unit + route-handler tests
```

## Build, run and test

Requires Node 18.18+.

```bash
npm install
npm run dev        # http://localhost:3000
npm test           # 43 Vitest tests
npm run typecheck
npm run build && npm start
```

Snippets are stored in `data/snippets.local.json`, which is created and seeded with examples on first run and is git-ignored. Set `SNIPPETS_FILE=/path/to/file.json` to store them somewhere else.

## API

```bash
# Search: q is ranked full-text, tag can repeat (AND), language filters
curl 'localhost:3000/api/snippets?q=lru&tag=cache&language=python'

# Create
curl -X POST localhost:3000/api/snippets -H 'content-type: application/json' \
  -d '{"title":"Hello","language":"bash","code":"echo $HOME","tags":"shell, demo"}'
# → 201 {"id":"…","title":"Hello","tags":["shell","demo"],…}

# Validation errors
curl -X POST localhost:3000/api/snippets -d '{"title":""}'
# → 400 {"errors":{"title":"Title is required.","code":"Code is required."}}

curl -X PUT    localhost:3000/api/snippets/<id> -d '{…}'   # 200 or 404
curl -X DELETE localhost:3000/api/snippets/<id>            # 204 or 404
```

## How the search scores

For a query like `lru cac`:

1. Tokenize → `lru`, `cac`. The last word is being typed, so it is a **prefix**: binary-search the sorted terms for everything starting with `cac` (→ `cache`).
2. For each term, every matching document gets `tf × ln(1 + N/df)`, where `tf` already includes the field weight. Exact matches beat prefix expansions (×0.8).
3. Documents must match **every** term. Results are sorted by total score, newest first on ties.

## Possible extensions

- Fuzzy matching (Levenshtein / trigram) for typos
- SQLite storage, plus user accounts and private and public snippets
- Export and import as GitHub Gists or a Markdown bundle
- More languages via a grammar table, or nested modes (e.g. SQL inside a JS template string)
- Keyboard shortcuts (`/` to focus search, `j`/`k` to navigate)
- Snippet versions with diffs between edits
