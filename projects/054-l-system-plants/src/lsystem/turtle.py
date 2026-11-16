"""Turtle interpretation of an L-system string.

Each symbol is read as a command for a "turtle" (a pen with a position and a
heading). Brackets push/pop the turtle state on a stack, which is how a single
linear string encodes a branching tree structure.

Symbol alphabet:

=======  ==============================================
F, G     move forward ``step`` and draw a line
f        move forward without drawing
+ / -    turn left / right by ``angle`` degrees
|        turn around (180 degrees)
[ / ]    push / pop the turtle state (start/end a branch)
!        shrink line width by ``width_decay``
other    ignored (e.g. X, Y used only for rewriting)
=======  ==============================================
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    """One drawn line, plus the branch depth it was drawn at (for colouring)."""

    x1: float
    y1: float
    x2: float
    y2: float
    depth: int
    width: float


@dataclass
class _State:
    x: float
    y: float
    heading: float  # degrees; 90 = straight up
    depth: int
    width: float
    step: float


@dataclass
class TurtleConfig:
    angle: float = 25.0
    step: float = 10.0
    start_heading: float = 90.0
    start_width: float = 2.0
    width_decay: float = 0.7
    length_decay: float = 1.0  # multiply step on each '[' (1.0 = no change)
    angle_jitter: float = 0.0  # +/- degrees of random variation per turn
    seed: int | None = 0


DRAW = frozenset("FG")


def interpret(commands: str, cfg: TurtleConfig | None = None) -> list[Segment]:
    """Walk ``commands`` and return the list of drawn segments.

    Runs in O(n) time with O(d) stack space, where d is max branch depth.
    """
    cfg = cfg or TurtleConfig()
    rng = random.Random(cfg.seed)
    s = _State(0.0, 0.0, cfg.start_heading, 0, cfg.start_width, cfg.step)
    stack: list[_State] = []
    out: list[Segment] = []

    def turn(sign: int) -> None:
        jitter = rng.uniform(-cfg.angle_jitter, cfg.angle_jitter) if cfg.angle_jitter else 0.0
        s.heading += sign * cfg.angle + jitter

    for ch in commands:
        if ch in DRAW or ch == "f":
            rad = math.radians(s.heading)
            nx = s.x + s.step * math.cos(rad)
            ny = s.y + s.step * math.sin(rad)
            if ch != "f":
                out.append(Segment(s.x, s.y, nx, ny, s.depth, s.width))
            s.x, s.y = nx, ny
        elif ch == "+":
            turn(+1)
        elif ch == "-":
            turn(-1)
        elif ch == "|":
            s.heading += 180.0
        elif ch == "[":
            stack.append(_State(**vars(s)))
            s.depth += 1
            s.step *= cfg.length_decay
        elif ch == "]":
            if not stack:
                raise ValueError("unbalanced ']' in command string")
            s = stack.pop()
        elif ch == "!":
            s.width *= cfg.width_decay
    return out


def bounds(segments: list[Segment]) -> tuple[float, float, float, float]:
    """Axis-aligned bounding box (min_x, min_y, max_x, max_y)."""
    if not segments:
        return (0.0, 0.0, 0.0, 0.0)
    xs = [v for sg in segments for v in (sg.x1, sg.x2)]
    ys = [v for sg in segments for v in (sg.y1, sg.y2)]
    return (min(xs), min(ys), max(xs), max(ys))
