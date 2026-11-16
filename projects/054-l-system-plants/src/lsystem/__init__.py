"""L-system plant generator: grammar rewriting + turtle graphics + SVG output."""

from .grammar import GrammarError, LSystem, parse_rules
from .presets import PRESETS, Preset
from .render import to_svg
from .turtle import Segment, TurtleConfig, bounds, interpret

__all__ = ["GrammarError", "LSystem", "parse_rules", "PRESETS", "Preset",
           "to_svg", "Segment", "TurtleConfig", "bounds", "interpret"]
__version__ = "1.0.0"
