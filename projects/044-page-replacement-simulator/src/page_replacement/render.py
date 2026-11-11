"""Plain-text rendering: textbook-style traces, tables and bar charts."""

from __future__ import annotations

from typing import Sequence

from .simulator import Result


def _cell(value, width: int) -> str:
    return ("-" if value is None else str(value)).rjust(width)


def trace_grid(result: Result) -> str:
    """The grid you draw on a whiteboard: one column per reference, one row per
    frame, faults marked with ``*`` and evictions listed underneath."""
    steps = result.steps
    w = max([len(str(p)) for p in result.refs] + [1]) + 1
    lines = ["ref   " + "".join(_cell(s.page, w) for s in steps)]
    for slot in range(result.frames):
        row = "".join(
            # Only redraw a frame cell when it changed — the textbook style —
            # but always draw on a fault so the new page is visible.
            _cell(s.frames[slot], w) if (not s.hit and s.slot == slot) or t == 0
            or s.frames[slot] != steps[t - 1].frames[slot]
            else " " * (w - 1) + "."
            for t, s in enumerate(steps)
        )
        lines.append(f"f{slot:<4} {row}")
    lines.append("fault " + "".join(("*" if not s.hit else "").rjust(w) for s in steps))
    lines.append(
        f"{result.algorithm.upper()}: {result.faults} faults, {result.hits} hits "
        f"({result.hit_ratio:.0%} hit ratio) with {result.frames} frames"
    )
    return "\n".join(lines)


def trace_steps(result: Result) -> str:
    """One line per reference, with policy state — useful for Clock."""
    out = []
    for s in result.steps:
        frames = " ".join(_cell(p, 2) for p in s.frames)
        what = "hit  " if s.hit else "FAULT"
        ev = f" evict {s.evicted}" if s.evicted is not None else ""
        note = f"  [{s.note}]" if s.note else ""
        out.append(f"t={s.t:<3} ref {s.page!s:>3}  {what} [{frames} ]{ev}{note}")
    return "\n".join(out)


def comparison_table(results: Sequence[Result]) -> str:
    """Side-by-side summary, with each algorithm's gap to OPT if present."""
    opt = next((r.faults for r in results if r.algorithm == "opt"), None)
    header = f"{'algorithm':<10}{'faults':>8}{'hits':>8}{'hit %':>8}"
    if opt is not None:
        header += f"{'vs OPT':>9}"
    rows = [header, "-" * len(header)]
    for r in sorted(results, key=lambda r: (r.faults, r.algorithm)):
        row = f"{r.algorithm:<10}{r.faults:>8}{r.hits:>8}{r.hit_ratio:>8.1%}"
        if opt is not None:
            row += f"{'+' + str(r.faults - opt) if r.faults > opt else '=':>9}"
        rows.append(row)
    return "\n".join(rows)


def sweep_table(curves: dict[str, dict[int, int]]) -> str:
    ks = sorted({k for c in curves.values() for k in c})
    header = f"{'frames':<10}" + "".join(f"{a:>8}" for a in curves)
    rows = [header, "-" * len(header)]
    for k in ks:
        rows.append(f"{k:<10}" + "".join(f"{curves[a][k]:>8}" for a in curves))
    return "\n".join(rows)


def bar_chart(curves: dict[str, dict[int, int]], width: int = 40) -> str:
    """Horizontal bars of faults per frame count, grouped by frame count."""
    peak = max((v for c in curves.values() for v in c.values()), default=0) or 1
    ks = sorted({k for c in curves.values() for k in c})
    label = max(len(a) for a in curves)
    out = []
    for k in ks:
        out.append(f"{k} frame{'s' if k != 1 else ''}:")
        for algo, curve in curves.items():
            n = curve[k]
            bar = "#" * max(1, round(n / peak * width)) if n else ""
            out.append(f"  {algo:<{label}} {bar} {n}")
    return "\n".join(out)
