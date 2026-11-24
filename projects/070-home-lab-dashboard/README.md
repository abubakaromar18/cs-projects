# Home Lab Dashboard

A small self-hosted start page for your home lab, written in **TypeScript** on plain Node.js with **zero runtime dependencies**.
List your services in a JSON file and get one page of links, each with a live status light, latency, uptime and a sparkline of recent checks.

- **HTTP(S) checks** with expected status codes, optional `insecure` mode for self-signed certs, and redirects counted as "up"
- **TCP port checks** for things that don't speak HTTP (SSH, SMB, databases)
- **Up / Slow / Down / Unchecked** states, with a per-service "slow" threshold
- **Uptime %** and a **latency sparkline** from a bounded history
- Grouped cards, a **filter box** (press `/`), a **Check now** button, auto-refresh, and light and dark themes
- A **`--once` CLI mode** that prints a table and exits non-zero if anything is down, for cron or CI
- Binds to **127.0.0.1 by default**: exposing a map of your network is something you opt into

It only probes the hosts **you** list in your own config.

## CS concepts demonstrated

| Concept | Where |
|---|---|
| **Ring buffer.** Fixed-capacity history with O(1) push, so memory stays flat however long it runs | `RingBuffer` in `src/server/monitor.ts` |
| **Bounded concurrency.** A worker pool runs at most *N* probes at once and keeps results in input order | `mapWithConcurrency` |
| **Request coalescing.** Concurrent `checkAll()` calls share one in-flight round, and timer ticks are skipped while a round is still running | `Monitor.checkAll` / `start` |
| **Timeouts and failure isolation.** Every probe has a hard timeout and *resolves* (never rejects), so one hung host can't stall the rest | `src/server/checks.ts` |
| **Monotonic clocks.** Latency uses `performance.now()`, not wall-clock time | `checks.ts` |
| **Validating untrusted input.** The config parser collects *all* errors and reports each with its JSON path (`groups[1].services[0].url`) | `src/server/config.ts` |
| **Discriminated unions.** `CheckSpec` is `http \| tcp \| none`, and `switch` narrowing makes a forgotten case a compile error | `src/shared/types.ts` |
| **A shared wire contract.** Server and browser import the same types for `/api/status` | `src/shared/types.ts` |
| **Path-traversal defence.** The static file server normalises and confines paths to their root | `safeJoin` in `src/server/app.ts` |
| **XSS-safe rendering.** The DOM is built only with `textContent`, links go through a URL-scheme allowlist, and nothing uses `innerHTML` | `src/client/app.ts`, `safeHref` |
| **Dependency injection for tests.** The checker and clock are injected, so monitor tests are deterministic | `MonitorOptions` |

## Project layout

```
070-home-lab-dashboard/
├── services.example.json   # sample config; copy to services.json
├── public/
│   ├── index.html          # page shell
│   └── styles.css          # cards, pills, sparkline, dark mode
├── src/
│   ├── shared/types.ts     # config + API types shared by server and client
│   ├── server/
│   │   ├── config.ts       # load + validate config, fill defaults
│   │   ├── checks.ts       # HTTP and TCP probes with timeouts
│   │   ├── monitor.ts      # polling loop, ring-buffer history, uptime, snapshot
│   │   ├── app.ts          # node:http server: static files + JSON API
│   │   └── main.ts         # CLI (serve, or --once)
│   └── client/
│       ├── format.ts       # pure formatting, filtering and sparkline layout
│       └── app.ts          # browser: fetch, render, poll
└── test/                   # node:test suites (config, checks, monitor, app, format)
```

## Build, run, test

Requires Node.js 18 or newer.

```bash
npm install
cp services.example.json services.json   # then edit it for your lab
npm run build
node dist/server/main.js --config services.json --port 8080
# open http://127.0.0.1:8080
```

`npm start` builds the project and serves the example config. To reach the dashboard from other machines on your LAN, add `--host 0.0.0.0`.

```bash
npm test        # compiles src + test, runs node --test (34 tests)
npm run typecheck
```

The tests start real local HTTP and TCP servers on `127.0.0.1`. They cover 200, redirect, 500, slow, timeout, refused and open/closed-port cases. They also run the full HTTP API against a monitor with an injected checker.

## Configuration

```jsonc
{
  "title": "My Home Lab",
  "intervalSeconds": 30,      // how often to check (default 30)
  "historySize": 60,          // samples kept per service (default 60)
  "groups": [
    { "name": "Media", "services": [
      { "name": "Jellyfin", "url": "http://192.168.1.10:8096", "icon": "🎬",
        "description": "Movies & TV",
        "check": { "type": "http", "path": "/health", "expectStatus": [200] } },
      { "name": "Proxmox", "url": "https://192.168.1.2:8006",
        "check": { "type": "http", "insecure": true, "slowMs": 800 } },
      { "name": "NAS", "url": "smb://192.168.1.20",
        "check": { "type": "tcp", "host": "192.168.1.20", "port": 445 } }
    ] }
  ]
}
```

| Field | Notes |
|---|---|
| `check` omitted | `http(s)://` URLs get an HTTP check; other schemes get none |
| `http` | `path`, `target` (probe a different URL), `expectStatus` (default: any 2xx/3xx), `insecure`, `timeoutMs` (default 5000), `slowMs` (default 1500) |
| `tcp` | `host` and `port`, which default to the URL's host and port, plus `timeoutMs` and `slowMs` |
| `none` | Link only, shown as "Unchecked" |

### API

| Route | |
|---|---|
| `GET /api/status` | Full snapshot: summary counts, and per service the current result, history and uptime |
| `POST /api/refresh` | Check everything now, then return the snapshot |
| `GET /api/health` | `{ ok: true }`, so the dashboard can monitor itself |

## Example output

```
$ node dist/server/main.js --config services.json --once
Demo Lab
STATUS     GROUP  SERVICE      LATENCY  DETAIL
● up       Self   Dashboard    5 ms     HTTP 200
○ down     Self   Missing API  4 ms     HTTP 404 (unexpected)
○ down     Other  Closed port  -        connection refused
· unknown  Other  Router       -        no health check

1 up, 0 degraded, 2 down, 1 unchecked
$ echo $?
1
```

In the browser, the banner reads "2 services down", the failing cards get a red outline, and each card shows latency, uptime, time since the last check and a bar sparkline. In the sparkline, bar height is latency, and red full-height bars are outages.

## Possible extensions

- Persist history to SQLite or a JSON file so uptime survives restarts
- Notifications (ntfy, Gotify, email) when a service changes state, with flap damping
- Server-Sent Events instead of polling, so the page updates the moment a check finishes
- More probe types: ICMP ping, DNS lookups, TLS certificate expiry warnings, Docker container status
- Auto-discovery from Docker labels or a Traefik/Caddy config
- A Dockerfile and a systemd unit for running it as a service
