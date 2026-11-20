"""Render mazes as ASCII art or SVG."""

from __future__ import annotations

from typing import Iterable

from .maze import Cell, Maze


def to_ascii(maze: Maze, path: Iterable[Cell] = ()) -> str:
    """Classic ``+--+`` style drawing. Cells on ``path`` are marked with ``*``;
    the start and end are marked ``S`` and ``E``."""
    on_path = set(path)
    lines = ["+" + "---+" * maze.cols]
    for r in range(maze.rows):
        body, floor = ["|"], ["+"]
        for c in range(maze.cols):
            cell = (r, c)
            mark = " "
            if cell == maze.start:
                mark = "S"
            elif cell == maze.end:
                mark = "E"
            elif cell in on_path:
                mark = "*"
            body.append(f" {mark} ")
            right = (r, c + 1)
            body.append(" " if c + 1 < maze.cols and maze.is_open(cell, right) else "|")
            below = (r + 1, c)
            floor.append("   " if r + 1 < maze.rows and maze.is_open(cell, below) else "---")
            floor.append("+")
        lines.append("".join(body))
        lines.append("".join(floor))
    return "\n".join(lines)


def to_svg(maze: Maze, path: Iterable[Cell] = (), cell_size: int = 20) -> str:
    """Standalone SVG with walls as line segments and the path as a polyline."""
    s = cell_size
    pad = s // 2
    w, h = maze.cols * s + 2 * pad, maze.rows * s + 2 * pad
    segs = []

    def line(x1, y1, x2, y2):
        segs.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')

    # Outer border, then each cell's right and bottom wall where closed.
    line(pad, pad, pad + maze.cols * s, pad)
    line(pad, pad, pad, pad + maze.rows * s)
    for r, c in maze.cells():
        x, y = pad + c * s, pad + r * s
        if not (c + 1 < maze.cols and maze.is_open((r, c), (r, c + 1))):
            line(x + s, y, x + s, y + s)
        if not (r + 1 < maze.rows and maze.is_open((r, c), (r + 1, c))):
            line(x, y + s, x + s, y + s)

    path = list(path)
    poly = ""
    if path:
        pts = " ".join(f"{pad + c * s + s / 2},{pad + r * s + s / 2}" for r, c in path)
        poly = (f'<polyline points="{pts}" fill="none" stroke="#d6336c" '
                f'stroke-width="{max(s // 4, 1)}" stroke-linecap="round" '
                f'stroke-linejoin="round"/>')

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">\n'
        f'<rect width="100%" height="100%" fill="white"/>\n'
        f'{poly}\n'
        f'<g stroke="black" stroke-width="2" stroke-linecap="square">\n'
        + "\n".join(segs)
        + "\n</g>\n</svg>\n"
    )
