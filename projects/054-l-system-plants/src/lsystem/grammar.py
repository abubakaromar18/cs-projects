"""L-system grammars: parallel string rewriting.

An L-system (Lindenmayer system) is a formal grammar where *every* symbol of
the current string is rewritten simultaneously at each step. This parallelism
is what distinguishes it from a Chomsky grammar, and it models how all cells
of a plant grow at the same time.

Two flavours are supported:

* **Deterministic (D0L)** - each symbol has at most one replacement.
* **Stochastic** - a symbol may have several weighted replacements; one is
  chosen at random per occurrence. A seeded RNG keeps results reproducible.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Mapping, Sequence, Union

# A rule's right-hand side is either one string, or a list of (weight, string)
# alternatives for a stochastic rule.
RuleSpec = Union[str, Sequence[tuple[float, str]]]


class GrammarError(ValueError):
    """Raised for malformed grammars (bad weights, unbalanced brackets...)."""


def _check_brackets(text: str, where: str) -> None:
    """Ensure '[' and ']' are balanced - an unbalanced branch would corrupt the
    turtle's state stack at render time, so we reject it up front."""
    depth = 0
    for ch in text:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth < 0:
                raise GrammarError(f"unmatched ']' in {where}: {text!r}")
    if depth:
        raise GrammarError(f"unclosed '[' in {where}: {text!r}")


@dataclass
class LSystem:
    """An axiom plus a set of production rules.

    ``rules`` maps a single-character predecessor to its successor(s).
    Symbols with no rule are copied unchanged (identity production).
    """

    axiom: str
    rules: Mapping[str, RuleSpec]
    _table: dict[str, list[tuple[float, str]]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.axiom:
            raise GrammarError("axiom must be non-empty")
        _check_brackets(self.axiom, "axiom")
        self._table = {}
        for pred, spec in self.rules.items():
            if len(pred) != 1:
                raise GrammarError(f"predecessor must be one symbol, got {pred!r}")
            alts = [(1.0, spec)] if isinstance(spec, str) else list(spec)
            if not alts:
                raise GrammarError(f"rule for {pred!r} has no alternatives")
            for weight, succ in alts:
                if weight <= 0:
                    raise GrammarError(f"weights must be positive (rule {pred!r})")
                _check_brackets(succ, f"rule {pred!r}")
            self._table[pred] = alts

    @property
    def is_stochastic(self) -> bool:
        return any(len(alts) > 1 for alts in self._table.values())

    def _rewrite_symbol(self, ch: str, rng: random.Random) -> str:
        alts = self._table.get(ch)
        if alts is None:
            return ch
        if len(alts) == 1:
            return alts[0][1]
        weights = [w for w, _ in alts]
        return rng.choices([s for _, s in alts], weights=weights, k=1)[0]

    def step(self, text: str, rng: random.Random | None = None) -> str:
        """Apply one parallel rewriting step to ``text``."""
        rng = rng or random.Random(0)
        # Building a list and joining once is O(n); repeated str += would be
        # quadratic in the worst case.
        return "".join(self._rewrite_symbol(ch, rng) for ch in text)

    def generate(self, iterations: int, seed: int | None = 0,
                 max_length: int = 2_000_000) -> str:
        """Expand the axiom ``iterations`` times.

        L-system strings grow exponentially, so ``max_length`` guards against
        accidentally exhausting memory.
        """
        if iterations < 0:
            raise ValueError("iterations must be >= 0")
        rng = random.Random(seed)
        text = self.axiom
        for i in range(iterations):
            text = self.step(text, rng)
            if len(text) > max_length:
                raise GrammarError(
                    f"string exceeded {max_length:,} symbols at iteration {i + 1}; "
                    "use fewer iterations"
                )
        return text


def parse_rules(lines: Sequence[str]) -> dict[str, RuleSpec]:
    """Parse rules written as ``X=successor`` or stochastic
    ``X=0.5:succA|0.5:succB``. Used by the CLI's ``--rule`` flag."""
    rules: dict[str, list[tuple[float, str]]] = {}
    for line in lines:
        if "=" not in line:
            raise GrammarError(f"rule must look like X=..., got {line!r}")
        pred, rhs = line.split("=", 1)
        pred = pred.strip()
        for part in rhs.split("|"):
            weight, succ = 1.0, part
            if ":" in part:
                w, succ = part.split(":", 1)
                try:
                    weight = float(w)
                except ValueError as exc:
                    raise GrammarError(f"bad weight {w!r} in {line!r}") from exc
            rules.setdefault(pred, []).append((weight, succ.strip()))
    return {k: (v[0][1] if len(v) == 1 else v) for k, v in rules.items()}
