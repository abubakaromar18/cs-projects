"""API gateway: the only service published to the host.

It sits on two networks. On `frontend` it accepts requests from the host
(port 8080). On `backend`, an internal network with no route to the outside,
it forwards them to the notes and stats services.

Routes:
    GET  /                 -> list of routes
    GET  /health           -> health of the gateway and every backend (503 if any is down)
    *    /api/notes[/...]  -> notes service  /notes[/...]
    GET  /api/stats        -> stats service  /stats

Every proxied request carries an X-Request-ID header (generated if the
client did not send one), so a single request can be followed through the
logs of all three containers.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger("gateway")

MAX_REQUEST = 16_384
TIMEOUT = 3


def resolve(path: str, upstreams: dict[str, str]) -> str | None:
    """Map a public path to an upstream URL, or None if no route matches."""
    if path == "/api/notes" or path.startswith("/api/notes/"):
        return upstreams["notes"] + path[len("/api"):]
    if path == "/api/stats":
        return upstreams["stats"] + "/stats"
    return None


def check_health(upstreams: dict[str, str]) -> tuple[bool, dict[str, str]]:
    """Ask each backend for /health. Returns (all_ok, per-service status)."""
    results = {"gateway": "ok"}
    for name, base in upstreams.items():
        try:
            with urllib.request.urlopen(f"{base}/health", timeout=TIMEOUT) as resp:
                results[name] = "ok" if resp.status == 200 else f"http {resp.status}"
        except (OSError, urllib.error.URLError) as exc:
            results[name] = f"down ({exc.__class__.__name__})"
    return all(v == "ok" for v in results.values()), results


class GatewayHandler(BaseHTTPRequestHandler):
    server_version = "gateway/1.0"

    def _send(self, status: int, body: bytes, content_type: str = "application/json",
              request_id: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if request_id:
            self.send_header("X-Request-ID", request_id)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: object, request_id: str | None = None) -> None:
        self._send(status, json.dumps(payload).encode(), request_id=request_id)

    def _handle(self) -> None:
        request_id = self.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        upstreams = self.server.upstreams

        if self.command == "GET" and self.path == "/":
            self._json(HTTPStatus.OK, {
                "service": "gateway",
                "routes": ["GET /health", "GET|POST /api/notes",
                           "GET|DELETE /api/notes/<id>", "GET /api/stats"],
            }, request_id)
            return
        if self.command == "GET" and self.path == "/health":
            ok, detail = check_health(upstreams)
            self._json(HTTPStatus.OK if ok else HTTPStatus.SERVICE_UNAVAILABLE,
                       {"status": "ok" if ok else "degraded", "services": detail}, request_id)
            return

        target = resolve(self.path, upstreams)
        if target is None:
            self._json(HTTPStatus.NOT_FOUND, {"error": "no route"}, request_id)
            return

        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_REQUEST:
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "body too large"}, request_id)
            return
        body = self.rfile.read(length) if length else None
        self._proxy(target, body, request_id)

    def _proxy(self, target: str, body: bytes | None, request_id: str) -> None:
        req = urllib.request.Request(target, data=body, method=self.command, headers={
            "Content-Type": self.headers.get("Content-Type", "application/json"),
            "X-Request-ID": request_id,
        })
        log.info("[%s] %s %s -> %s", request_id, self.command, self.path, target)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                self._send(resp.status, resp.read(),
                           resp.headers.get("Content-Type", "application/json"), request_id)
        except urllib.error.HTTPError as exc:
            # The upstream answered with an error (404, 400...): pass it through.
            self._send(exc.code, exc.read(),
                       exc.headers.get("Content-Type", "application/json"), request_id)
        except OSError as exc:
            # The upstream did not answer at all.
            log.warning("[%s] upstream %s unreachable: %s", request_id, target, exc)
            self._json(HTTPStatus.BAD_GATEWAY, {"error": "upstream unavailable"}, request_id)

    do_GET = do_POST = do_DELETE = _handle  # noqa: N815

    def log_message(self, fmt: str, *args) -> None:
        log.info("%s %s", self.address_string(), fmt % args)


def make_server(host: str, port: int, notes_url: str, stats_url: str) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), GatewayHandler)
    server.upstreams = {"notes": notes_url.rstrip("/"), "stats": stats_url.rstrip("/")}
    return server


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    port = int(os.environ.get("PORT", "8080"))
    server = make_server(
        "0.0.0.0",
        port,
        os.environ.get("NOTES_URL", "http://notes:8000"),
        os.environ.get("STATS_URL", "http://stats:8000"),
    )
    log.info("gateway listening on :%d -> %s", port, server.upstreams)
    server.serve_forever()


if __name__ == "__main__":
    main()
