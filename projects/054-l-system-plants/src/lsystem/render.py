"""Render turtle segments to a standalone SVG document (no dependencies)."""

from __future__ import annotations

from .turtle import Segment, bounds


def _lerp_color(a: str, b: str, t: float) -> str:
    """Linearly interpolate between two '#rrggbb' colours."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    mixed = (round(x + (y - x) * t) for x, y in zip(ca, cb))
    return "#" + "".join(f"{v:02x}" for v in mixed)


def to_svg(segments: list[Segment], size: int = 800, margin: int = 20,
           trunk: str = "#5b3a1e", leaf: str = "#3fa34d",
           background: str = "#fbfaf5") -> str:
    """Fit the drawing into a ``size`` x ``size`` canvas.

    Line colour fades from ``trunk`` to ``leaf`` with branch depth, so the
    bracket structure of the grammar is visible in the picture.
    """
    min_x, min_y, max_x, max_y = bounds(segments)
    w, h = max_x - min_x, max_y - min_y
    scale = (size - 2 * margin) / max(w, h, 1e-9)
    # Centre the drawing; SVG's y axis points down, so flip y.
    ox = margin + ((size - 2 * margin) - w * scale) / 2
    oy = margin + ((size - 2 * margin) - h * scale) / 2
    max_depth = max((sg.depth for sg in segments), default=0) or 1

    def px(x: float) -> float:
        return ox + (x - min_x) * scale

    def py(y: float) -> float:
        return oy + (max_y - y) * scale

    lines = []
    for sg in segments:
        color = _lerp_color(trunk, leaf, sg.depth / max_depth)
        lines.append(
            f'<line x1="{px(sg.x1):.2f}" y1="{py(sg.y1):.2f}" '
            f'x2="{px(sg.x2):.2f}" y2="{py(sg.y2):.2f}" '
            f'stroke="{color}" stroke-width="{max(sg.width, 0.3):.2f}"/>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}">\n'
        f'<rect width="100%" height="100%" fill="{background}"/>\n'
        f'<g stroke-linecap="round">\n' + "\n".join(lines) + "\n</g>\n</svg>\n"
    )
