"""Stats service: counts events sent by other services.

Endpoints (internal network only, never published to the host):
    GET  /health   -> {"status": "ok"}
    POST /events   -> record one event, body {"type": "note_created"}
    GET  /stats    -> per-type counts, total and uptime

Counts survive container restarts because they are written to a JSON file
inside DATA_DIR, which Docker Compose mounts from the named volume
`stats-data`.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

log = logging.getLogger("stats")

# Event types are short identifiers; this stops clients from filling the
# file with arbitrary keys.
EVENT_TYPE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
MAX_BODY = 4096


class StatsStore:
    """Thread-safe counter map persisted to a JSON file."""

    def __init__(self, data_dir: str | os.PathLike) -> None:
        self.path = Path(data_dir) / "stats.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._counts: dict[str, int] = self._load()

    def _load(self) -> dict[str, int]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return {str(k): int(v) for k, v in raw.get("counts", {}).items()}
        except FileNotFoundError:
            return {}
        except (ValueError, AttributeError):
            log.warning("stats file %s is corrupt; starting from zero", self.path)
            return {}

    def _save(self) -> None:
        # Write to a temp file and rename it over the old one. The rename is
        # atomic, so a crash mid-write never leaves a half-written file.
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"counts": self._counts}, fh)
        os.replace(tmp, self.path)

    def record(self, event_type: str) -> int:
        with self._lock:
            self._counts[event_type] = self._counts.get(event_type, 0) + 1
            self._save()
            return self._counts[event_type]

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)


class StatsHandler(BaseHTTPRequestHandler):
    server_version = "stats/1.0"
    # Set on the server object by make_server().
    store: StatsStore
    started: float

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (http.server naming)
        if self.path == "/health":
            self._send(HTTPStatus.OK, {"status": "ok", "service": "stats"})
        elif self.path == "/stats":
            counts = self.server.store.snapshot()
            self._send(HTTPStatus.OK, {
                "counts": counts,
                "total": sum(counts.values()),
                "uptime_seconds": round(time.time() - self.server.started, 1),
            })
        else:
            self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/events":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "body too large"})
            return
        try:
            event = json.loads(self.rfile.read(length) or b"{}")
            event_type = event["type"]
        except (ValueError, KeyError, TypeError):
            self._send(HTTPStatus.BAD_REQUEST, {"error": "expected JSON {\"type\": ...}"})
            return
        if not isinstance(event_type, str) or not EVENT_TYPE.match(event_type):
            self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid event type"})
            return
        count = self.server.store.record(event_type)
        self._send(HTTPStatus.CREATED, {"type": event_type, "count": count})

    def log_message(self, fmt: str, *args) -> None:
        log.info("%s %s", self.address_string(), fmt % args)


def make_server(host: str, port: int, data_dir: str) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), StatsHandler)
    server.store = StatsStore(data_dir)
    server.started = time.time()
    return server


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    port = int(os.environ.get("PORT", "8000"))
    server = make_server("0.0.0.0", port, os.environ.get("DATA_DIR", "/data"))
    log.info("stats listening on :%d", port)
    server.serve_forever()


if __name__ == "__main__":
    main()
