"""A tiny JSON-over-HTTP API plus a static dashboard page, using only the stdlib.

Routes
------
GET  /                      -> the dashboard (static/index.html)
GET  /api/pins              -> list of pin states
GET  /api/pins/<n>          -> one pin
POST /api/pins/<n>          -> body {"value": true|false} or {"duty": 0-100}
POST /api/pins/<n>/toggle   -> flip an output pin
GET  /api/system            -> CPU temp, load, uptime, memory
GET  /api/history           -> recent pin changes, newest first

Security model
--------------
This controls physical hardware, so it is locked down by default:

* The CLI binds to 127.0.0.1 unless you explicitly pass ``--host``.
* If a token is configured, every /api request must send
  ``Authorization: Bearer <token>``; comparisons use ``hmac.compare_digest``
  to avoid timing leaks.
* State-changing requests must be POST with a JSON body, so a malicious page
  can't flip a relay with a simple ``<img src=...>`` (no CSRF via GET).
* Request bodies are capped at a few KB.
"""

from __future__ import annotations

import hmac
import json
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any, Callable

from . import system
from .board import Board
from .gpio import GPIOError

MAX_BODY_BYTES = 4096
PIN_ROUTE = re.compile(r"^/api/pins/(\d+)(/toggle)?$")


class ApiError(Exception):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _load_index() -> bytes:
    return resources.files("pidash").joinpath("static/index.html").read_bytes()


def make_handler(
    board: Board,
    token: str | None = None,
    vitals: Callable[[], dict[str, Any]] = system.vitals,
) -> type[BaseHTTPRequestHandler]:
    """Build a handler class bound to a specific board (closure over state)."""

    index_html = _load_index()

    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "pidash/1.0"

        # Quieter logging: one line per request to stderr is plenty.
        def log_message(self, fmt: str, *args: Any) -> None:  # noqa: D401
            if getattr(self.server, "verbose", True):
                super().log_message(fmt, *args)

        # --- helpers ---------------------------------------------------------
        def _send(self, status: HTTPStatus, body: bytes, ctype: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: HTTPStatus, payload: Any) -> None:
            self._send(status, json.dumps(payload).encode(), "application/json")

        def _check_auth(self) -> None:
            if token is None:
                return
            header = self.headers.get("Authorization", "")
            supplied = header[7:] if header.startswith("Bearer ") else ""
            if not hmac.compare_digest(supplied.encode(), token.encode()):
                raise ApiError(HTTPStatus.UNAUTHORIZED, "missing or invalid token")

        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY_BYTES:
                raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body too large")
            if "application/json" not in self.headers.get("Content-Type", ""):
                raise ApiError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "send application/json")
            raw = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ApiError(HTTPStatus.BAD_REQUEST, f"invalid JSON: {exc.msg}") from exc
            if not isinstance(data, dict):
                raise ApiError(HTTPStatus.BAD_REQUEST, "JSON body must be an object")
            return data

        def _dispatch(self, fn: Callable[[], Any]) -> None:
            try:
                self._json(HTTPStatus.OK, fn())
            except ApiError as e:
                self._json(e.status, {"error": e.message})
            except KeyError as e:
                self._json(HTTPStatus.NOT_FOUND, {"error": f"GPIO{e.args[0]} is not configured"})
            except GPIOError as e:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(e)})

        # --- verbs -----------------------------------------------------------
        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                self._send(HTTPStatus.OK, index_html, "text/html; charset=utf-8")
                return

            def route() -> Any:
                self._check_auth()
                if path == "/api/pins":
                    return board.snapshot()
                if path == "/api/system":
                    return vitals()
                if path == "/api/history":
                    return board.history()
                m = PIN_ROUTE.match(path)
                if m and not m.group(2):
                    return board.pin_state(int(m.group(1)))
                raise ApiError(HTTPStatus.NOT_FOUND, "no such route")

            self._dispatch(route)

        def do_POST(self) -> None:
            path = self.path.split("?", 1)[0]

            def route() -> Any:
                self._check_auth()
                m = PIN_ROUTE.match(path)
                if not m:
                    raise ApiError(HTTPStatus.NOT_FOUND, "no such route")
                pin = int(m.group(1))
                body = self._body()
                if m.group(2):
                    return board.toggle(pin)
                if "duty" in body:
                    return board.set_duty(pin, body["duty"])
                if isinstance(body.get("value"), bool):
                    return board.set(pin, body["value"])
                raise ApiError(HTTPStatus.BAD_REQUEST, 'send {"value": bool} or {"duty": 0-100}')

            self._dispatch(route)

    return DashboardHandler


def make_server(
    board: Board,
    host: str = "127.0.0.1",
    port: int = 8080,
    token: str | None = None,
    verbose: bool = True,
    vitals: Callable[[], dict[str, Any]] = system.vitals,
) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((host, port), make_handler(board, token, vitals))
    httpd.daemon_threads = True
    httpd.verbose = verbose  # type: ignore[attr-defined]
    return httpd
