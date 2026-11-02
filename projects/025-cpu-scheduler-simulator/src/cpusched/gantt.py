"""Render a Schedule as a Gantt chart: ASCII for the terminal, SVG for files.

ASCII example::

    +----+--------+----+
    | P1 |   P2   | P1 |
    +----+--------+----+
    0    2        6    8
"""

from __future__ import annotations

from html import escape

from .models import Schedule, Slice

IDLE_LABEL = "idle"


def _label(s: Slice, show_levels: bool) -> str:
    if s.idle:
        return IDLE_LABEL
    return f"{s.pid}@{s.level}" if show_levels and s.level is not None else str(s.pid)


def ascii_gantt(schedule: Schedule, scale: int = 2, show_levels: bool = False) -> str:
    """Return a three-line ASCII Gantt chart plus a time axis.

    Each time unit gets ``scale`` columns, but a bar is widened if needed so
    its label and the time tick under its left edge always fit.
    """
    if not schedule.slices:
        return "(empty schedule)"
    border, middle, axis = "+", "|", ""
    for s in schedule.slices:
        label = _label(s, show_levels)
        tick = str(s.start)
        width = max(s.duration * scale, len(label) + 2, len(tick) + 1)
        border += "-" * width + "+"
        middle += label.center(width) + "|"
        axis += tick.ljust(width + 1)
    axis += str(schedule.slices[-1].end)
    return "\n".join([border, middle, border, axis])


# A small colour-blind-friendly palette; processes cycle through it.
_PALETTE = ["#4e79a7", "#f28e2b", "#59a14f", "#e15759", "#76b7b2",
            "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac"]


def svg_gantt(schedule: Schedule, unit: int = 24, row_height: int = 28) -> str:
    """Return a standalone SVG Gantt chart with one row per process.

    Rows make preemption easy to see: a process that is interrupted shows
    several separate bars on its row.
    """
    pids = [p.pid for p in schedule.processes]
    colour = {pid: _PALETTE[i % len(_PALETTE)] for i, pid in enumerate(pids)}
    left, top = 70, 34
    width = left + schedule.makespan * unit + 20
    height = top + len(pids) * row_height + 30

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'font-family="monospace" font-size="12">',
        f'<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{left}" y="18" font-size="14" font-weight="bold">{escape(schedule.algorithm)}</text>',
    ]
    for row, pid in enumerate(pids):
        y = top + row * row_height
        out.append(f'<text x="8" y="{y + row_height * 0.65:.0f}">{escape(pid)}</text>')
    for s in schedule.slices:
        if s.idle:
            continue
        row = pids.index(s.pid)
        x = left + s.start * unit
        y = top + row * row_height + 3
        title = f"{s.pid}: {s.start}-{s.end}" + (f" (level {s.level})" if s.level is not None else "")
        out.append(
            f'<rect x="{x}" y="{y}" width="{s.duration * unit}" height="{row_height - 6}" '
            f'fill="{colour[s.pid]}" stroke="black" stroke-width="0.5">'
            f'<title>{escape(title)}</title></rect>'
        )
        if s.level is not None and s.duration * unit >= 20:
            out.append(f'<text x="{x + 4}" y="{y + row_height * 0.6:.0f}" fill="white">L{s.level}</text>')
    # Time axis with a tick at every slice boundary.
    axis_y = top + len(pids) * row_height + 4
    out.append(f'<line x1="{left}" y1="{axis_y}" x2="{left + schedule.makespan * unit}" '
               f'y2="{axis_y}" stroke="black"/>')
    ticks = sorted({0, *(s.start for s in schedule.slices), schedule.makespan})
    for t in ticks:
        x = left + t * unit
        out.append(f'<line x1="{x}" y1="{axis_y}" x2="{x}" y2="{axis_y + 5}" stroke="black"/>')
        out.append(f'<text x="{x}" y="{axis_y + 18}" text-anchor="middle">{t}</text>')
    out.append("</svg>")
    return "\n".join(out)
