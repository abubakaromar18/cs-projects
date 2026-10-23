"""Rendering scan reports as a text table or JSON."""

from __future__ import annotations

import json

from .scanner import PortResult, PortState, ScanReport


def _row(r: PortResult) -> str:
    latency = f"{r.latency_ms:6.1f}ms" if r.latency_ms is not None else "      - "
    line = f"{r.port:>5}/tcp  {r.state.value:<8}  {r.service:<14} {latency}"
    if r.banner:
        line += f"  {r.banner[:60]}"
    return line


def render_text(report: ScanReport, *, show_all: bool = False) -> str:
    """Human-readable report. By default only open ports are listed."""
    t = report.target
    label = t.host if t.host == str(t.address) else f"{t.host} ({t.address})"
    lines = [f"Scan report for {label}"]

    shown = report.results if show_all else report.by_state(PortState.OPEN)
    if shown:
        lines.append(" PORT      STATE     SERVICE        LATENCY")
        lines.extend(_row(r) for r in shown)
    else:
        lines.append("No open ports found.")

    counts = report.counts()
    summary = ", ".join(f"{n} {s}" for s, n in counts.items() if n)
    lines.append(f"{len(report.results)} ports scanned in {report.elapsed_s:.2f}s: {summary}")
    return "\n".join(lines)


def to_dict(report: ScanReport) -> dict:
    return {
        "host": report.target.host,
        "address": str(report.target.address),
        "elapsed_s": round(report.elapsed_s, 4),
        "counts": report.counts(),
        "results": [
            {
                "port": r.port,
                "state": r.state.value,
                "service": r.service,
                "latency_ms": None if r.latency_ms is None else round(r.latency_ms, 3),
                "banner": r.banner,
                "detail": r.detail,
            }
            for r in report.results
        ],
    }


def render_json(report: ScanReport) -> str:
    return json.dumps(to_dict(report), indent=2)
