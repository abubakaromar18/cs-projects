"""Entropy estimation.

Two estimates are computed:

* **Naive (charset) entropy** — ``len(password) * log2(pool_size)``, where the
  pool is the union of character classes used. This is what most "strength
  meters" show and it badly overestimates passwords like ``Password1!``.

* **Pattern-aware entropy** — the password is greedily segmented into
  recognisable patterns (dictionary words, leet-speak words, sequences,
  repeats, keyboard walks, years). Each pattern is charged only the bits an
  attacker who *knows that pattern* would need to guess it; leftover
  characters are charged at brute-force cost. This mirrors the idea behind
  Dropbox's zxcvbn, in a much smaller form.
"""

from __future__ import annotations

import math
import string
from dataclasses import dataclass

from .patterns import Match, find_matches

# Character classes and their sizes.
CHAR_CLASSES: dict[str, int] = {
    "lowercase": 26,
    "uppercase": 26,
    "digits": 10,
    "symbols": 33,  # printable ASCII punctuation + space
}


def char_classes(password: str) -> set[str]:
    """Return the set of character-class names present in *password*."""
    found: set[str] = set()
    for ch in password:
        if ch in string.ascii_lowercase:
            found.add("lowercase")
        elif ch in string.ascii_uppercase:
            found.add("uppercase")
        elif ch in string.digits:
            found.add("digits")
        else:
            found.add("symbols")
    return found


def pool_size(password: str) -> int:
    """Size of the brute-force alphabet implied by the characters used."""
    return sum(CHAR_CLASSES[c] for c in char_classes(password))


def naive_entropy(password: str) -> float:
    """Classic ``L * log2(N)`` entropy in bits."""
    if not password:
        return 0.0
    return len(password) * math.log2(pool_size(password))


@dataclass(frozen=True)
class EntropyReport:
    naive_bits: float
    effective_bits: float
    matches: tuple[Match, ...]


def _select_non_overlapping(matches: list[Match]) -> list[Match]:
    """Pick a set of non-overlapping matches that saves the most bits.

    Classic weighted-interval scheduling via dynamic programming: each match
    is worth ``brute_cost(span) - match.bits``; we maximise the total saving.
    """
    if not matches:
        return []
    ms = sorted(matches, key=lambda m: m.end)
    n = len(ms)
    # best[i] = (saving, chosen) using the first i matches
    best: list[tuple[float, list[Match]]] = [(0.0, [])] * (n + 1)
    for i, m in enumerate(ms, start=1):
        # latest match ending at or before m.start
        j = i - 1
        while j > 0 and ms[j - 1].end > m.start:
            j -= 1
        take_saving = best[j][0] + m.saving
        if take_saving > best[i - 1][0]:
            best[i] = (take_saving, best[j][1] + [m])
        else:
            best[i] = best[i - 1]
    return sorted(best[n][1], key=lambda m: m.start)


def estimate(password: str) -> EntropyReport:
    """Return naive and pattern-aware entropy for *password*."""
    naive = naive_entropy(password)
    if not password:
        return EntropyReport(0.0, 0.0, ())

    per_char = math.log2(pool_size(password))
    chosen = _select_non_overlapping(
        [m for m in find_matches(password, per_char) if m.saving > 0]
    )

    covered = sum(m.end - m.start for m in chosen)
    leftover = len(password) - covered
    bits = leftover * per_char + sum(m.bits for m in chosen)
    # Combining k independent pieces adds some uncertainty about their order.
    pieces = len(chosen) + (1 if leftover else 0)
    if pieces > 1:
        bits += math.log2(pieces)
    return EntropyReport(naive, min(bits, naive), tuple(chosen))
