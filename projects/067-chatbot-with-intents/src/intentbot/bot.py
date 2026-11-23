"""The hybrid bot: rules -> classifier -> fallback.

Routing order for each message:

1. **Rules.** A regex match is trusted outright (confidence 1.0) and
   may carry slots extracted by named groups.
2. **Classifier.** Naive Bayes picks the most probable intent.
3. **Fallback.** If the classifier's probability is below
   ``threshold`` or too few of the words were seen in training, the bot
   admits it didn't understand rather than guessing.

Intent-specific behaviour (doing the math, reading the clock, using the
remembered name) lives in small handler functions that turn the raw
match into template variables.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from importlib import resources
from pathlib import Path
from typing import Callable

from . import calc
from .classifier import NaiveBayesClassifier
from .rules import RuleEngine

FALLBACK_RESPONSES = [
    "Sorry, I didn't catch that. Try asking 'what can you do?'",
    "I'm not sure what you mean. Could you rephrase?",
]


@dataclass
class Reply:
    text: str
    intent: str  # "fallback" when nothing was confident enough
    confidence: float
    source: str  # "rule", "classifier" or "fallback"
    slots: dict[str, str] = field(default_factory=dict)


@dataclass
class Context:
    """Per-conversation memory."""

    name: str | None = None
    last_intent: str | None = None
    turns: int = 0


Handler = Callable[[dict[str, str], Context], dict[str, str] | str]


def load_spec(path: str | Path | None = None) -> dict:
    if path is None:
        text = resources.files("intentbot").joinpath("data/intents.json").read_text(encoding="utf-8")
    else:
        text = Path(path).read_text(encoding="utf-8")
    return json.loads(text)


def training_examples(spec: dict) -> list[tuple[str, str]]:
    """(text, intent) pairs for the classifier.

    Intents flagged ``rule_only`` need slots that only a regex can
    extract (a math expression, a name), so they are never predicted
    by the classifier.
    """
    return [
        (ex, name)
        for name, data in spec["intents"].items()
        if not data.get("rule_only")
        for ex in data.get("examples", [])
    ]


class ChatBot:
    def __init__(
        self,
        spec: dict | None = None,
        *,
        threshold: float = 0.45,
        min_known: float = 0.5,
        alpha: float = 0.3,
        seed: int | None = None,
        clock: Callable[[], datetime] = datetime.now,
    ):
        spec = spec if spec is not None else load_spec()
        self.intents: dict[str, dict] = spec["intents"]
        self.rules = RuleEngine.from_specs(spec.get("rules", []))
        # Small alpha: with tiny per-intent vocabularies, alpha=1 smooths
        # so hard that a single strong keyword ("hi") can't win.
        self.classifier = NaiveBayesClassifier(alpha=alpha).fit(training_examples(spec))
        self.threshold = threshold
        self.min_known = min_known
        self.rng = random.Random(seed)
        self.clock = clock
        self.context = Context()
        self.handlers: dict[str, Handler] = {
            "math": self._handle_math,
            "time": self._handle_time,
            "set_name": self._handle_set_name,
            "ask_my_name": self._handle_ask_name,
        }

    # ---- routing --------------------------------------------------------

    def classify(self, text: str) -> tuple[str, float, str, dict[str, str]]:
        """Return (intent, confidence, source, slots) without responding."""
        m = self.rules.match(text)
        if m:
            return m.intent, 1.0, "rule", m.slots
        intent, p = self.classifier.predict(text)
        if p < self.threshold or self.classifier.known_fraction(text) < self.min_known:
            return "fallback", p, "fallback", {}
        return intent, p, "classifier", {}

    def respond(self, text: str) -> Reply:
        self.context.turns += 1
        if not text.strip():
            return Reply("Say something and I'll do my best!", "fallback", 0.0, "fallback")

        intent, conf, source, slots = self.classify(text)
        if intent == "fallback":
            return Reply(self.rng.choice(FALLBACK_RESPONSES), intent, conf, source)

        handler = self.handlers.get(intent)
        variables: dict[str, str] = dict(slots)
        if handler:
            out = handler(slots, self.context)
            if isinstance(out, str):  # handler produced the full reply itself
                self.context.last_intent = intent
                return Reply(out, intent, conf, source, slots)
            variables.update(out)

        variables.setdefault("name", self.context.name or "friend")
        variables.setdefault("name_suffix", f", {self.context.name}" if self.context.name else "")
        template = self.rng.choice(self.intents[intent]["responses"])
        self.context.last_intent = intent
        return Reply(template.format(**variables), intent, conf, source, slots)

    # ---- handlers -------------------------------------------------------

    @staticmethod
    def _handle_math(slots: dict[str, str], ctx: Context) -> dict[str, str] | str:
        expr = slots.get("expr")
        if not expr:
            return "Give me an expression, like 'what is 12 * 4'."
        try:
            result = calc.evaluate(expr)
        except calc.CalcError as e:
            return f"I couldn't compute that: {e}."
        if isinstance(result, float):
            result = int(result) if result.is_integer() else round(result, 6)
        return {"expr": expr, "result": str(result)}

    def _handle_time(self, slots: dict[str, str], ctx: Context) -> dict[str, str]:
        return {"time": self.clock().strftime("%H:%M")}

    @staticmethod
    def _handle_set_name(slots: dict[str, str], ctx: Context) -> dict[str, str] | str:
        name = slots.get("name")
        if not name:
            return "What should I call you? Try 'my name is ...'."
        ctx.name = name.capitalize()
        return {"name": ctx.name}

    @staticmethod
    def _handle_ask_name(slots: dict[str, str], ctx: Context) -> dict[str, str] | str:
        if not ctx.name:
            return "I don't know your name yet. Tell me with 'my name is ...'."
        return {"name": ctx.name}
