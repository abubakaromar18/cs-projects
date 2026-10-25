"""Turn entropy and breach results into a score, crack-time estimate and advice."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .breach import in_local_list
from .entropy import EntropyReport, char_classes, estimate

LABELS = ("very weak", "weak", "fair", "strong", "very strong")

# Guesses per second for two attacker models.
ONLINE_THROTTLED = 100            # rate-limited login form
OFFLINE_FAST_HASH = 1e10          # GPU rig vs. unsalted fast hash


@dataclass
class Result:
    length: int
    score: int
    label: str
    entropy: EntropyReport
    breached: bool
    pwned_count: int | None = None
    feedback: list[str] = field(default_factory=list)

    def crack_seconds(self, rate: float) -> float:
        # On average an attacker searches half the space.
        return 2 ** self.entropy.effective_bits / 2 / rate

    def to_dict(self) -> dict:
        return {
            "length": self.length,
            "score": self.score,
            "label": self.label,
            "naive_entropy_bits": round(self.entropy.naive_bits, 1),
            "effective_entropy_bits": round(self.entropy.effective_bits, 1),
            "breached": self.breached,
            "pwned_count": self.pwned_count,
            "crack_time_online": human_time(self.crack_seconds(ONLINE_THROTTLED)),
            "crack_time_offline": human_time(self.crack_seconds(OFFLINE_FAST_HASH)),
            "patterns": [{"kind": m.kind, "token": m.token} for m in self.entropy.matches],
            "feedback": self.feedback,
        }


def human_time(seconds: float) -> str:
    """Format a duration roughly, e.g. ``3 hours`` or ``centuries``."""
    if seconds < 1:
        return "instant"
    units = (("year", 31_557_600), ("day", 86_400), ("hour", 3_600),
             ("minute", 60), ("second", 1))
    if seconds >= 100 * 31_557_600:
        return "centuries"
    for name, size in units:
        if seconds >= size:
            n = int(seconds // size)
            return f"{n} {name}{'s' if n != 1 else ''}"
    return "instant"  # pragma: no cover


def bits_to_score(bits: float) -> int:
    """Map effective entropy to a 0-4 score."""
    for score, threshold in enumerate((28, 36, 60, 80)):
        if bits < threshold:
            return score
    return 4


def _feedback(pw: str, report: EntropyReport, breached: bool) -> list[str]:
    tips: list[str] = []
    if breached:
        tips.append("This password appears in a breach list — never use it.")
    if len(pw) < 12:
        tips.append("Use at least 12 characters; length matters more than symbols.")
    kinds = {m.kind.split(" ")[0] for m in report.matches}
    if kinds & {"dictionary", "common-password"}:
        tips.append("Avoid common words and passwords, even with l33t substitutions.")
    if "sequence" in kinds or "keyboard" in kinds:
        tips.append("Avoid sequences like 'abc', '123' or keyboard walks like 'qwerty'.")
    if "repeat" in kinds:
        tips.append("Avoid repeated characters or chunks.")
    if "year" in kinds:
        tips.append("Avoid years and dates; they are easy to guess.")
    if len(char_classes(pw)) < 3 and len(pw) < 16:
        tips.append("Mix character types, or use a longer passphrase of random words.")
    if not tips and bits_to_score(report.effective_bits) < 4:
        tips.append("Add a few more random characters or words.")
    return tips


def check(password: str, extra_list: Path | None = None,
          pwned: int | None = None) -> Result:
    """Analyse *password*. *pwned* is an optional HIBP count fetched by the caller."""
    report = estimate(password)
    breached = in_local_list(password, extra_list) or bool(pwned)
    score = 0 if breached else bits_to_score(report.effective_bits)
    return Result(
        length=len(password),
        score=score,
        label=LABELS[score],
        entropy=report,
        breached=breached,
        pwned_count=pwned,
        feedback=_feedback(password, report, breached),
    )
