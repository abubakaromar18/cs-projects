"""Shared test helpers: load each service's app.py and run it on a free port.

The three services all have a module called app.py, so they are loaded
under unique names with importlib instead of a plain import.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICES = ROOT / "services"

# Expected warnings (e.g. "stats unreachable") would clutter the test output.
logging.disable(logging.WARNING)


def load_service(name: str):
    service_dir = SERVICES / name
    # Lets notes/app.py do `from notes_store import ...` just like in its container.
    if str(service_dir) not in sys.path:
        sys.path.insert(0, str(service_dir))
    spec = importlib.util.spec_from_file_location(f"{name}_app", service_dir / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunningServer:
    """Start an http.server instance in a background thread (port 0 = any free port)."""

    def __init__(self, server) -> None:
        self.server = server
        self.thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()
        host, port = server.server_address[:2]
        self.url = f"http://127.0.0.1:{port}"

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def request(method: str, url: str, payload: object | None = None, raw: bytes | None = None,
            headers: dict | None = None):
    """Make an HTTP call and return (status, parsed JSON body, headers)."""
    data = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read() or b"null"), resp.headers
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"null"), exc.headers
