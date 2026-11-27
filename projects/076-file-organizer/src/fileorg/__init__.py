"""fileorg: sort files into folders by type and/or date, safely.

The package is split into three layers:

* :mod:`fileorg.rules`    - pure classification (extension -> category)
* :mod:`fileorg.planner`  - pure planning (directory listing -> list of moves)
* :mod:`fileorg.executor` - side effects (perform moves, journal, undo)

Keeping planning free of side effects is what makes ``--dry-run`` trustworthy:
the dry run prints exactly the plan the real run would execute.
"""

from .rules import DEFAULT_RULES, Rules, load_rules
from .planner import Move, Plan, plan_moves
from .executor import apply_plan, undo

__all__ = [
    "DEFAULT_RULES",
    "Rules",
    "load_rules",
    "Move",
    "Plan",
    "plan_moves",
    "apply_plan",
    "undo",
]
__version__ = "1.0.0"
