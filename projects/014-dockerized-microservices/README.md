# 014 · Dockerized Microservices (Docker Compose)

Three small HTTP services wired together with **Docker Compose**: an API
gateway, a notes service and a stats service. Only the gateway is published to
the host. The other two sit on a private, internal network, find each other
by service name, and keep their data in **named volumes** that outlive the
containers.

The services are plain Python 3.12 using only the standard library, so the
images need no `pip install` and the code stays short enough to read in one
sitting. The project is about the Compose part: networks, volumes,
health checks, start-up order and service discovery.

```
                 ┌──────────────── frontend network ────────────────┐
  host           │                                                  │
  127.0.0.1:8080 ┼──► gateway :8080                                 │
                 │       │                                          │
                 └───────┼──────────────────────────────────────────┘
                 ┌───────┼──────── backend network (internal) ──────┐
                 │       ├──► notes :8000 ──(events)──► stats :8000 │
                 │       │      │                         │         │
                 │       └──────┼────────────────────────►│         │
                 │              ▼                         ▼         │
                 │      [notes-data volume]      [stats-data volume]│
                 └──────────────────────────────────────────────────┘
```

| Service   | Networks              | Port on host     | Volume       | Job                                        |
|-----------|-----------------------|------------------|--------------|--------------------------------------------|
| `gateway` | `frontend`, `backend` | `127.0.0.1:8080` | none         | Routes `/api/*` to the backends, health aggregation, request IDs |
| `notes`   | `backend`             | none             | `notes-data` | CRUD API for notes, stored in `/data/notes.json` |
| `stats`   | `backend`             | none             | `stats-data` | Counts events (`note_created`, `note_deleted`) |

## Key concepts

- **Service discovery through Compose DNS.** Containers on the same network
  reach each other by service name: the gateway calls `http://notes:8000`,
  and notes calls `http://stats:8000`. No IP addresses anywhere.
- **Network segmentation.** `backend` is declared `internal: true`, so it has
  no route to the internet. Only the gateway joins both networks, which makes
  it the single entry point. notes and stats publish no ports.
- **Named volumes for state.** `docker compose down` removes containers but
  keeps `notes-data` and `stats-data`; `docker compose down -v` deletes them.
  Writes go to a temp file and are `os.replace`d into place, so a crash never
  leaves a half-written JSON file.
- **Health checks and start-up order.** Each Dockerfile has a `HEALTHCHECK`.
  `depends_on: condition: service_healthy` starts stats first, then notes,
  then the gateway, each only once the one before it answers.
- **Graceful degradation.** notes sends events to stats in a background
  thread and only logs a warning if stats is down; notes keep working. The
  gateway returns `502` for an unreachable upstream and `/health` reports
  `503 degraded` with per-service detail.
- **Request tracing.** The gateway adds an `X-Request-ID` header (or keeps the
  client's) and forwards it, so one request can be followed through all logs.
- **Container hygiene.** Slim base image, non-root user, unbuffered logs,
  `.dockerignore`, port bound to localhost by default.

## Layout

```
compose.yaml            the whole stack
Makefile                up / down / logs / test / smoke shortcuts
.env.example            copy to .env to change GATEWAY_PORT
services/
  gateway/  app.py, Dockerfile
  notes/    app.py, notes_store.py, Dockerfile
  stats/    app.py, Dockerfile
scripts/
  smoke_test.sh         end-to-end test against the running containers
  run_local.py          run the three services without Docker
tests/                  unit, integration and compose-file tests (unittest)
```

## Run it

Requires Docker with the Compose plugin (`docker compose version`).

```bash
make up          # docker compose up --build -d --wait
make ps          # all three should show "healthy"
make smoke       # end-to-end checks against the real containers
make logs        # follow logs
make down        # stop; data volumes are kept
make clean-volumes   # stop and delete the data
```

No Docker? `make local` runs the same three services as plain processes on
ports 8080 / 8001 / 8002.

## API

All requests go through the gateway on `http://127.0.0.1:8080`.

| Method   | Path              | Description                                  |
|----------|-------------------|----------------------------------------------|
| `GET`    | `/`               | Route list                                   |
| `GET`    | `/health`         | Health of all services (`200` or `503`)      |
| `GET`    | `/api/notes`      | List notes                                   |
| `POST`   | `/api/notes`      | Create `{"title": "...", "body": "..."}`     |
| `GET`    | `/api/notes/<id>` | One note                                     |
| `DELETE` | `/api/notes/<id>` | Delete a note                                |
| `GET`    | `/api/stats`      | Event counts                                 |

### Example session

```console
$ curl -s localhost:8080/health
{"status": "ok", "services": {"gateway": "ok", "notes": "ok", "stats": "ok"}}

$ curl -s -X POST localhost:8080/api/notes -d '{"title": "Compose", "body": "volumes outlive containers"}'
{"id": 1, "title": "Compose", "body": "volumes outlive containers", "created_at": "2026-10-27T13:50:55+00:00"}

$ curl -s localhost:8080/api/stats
{"counts": {"note_created": 1}, "total": 1, "uptime_seconds": 12.4}

$ docker compose stop stats
$ curl -s localhost:8080/health
{"status": "degraded", "services": {"gateway": "ok", "notes": "ok", "stats": "down (URLError)"}}

$ curl -s -X POST localhost:8080/api/notes -d '{"title": "still works"}'
{"id": 2, "title": "still works", "body": "", "created_at": "..."}

$ docker compose start stats
$ docker compose down && docker compose up -d --wait
$ curl -s localhost:8080/api/notes      # both notes are still there
```

Try reaching a backend directly and it fails, because only the gateway
publishes a port:

```console
$ curl localhost:8000/notes
curl: (7) Failed to connect to localhost port 8000
```

## Tests

```bash
make test        # or: cd tests && python3 -m unittest -v
```

32 tests, standard library only:

- `test_stats.py`, `test_notes.py`: storage, persistence across restarts,
  validation, and each HTTP API on its own.
- `test_gateway.py`: routing table, and behaviour when no backend is up
  (`502`, `503 degraded`).
- `test_integration.py`: all three services wired together on local ports the
  way Compose wires them: notes → stats events, error pass-through,
  request-ID propagation, data surviving a full restart, notes still working
  with stats down.
- `test_compose.py`: parses `compose.yaml` with `docker compose config` and
  checks the architecture (only the gateway has ports, `backend` is internal,
  named volumes, health-gated `depends_on`, non-root Dockerfiles). Skipped if
  the Docker CLI is not installed.

`scripts/smoke_test.sh` (`make smoke`) is the container-level test: it brings
the stack up and checks health, the notes → stats flow, DNS service discovery,
that `stats` has no internet access, and that data survives
`docker compose restart notes`.

> **Note on how this was verified:** all 32 Python tests pass, and
> `docker compose config` validates the compose file. The build environment
> could not pull images from Docker Hub, so the images were not built and
> `smoke_test.sh` was not run there. Run `make smoke` on a machine with
> Docker to check the containers.

## Possible extensions

- Swap the JSON files for a Postgres or Redis container and see how volumes
  and health checks change.
- Send events through a message queue (RabbitMQ, NATS) instead of HTTP.
- Put nginx or Traefik in front as a reverse proxy with rate limiting.
- Add Prometheus metrics endpoints and a Grafana container.
- Scale notes with `docker compose up --scale notes=3` (needs a shared
  database first, since each replica would otherwise get its own file).
- Add a `compose.override.yaml` for development with bind-mounted source and
  auto-reload.
- Build multi-arch images and push them from GitHub Actions.
