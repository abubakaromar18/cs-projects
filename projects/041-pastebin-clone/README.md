# 041 · Pastebin Clone

A small paste-sharing service built with **Node.js + Express**. Paste some code, pick a language and an expiry, and get a short link with server-side syntax highlighting. Pastes can also be set to **burn after reading**, so they're deleted the first time someone opens them.

Everything is in memory and binds to `127.0.0.1` by default. It's a learning project, not a production service.

## Features

- Web form plus a JSON API for creating and reading pastes
- Expiry options of 10 minutes, 1 hour, 1 day, 1 week, or never (the API accepts any `Ns/m/h/d/w` value up to 30 days)
- Burn-after-read pastes that are deleted on first view
- Server-side highlighting with [highlight.js](https://highlightjs.org/): pick a language or let it auto-detect, and lines are numbered
- `/raw/:id` endpoint that serves plain text
- Per-paste **delete token**, returned only to the creator, for deleting a paste early
- A recent-pastes list (burn-after-read pastes are hidden from it)
- Security headers (strict CSP, `nosniff`, no referrer) and HTML escaping of all user input

## CS concepts demonstrated

| Concept | Where |
|---|---|
| **TTL expiry with a min-heap**: lazy expiry on read plus an eager sweep that pops expired entries in O(k log n) | `src/store.js` (`ExpiryHeap`, `sweep`) |
| **Stale-entry handling**: heap entries for pastes that were already deleted are skipped instead of searched for and removed | `PasteStore.sweep` |
| **Unbiased random IDs**: crypto randomness with rejection sampling, avoiding the bias of `byte % 62` | `src/ids.js` |
| **Constant-time comparison** of secrets (`timingSafeEqual`) | `deleteWithToken` |
| **Dependency injection** of the clock and store, so time-based behaviour can be tested deterministically | `createApp({ store })`, `new PasteStore({ now })` |
| **REST design**: `201 + Location`, `204`, `303 See Other` after a form POST, plus `400/403/404/413/503` | `src/app.js` |
| **Output encoding and XSS defence**: escape-on-output templates, a CSP with no inline scripts, and raw text served as `text/plain` | `src/views.js`, `src/app.js` |
| **Input validation and size limits** at both the body-parser and application level | `parsePasteInput` |

## Project layout

```
041-pastebin-clone/
├── src/
│   ├── server.js     # entry point: listen + graceful shutdown
│   ├── app.js        # Express app factory, routes, error handling
│   ├── store.js      # PasteStore + ExpiryHeap
│   ├── expiry.js     # "10m"/"1d"/"never" parsing, human-readable remaining time
│   ├── highlight.js  # highlight.js wrapper + HTML escaping
│   ├── ids.js        # base62 ID generation/validation
│   └── views.js      # HTML templates
├── public/app.css
└── test/             # node:test + supertest
```

## Run it

Requires Node 18 or newer.

```bash
npm install
npm start                 # http://127.0.0.1:3000
PORT=8080 npm start       # different port
npm run dev               # restart on file changes
```

## Test it

```bash
npm test
```

There are 27 tests, written with the built-in `node:test` runner and `supertest`. They cover heap ordering and expiry, burning pastes, delete tokens, the capacity limit, highlighting and escaping, and every HTTP route. Tests inject a fake clock, so expiry is checked without waiting.

## API examples

```bash
# Create a paste
curl -s -X POST localhost:3000/api/pastes \
  -H 'Content-Type: application/json' \
  -d '{"content":"fn main() { println!(\"hi\"); }","language":"rust","expiresIn":"1h"}'
```

```json
{
  "id": "EE9msshc",
  "title": "",
  "language": "rust",
  "content": "fn main() { println!(\"hi\"); }",
  "createdAt": "2026-11-10T02:44:52.869Z",
  "expiresAt": "2026-11-10T03:44:52.869Z",
  "burnAfterRead": false,
  "views": 0,
  "url": "http://localhost:3000/EE9msshc",
  "rawUrl": "http://localhost:3000/raw/EE9msshc",
  "deleteToken": "mxMoIH3gWA91JmqZAC1J5UoQ"
}
```

```bash
curl localhost:3000/raw/EE9msshc                          # plain text
curl localhost:3000/api/pastes/EE9msshc                   # JSON (counts a view)
curl -X DELETE localhost:3000/api/pastes/EE9msshc \
     -H 'X-Delete-Token: mxMoIH3gWA91JmqZAC1J5UoQ'        # 204 No Content
```

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | New-paste form and recent pastes |
| `POST` | `/pastes` | Form submit, which redirects to the paste (or shows a share page for burn-after-read) |
| `GET` | `/:id` | Highlighted HTML view |
| `GET` | `/raw/:id` | Raw text |
| `POST` | `/api/pastes` | Create a paste: `content`, `title?`, `language?`, `expiresIn?`, `burnAfterRead?` |
| `GET` | `/api/pastes/:id` | Paste as JSON |
| `DELETE` | `/api/pastes/:id` | Delete a paste (needs the `X-Delete-Token` header) |
| `GET` | `/healthz` | Health check |

## Possible extensions

- Persist pastes in SQLite or Redis, using Redis `EXPIRE` in place of the heap
- Per-IP rate limiting with a token bucket
- Password-protected pastes, or client-side encryption so the server never sees the plaintext (the key lives in the URL fragment)
- Diff view between two pastes, or forking a paste
- Dark-mode theme switching, and copy-to-clipboard
- Content-addressed deduplication, where identical content shares storage keyed by its SHA-256 hash
