"""Command-line interface: ``portscan HOST [-p PORTS] [options]``."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .ports import PortSpecError, parse_ports
from .report import render_json, render_text
from .scanner import PortState, ScanConfig, scan
from .targets import TargetNotAllowed, make_target


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="portscan",
        description="Educational TCP connect scanner for machines you own "
                    "(loopback by default; private LAN with --allow-private).",
    )
    p.add_argument("host", nargs="?", default="127.0.0.1",
                   help="target host (default: 127.0.0.1)")
    p.add_argument("-p", "--ports", default="1-1024",
                   help="ports, e.g. '22,80,8000-8100', 'top' or 'all' (default: 1-1024)")
    p.add_argument("-t", "--timeout", type=float, default=1.0,
                   help="per-connection timeout in seconds (default: 1.0)")
    p.add_argument("-c", "--concurrency", type=int, default=200,
                   help="max simultaneous connections (default: 200)")
    p.add_argument("-b", "--banner", action="store_true",
                   help="grab a short greeting banner from open ports")
    p.add_argument("-a", "--all", action="store_true", dest="show_all",
                   help="list closed/filtered ports too")
    p.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    p.add_argument("--allow-private", action="store_true",
                   help="permit RFC 1918 / link-local addresses (your own LAN)")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="print each open port as soon as it is found (stderr)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        ports = parse_ports(args.ports)
        target = make_target(args.host, allow_private=args.allow_private)
        cfg = ScanConfig(timeout=args.timeout, concurrency=args.concurrency,
                         grab_banner=args.banner)
        if cfg.timeout <= 0 or cfg.concurrency < 1:
            raise ValueError("timeout must be > 0 and concurrency >= 1")
    except (PortSpecError, TargetNotAllowed, ValueError) as exc:
        print(f"portscan: error: {exc}", file=sys.stderr)
        return 2

    def live(result):
        if args.verbose and result.state is PortState.OPEN:
            print(f"[+] {result.port}/tcp open", file=sys.stderr, flush=True)

    try:
        report = scan(target, ports, cfg, on_result=live)
    except KeyboardInterrupt:
        print("portscan: interrupted", file=sys.stderr)
        return 130

    print(render_json(report) if args.json else render_text(report, show_all=args.show_all))
    # Exit 0 if anything is open, 1 otherwise — convenient in shell scripts.
    return 0 if report.open_ports else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
