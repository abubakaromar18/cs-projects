# 002 · URL Shortener

A small, complete URL shortening service in Go. Paste a long link, get a short
one like `http://localhost:8080/aZ3k9Qx`, and see how many times it has been
clicked. Links are stored in SQLite, so they survive restarts.

- Random 7-character base62 codes, or a custom alias (`/go-docs`)
- `302` redirects that count clicks and record the last click time
- Shortening the same URL twice returns the same code
- JSON API plus a simple HTML page (light and dark mode)
- Input validation: only `http`/`https`, valid hostnames, length limits, reserved words
- Graceful shutdown, request logging, server timeouts

## CS concepts

| Concept | Where |
|---|---|
| **Base62 encoding** and the size of a code space (62⁷ ≈ 3.5 × 10¹²) | `internal/shortcode` |
| **Cryptographic randomness** without modulo bias (`crypto/rand` + `rand.Int`) | `shortcode.Generate` |
| **Collision handling** by retrying on a unique-constraint violation | `server.shorten` |
| **Atomic read-modify-write**: `UPDATE … SET clicks = clicks + 1 … RETURNING url` | `store.Resolve` |
| **Relational schema and indexes** (primary key on code, index on URL) | `store.schema` |
| **Concurrency**: WAL mode, busy timeout, single-writer connection pool; a test fires 200 concurrent clicks and checks none are lost | `store` |
| **HTTP semantics**: 201 vs 200, 302 vs 301 (301s are cached and would undercount), 404/409/400 | `internal/server` |
| **Layered design**: code generation, persistence, and HTTP are separate packages | whole project |
| **Defensive input handling**: scheme allow-list, hostname check, `MaxBytesReader`, HTML auto-escaping | `server.normalizeURL`, templates |

## Layout

```
cmd/shortener/          main: flags, HTTP server, graceful shutdown
internal/shortcode/     code generation, alias validation, base62 encode/decode
internal/store/         SQLite persistence (create, resolve+count, list, delete)
internal/server/        routes, JSON API, redirect, HTML page (embedded template)
```

## Build, run, test

Requires **Go 1.22+** and a **C compiler** (gcc or clang), because the
`github.com/mattn/go-sqlite3` driver uses cgo.

```bash
make run                 # go run ./cmd/shortener  → http://127.0.0.1:8080
make build               # bin/shortener
make test                # go test -race ./...
make cover               # coverage report
```

Flags:

```
-addr      listen address              (default 127.0.0.1:8080)
-db        SQLite file                 (default shortener.db)
-base-url  public prefix for links     (default http://<addr>)
```

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/links` | Body `{"url": "...", "alias": "optional"}`. 201 if created, 200 if the URL already had a code |
| `GET` | `/api/links?limit=20&offset=0` | Newest first, max 100 per page |
| `GET` | `/api/links/{code}` | One link with stats |
| `DELETE` | `/api/links/{code}` | 204, or 404 |
| `GET` | `/api/stats` | Total links and clicks |
| `GET` | `/{code}` | 302 redirect to the destination, counts a click |
| `GET` | `/healthz` | Liveness check |

## Example

```console
$ curl -s -X POST localhost:8080/api/links -d '{"url":"https://go.dev/doc/effective_go"}'
{"code":"ZEEOD3L","url":"https://go.dev/doc/effective_go","custom":false,"clicks":0,
 "created_at":"2026-10-21T13:48:18.345Z","short_url":"http://127.0.0.1:8080/ZEEOD3L"}

$ curl -s -X POST localhost:8080/api/links -d '{"url":"sqlite.org","alias":"sqlite"}'
{"code":"sqlite","url":"https://sqlite.org","custom":true,"clicks":0, ... }

$ curl -si localhost:8080/sqlite | head -4
HTTP/1.1 302 Found
Cache-Control: no-store
Content-Type: text/html; charset=utf-8
Location: https://sqlite.org

$ curl -s localhost:8080/api/links/sqlite
{"code":"sqlite","url":"https://sqlite.org","custom":true,"clicks":1,
 "last_clicked_at":"2026-10-21T13:48:18.357Z", ... }

$ curl -s localhost:8080/api/stats
{"links":2,"clicks":1}
```

Errors are JSON too: `{"error":"only http and https URLs are allowed"}`.

## Tests

Tests run against real SQLite files in temporary directories and a real
`httptest.Server`; nothing is mocked except the code generator in the
collision test. They cover code generation and validation, base62 round
trips, persistence across reopen, pagination, concurrent click counting,
alias conflicts, duplicate-URL reuse, bad input, redirects, deletion, and
HTML escaping in the form page.

## Possible extensions

- Per-click analytics table (referrer, user agent, day buckets) with a chart
- Link expiry dates and one-time links
- Rate limiting per IP (token bucket) to stop abuse
- QR code for each short link
- Swap to a pure-Go SQLite driver (`modernc.org/sqlite`) to drop the cgo requirement
- Blocklist check for known-malicious domains before shortening
- API keys so only owners can delete their links
