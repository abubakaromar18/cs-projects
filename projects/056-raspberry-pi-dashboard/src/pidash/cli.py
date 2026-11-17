"""Command-line entry point: ``pidash --config pins.json``."""

from __future__ import annotations

import argparse
import os
import sys
from importlib import resources

from .board import Board
from .gpio import GPIOError, make_backend
from .server import make_server


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pidash", description="Raspberry Pi GPIO web dashboard")
    p.add_argument("--config", help="pin config JSON (default: bundled demo layout)")
    p.add_argument("--backend", choices=["mock", "rpi"], default="mock",
                   help="mock = simulated pins (default), rpi = real hardware via RPi.GPIO")
    p.add_argument("--host", default="127.0.0.1",
                   help="bind address (default 127.0.0.1; use 0.0.0.0 for your LAN)")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--quiet", action="store_true", help="suppress per-request logs")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # The token comes from the environment so it never lands in shell history.
    token = os.environ.get("PIDASH_TOKEN") or None

    if args.host not in ("127.0.0.1", "localhost", "::1") and token is None:
        print("warning: listening beyond localhost without PIDASH_TOKEN set - "
              "anyone on your network can switch your pins", file=sys.stderr)

    try:
        backend = make_backend(args.backend)
        if args.config:
            board = Board.from_json_file(backend, args.config)
        else:
            with resources.as_file(resources.files("pidash").joinpath("static/demo-pins.json")) as f:
                board = Board.from_json_file(backend, f)
    except (GPIOError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    httpd = make_server(board, args.host, args.port, token, verbose=not args.quiet)
    print(f"pidash [{backend.name}] serving {len(board.pins)} pins on http://{args.host}:{args.port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    finally:
        httpd.server_close()
        backend.cleanup()
    return 0


if __name__ == "__main__":
    sys.exit(main())
