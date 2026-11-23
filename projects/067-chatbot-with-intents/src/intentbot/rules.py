"""Hand-written regex rules.

Rules are the "precision" half of the hybrid: when a pattern matches we
are certain of the intent and can pull out slots (a name, a number, a
math expression) with named groups. The classifier handles the long
tail of phrasings that no one wrote a rule for.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Match:
    intent: str
    slots: dict[str, str] = field(default_factory=dict)
    rule: str = ""


@dataclass
class Rule:
    intent: str
    pattern: str
    priority: int = 0
    _compiled: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._compiled = re.compile(self.pattern, re.IGNORECASE)

    def match(self, text: str) -> Match | None:
        m = self._compiled.search(text)
        if not m:
            return None
        slots = {k: v.strip() for k, v in m.groupdict().items() if v}
        return Match(self.intent, slots, self.pattern)


class RuleEngine:
    """Ordered rule set: highest priority wins, ties go to definition order."""

    def __init__(self, rules: list[Rule] | None = None):
        self.rules: list[Rule] = []
        for r in rules or []:
            self.add(r)

    def add(self, rule: Rule) -> None:
        self.rules.append(rule)
        # sort() is stable, so equal priorities keep insertion order.
        self.rules.sort(key=lambda r: -r.priority)

    def match(self, text: str) -> Match | None:
        for rule in self.rules:
            m = rule.match(text)
            if m:
                return m
        return None

    @classmethod
    def from_specs(cls, specs: list[dict]) -> "RuleEngine":
        return cls([Rule(s["intent"], s["pattern"], s.get("priority", 0)) for s in specs])
