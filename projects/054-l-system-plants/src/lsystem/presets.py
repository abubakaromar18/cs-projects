"""Classic plant grammars, mostly from Prusinkiewicz & Lindenmayer,
*The Algorithmic Beauty of Plants* (1990), figure 1.24."""

from __future__ import annotations

from dataclasses import dataclass, field

from .grammar import LSystem, RuleSpec
from .turtle import TurtleConfig


@dataclass(frozen=True)
class Preset:
    description: str
    axiom: str
    rules: dict[str, RuleSpec]
    iterations: int
    turtle: TurtleConfig = field(default_factory=TurtleConfig)

    def lsystem(self) -> LSystem:
        return LSystem(self.axiom, self.rules)


PRESETS: dict[str, Preset] = {
    "fern": Preset(
        "Fractal fern (ABOP 1.24f)",
        "X", {"X": "F+[[!X]-!X]-F[-!FX]+!X", "F": "FF"}, 5,
        TurtleConfig(angle=22.5, start_heading=75, start_width=3),
    ),
    "bush": Preset(
        "Bushy plant (ABOP 1.24d)",
        "F", {"F": "FF-[!-F+F+F]+[!+F-F-F]"}, 4,
        TurtleConfig(angle=22.5, start_width=3),
    ),
    "weed": Preset(
        "Edge-rewritten weed (ABOP 1.24a)",
        "F", {"F": "F[+F]F[-F]F"}, 5,
        TurtleConfig(angle=25.7, start_width=1.5),
    ),
    "tree": Preset(
        "Node-rewritten tree with shrinking branches (ABOP 1.24e)",
        "X", {"X": "F[+!X][-!X]F!X", "F": "FF"}, 6,
        TurtleConfig(angle=20, start_width=4, width_decay=0.75),
    ),
    "random-shrub": Preset(
        "Stochastic shrub - each run with a new seed grows a different plant",
        "F",
        {"F": [(0.33, "F[+!F]F[-!F]F"), (0.33, "F[+!F]F"), (0.34, "F[-!F]F")]},
        5,
        TurtleConfig(angle=25, start_width=3, angle_jitter=6),
    ),
}
