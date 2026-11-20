"""Command-line interface: ``netspeed serve``, ``netspeed test``, ``netspeed demo``."""

from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import sys
from dataclasses import asdict

from . import protocol as p
from .client import SpeedClient, udp_probe
from .server import SpeedServer
from .stats import LatencySummary, format_bytes, format_rate


def _is_private(host: str) -> bool:
    """True for loopback / RFC 1918 / link-local addresses."""
    try:
        addr = ipaddress.ip_address(socket.gethostbyname(host))
    except (OSError, ValueError):
        return False
    return addr.is_loopback or addr.is_private or addr.is_link_local


def _fmt_latency(name: str, s: LatencySummary) -> list[str]:
    return [
        f"{name} ({s.count} samples)",
        f"  min/avg/median/p95/max  {s.min:.3f} / {s.mean:.3f} / {s.median:.3f} / {s.p95:.3f} / {s.max:.3f} ms",
        f"  stdev {s.stdev:.3f} ms   jitter {s.jitter:.3f} ms   jitter(RFC 3550) {s.jitter_rfc3550:.3f} ms",
    ]


def run_tests(host: str, port: int, pings: int, duration: float, udp_count: int) -> dict:
    """Run the full suite and return results as a plain dict."""
    out: dict = {"host": host, "port": port}
    with SpeedClient(host, port) as c:
        out["tcp_latency"] = asdict(c.measure_latency(pings))
        for direction in ("download", "upload"):
            r = c.timed_transfer(direction, duration)
            out[direction] = {"bytes": r.bytes, "seconds": r.seconds, "bps": r.bps}
    u = udp_probe(host, port, count=udp_count)
    out["udp"] = {
        "sent": u.sent,
        "received": u.received,
        "loss": u.loss,
        "duplicates": u.duplicates,
        "reordered": u.reordered,
        "latency": asdict(u.latency) if u.latency else None,
    }
    return out


def render(res: dict) -> str:
    lines = [f"netspeed → {res['host']}:{res['port']}", ""]
    lines += _fmt_latency("TCP latency", LatencySummary(**res["tcp_latency"]))
    lines.append("")
    for d in ("download", "upload"):
        r = res[d]
        lines.append(
            f"{d.capitalize():<9} {format_rate(r['bps']):>15}   "
            f"({format_bytes(r['bytes'])} in {r['seconds']:.2f} s)"
        )
    u = res["udp"]
    lines += ["", f"UDP probes: {u['received']}/{u['sent']} returned, loss {u['loss']:.1%}, "
                  f"{u['reordered']} reordered, {u['duplicates']} duplicates"]
    if u["latency"]:
        lines += _fmt_latency("UDP latency", LatencySummary(**u["latency"]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="netspeed", description="Measure latency, jitter, throughput and loss to a netspeed server you run.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="run the measurement server")
    s.add_argument("--host", default="127.0.0.1", help="bind address (default: loopback only)")
    s.add_argument("--port", type=int, default=p.DEFAULT_PORT)

    for name, help_ in (("test", "test against a running server"), ("demo", "start a local server and test it")):
        t = sub.add_parser(name, help=help_)
        if name == "test":
            t.add_argument("--host", default="127.0.0.1")
            t.add_argument("--port", type=int, default=p.DEFAULT_PORT)
            t.add_argument("--allow-public", action="store_true",
                           help="allow non-private addresses (only for servers you own)")
        t.add_argument("-n", "--pings", type=int, default=20)
        t.add_argument("-t", "--duration", type=float, default=2.0, help="seconds per throughput direction")
        t.add_argument("--udp", type=int, default=100, help="number of UDP probes")
        t.add_argument("--json", action="store_true", help="print machine-readable JSON")

    a = ap.parse_args(argv)

    if a.cmd == "serve":
        srv = SpeedServer(a.host, a.port)
        print(f"netspeed server listening on {srv.host}:{srv.port} (tcp+udp); Ctrl-C to stop")
        srv.serve_forever()
        return 0

    if a.cmd == "test" and not a.allow_public and not _is_private(a.host):
        print(f"refusing to test public address {a.host!r}; netspeed is meant for your own "
              "machines. Pass --allow-public if you run that server.", file=sys.stderr)
        return 2

    try:
        if a.cmd == "demo":
            with SpeedServer("127.0.0.1", 0) as srv:
                res = run_tests(srv.host, srv.port, a.pings, a.duration, a.udp)
        else:
            res = run_tests(a.host, a.port, a.pings, a.duration, a.udp)
    except OSError as e:
        print(f"netspeed: {e}", file=sys.stderr)
        return 1

    print(json.dumps(res, indent=2) if a.json else render(res))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
