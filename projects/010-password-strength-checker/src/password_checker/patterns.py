"""Pattern detectors.

Each detector scans the password and yields :class:`Match` objects that
describe a substring and the number of bits an informed attacker needs to
guess it. Detectors are deliberately simple and readable.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Iterator

LEET = str.maketrans({"@": "a", "4": "a", "3": "e", "1": "i", "!": "i",
                      "0": "o", "$": "s", "5": "s", "7": "t", "+": "t"})

KEYBOARD_ROWS = ("`1234567890-=", "qwertyuiop[]\\", "asdfghjkl;'", "zxcvbnm,./")
SEQUENCES = ("abcdefghijklmnopqrstuvwxyz", "0123456789")


@dataclass(frozen=True)
class Match:
    kind: str
    start: int
    end: int  # exclusive
    token: str
    bits: float
    brute_bits: float  # cost of this span if brute-forced

    @property
    def saving(self) -> float:
        return self.brute_bits - self.bits


@lru_cache(maxsize=None)
def load_wordlist(name: str) -> dict[str, int]:
    """Load a bundled list as ``{word: rank}`` (rank 1 = most common)."""
    text = resources.files("password_checker.data").joinpath(name).read_text("utf-8")
    words = [w.strip().lower() for w in text.splitlines()
             if w.strip() and not w.startswith("#")]
    ranks: dict[str, int] = {}
    for i, w in enumerate(words, start=1):
        ranks.setdefault(w, i)
    return ranks


def _case_bits(token: str) -> float:
    """Extra bits for capitalisation variants of a lowercase word."""
    if token.islower() or not any(c.isalpha() for c in token):
        return 0.0
    if token[0].isupper() and token[1:].lower() == token[1:]:
        return 1.0  # Capitalised: very common, ~1 bit
    if token.isupper():
        return 1.0
    uppers = sum(c.isupper() for c in token)
    letters = sum(c.isalpha() for c in token)
    # choose which letters are uppercase
    return math.log2(sum(math.comb(letters, k) for k in range(1, min(uppers, letters - uppers) + 1)) or 1) + 1


def dictionary_matches(pw: str, per_char: float) -> Iterator[Match]:
    """Words from the common-password and dictionary lists, including leet-speak."""
    lists = (("common-password", load_wordlist("common_passwords.txt")),
             ("dictionary", load_wordlist("dictionary_words.txt")))
    lower = pw.lower()
    for i in range(len(pw)):
        for j in range(i + 3, len(pw) + 1):  # words of length >= 3
            raw = lower[i:j]
            plain = raw.translate(LEET)
            for kind, ranks in lists:
                leet = raw not in ranks
                rank = ranks.get(plain) if leet else ranks[raw]
                if rank is None:
                    continue
                bits = math.log2(rank + 1) + _case_bits(pw[i:j])
                if leet:
                    subs = sum(a != b for a, b in zip(raw, plain))
                    bits += subs  # ~1 bit per leet substitution
                    kind_name = f"{kind} (leet)"
                else:
                    kind_name = kind
                yield Match(kind_name, i, j, pw[i:j], bits, (j - i) * per_char)


def repeat_matches(pw: str, per_char: float) -> Iterator[Match]:
    """Runs of one character (``aaaa``) or a repeated chunk (``abcabc``)."""
    for m in re.finditer(r"(.+?)\1+", pw):
        unit, whole = m.group(1), m.group(0)
        count = len(whole) // len(unit)
        bits = len(unit) * per_char + math.log2(count)
        yield Match("repeat", m.start(), m.end(), whole, bits, len(whole) * per_char)


def sequence_matches(pw: str, per_char: float) -> Iterator[Match]:
    """Ascending/descending alphabet or digit runs of length >= 3."""
    lower = pw.lower()
    i = 0
    while i < len(pw) - 2:
        best = 0
        for seq in SEQUENCES:
            for s in (seq, seq[::-1]):
                k = s.find(lower[i:i + 3])
                if k < 0:
                    continue
                n = 3
                while i + n < len(pw) and k + n < len(s) and lower[i + n] == s[k + n]:
                    n += 1
                best = max(best, n)
        if best:
            # start char (~log2 36) + direction bit + length
            bits = math.log2(36) + 1 + math.log2(best)
            yield Match("sequence", i, i + best, pw[i:i + best], bits, best * per_char)
            i += best
        else:
            i += 1


def keyboard_matches(pw: str, per_char: float) -> Iterator[Match]:
    """Straight runs along a keyboard row, e.g. ``qwerty`` or ``asdf``."""
    lower = pw.lower()
    i = 0
    while i < len(pw) - 3:
        best = 0
        for row in KEYBOARD_ROWS:
            for r in (row, row[::-1]):
                k = r.find(lower[i:i + 4])
                if k < 0:
                    continue
                n = 4
                while i + n < len(pw) and k + n < len(r) and lower[i + n] == r[k + n]:
                    n += 1
                best = max(best, n)
        if best:
            bits = math.log2(47) + 1 + math.log2(best)  # start key, direction, length
            yield Match("keyboard", i, i + best, pw[i:i + best], bits, best * per_char)
            i += best
        else:
            i += 1


def year_matches(pw: str, per_char: float) -> Iterator[Match]:
    """Plausible years 1900-2099 — birthdays and graduation years are common."""
    for m in re.finditer(r"(?=((?:19|20)\d\d))", pw):
        start = m.start(1)
        yield Match("year", start, start + 4, m.group(1), math.log2(200), 4 * per_char)


DETECTORS = (dictionary_matches, repeat_matches, sequence_matches,
             keyboard_matches, year_matches)


def find_matches(pw: str, per_char: float) -> list[Match]:
    """Run every detector and collect all candidate matches."""
    out: list[Match] = []
    for detect in DETECTORS:
        out.extend(detect(pw, per_char))
    return out
