"""Notes service: a small CRUD API that reports events to the stats service.

Endpoints (internal network only):
    GET    /health        -> {"status": "ok"}
    GET    /notes         -> list of notes
    POST   /notes         -> create, body {"title": "...", "body": "..."}
    GET    /notes/<id>    -> one note
    DELETE /notes/<id>    -> delete one note

The service finds the stats service by its Compose service name
(STATS_URL=http://stats:8000). Docker's embedded DNS resolves `stats` to the
container's IP on the shared `backend` network.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import urllib.request
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from notes_store import NoteStore, ValidationError, validate

log = logging.getLogger("notes")

NOTE_PATH = re.compile(r"^/notes/(\d+)$")
MAX_REQUEST = 16_384


def emit_event(stats_url: str | None, event_type: str) -> threading.Thread | None:
    """Tell the stats service something happened, without blocking the caller.

    This is fire-and-forget: if stats is down, the note is still saved and we
    only log a warning. One slow or failed service should not take the others
    down with it.
    """
    if not stats_url:
        return None

    def send() -> None:
        req = urllib.request.Request(
            f"{stats_url}/events",
            data=json.dumps({"type": event_type}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=2):
                pass
        except OSError as exc:
            log.warning("could not reach stats service: %s", exc)

    thread = threading.Thread(target=send, daemon=True)
    thread.start()
    return thread


class NotesHandler(BaseHTTPRequestHandler):
    server_version = "notes/1.0"

    def _send(self, status: int, payload: object) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        store: NoteStore = self.server.store
        if self.path == "/health":
            self._send(HTTPStatus.OK, {"status": "ok", "service": "notes"})
        elif self.path == "/notes":
            self._send(HTTPStatus.OK, [asdict(n) for n in store.list()])
        elif match := NOTE_PATH.match(self.path):
            note = store.get(int(match.group(1)))
            if note is None:
                self._send(HTTPStatus.NOT_FOUND, {"error": "note not found"})
            else:
                self._send(HTTPStatus.OK, asdict(note))
        else:
            self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/notes":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_REQUEST:
            self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "body too large"})
            return
        try:
            title, body = _parse_note(self.rfile.read(length))
        except ValidationError as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        note = self.server.store.create(title, body)
        emit_event(self.server.stats_url, "note_created")
        self._send(HTTPStatus.CREATED, asdict(note))

    def do_DELETE(self) -> None:  # noqa: N802
        match = NOTE_PATH.match(self.path)
        if not match:
            self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})
        elif self.server.store.delete(int(match.group(1))):
            emit_event(self.server.stats_url, "note_deleted")
            self._send(HTTPStatus.OK, {"deleted": int(match.group(1))})
        else:
            self._send(HTTPStatus.NOT_FOUND, {"error": "note not found"})

    def log_message(self, fmt: str, *args) -> None:
        log.info("%s %s", self.address_string(), fmt % args)


def _parse_note(raw: bytes) -> tuple[str, str]:
    try:
        data = json.loads(raw or b"null")
    except ValueError as exc:
        raise ValidationError("body is not valid JSON") from exc
    return validate(data)


def make_server(host: str, port: int, data_dir: str, stats_url: str | None) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), NotesHandler)
    server.store = NoteStore(data_dir)
    server.stats_url = stats_url.rstrip("/") if stats_url else None
    return server


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    port = int(os.environ.get("PORT", "8000"))
    server = make_server(
        "0.0.0.0",
        port,
        os.environ.get("DATA_DIR", "/data"),
        os.environ.get("STATS_URL", "http://stats:8000"),
    )
    log.info("notes listening on :%d (stats at %s)", port, server.stats_url)
    server.serve_forever()


if __name__ == "__main__":
    main()
