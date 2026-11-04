"""Letter statistics used to tell English from gibberish.

* chi-squared distance between observed letter counts and English frequencies
* index of coincidence (IoC): the probability that two random letters match.
  English is about 0.066; uniformly random letters give 1/26 ~= 0.0385.
  Monoalphabetic ciphers (Caesar) preserve IoC; polyalphabetic ones flatten it.
"""

from __future__ import annotations

import math
from collections import Counter

from .ciphers import ALPHABET

# Relative letter frequencies of English text (percent), A..Z.
ENGLISH_FREQ: dict[str, float] = dict(zip(ALPHABET, [
    8.167, 1.492, 2.782, 4.253, 12.702, 2.228, 2.015, 6.094, 6.966, 0.153,
    0.772, 4.025, 2.406, 6.749, 7.507, 1.929, 0.095, 5.987, 6.327, 9.056,
    2.758, 0.978, 2.360, 0.150, 1.974, 0.074,
]))
_TOTAL = sum(ENGLISH_FREQ.values())
ENGLISH_PROB: dict[str, float] = {k: v / _TOTAL for k, v in ENGLISH_FREQ.items()}

ENGLISH_IOC = sum(p * p for p in ENGLISH_PROB.values())  # ~0.0655
RANDOM_IOC = 1 / 26


def letters_only(text: str) -> str:
    """Uppercase ASCII letters of `text`, everything else dropped."""
    return "".join(c for c in text.upper() if c in ALPHABET)


def letter_counts(text: str) -> dict[str, int]:
    """Count of each letter A..Z (always 26 keys)."""
    c = Counter(letters_only(text))
    return {ch: c.get(ch, 0) for ch in ALPHABET}


def chi_squared(text: str) -> float:
    """Chi-squared statistic of `text` against English. Lower = more English-like.

    Returns +inf for text with no letters so it always ranks last.
    """
    counts = letter_counts(text)
    n = sum(counts.values())
    if n == 0:
        return math.inf
    return sum((counts[ch] - n * p) ** 2 / (n * p) for ch, p in ENGLISH_PROB.items())


def index_of_coincidence(text: str) -> float:
    """IoC = sum f_i (f_i - 1) / (N (N - 1)). Returns 0.0 for fewer than 2 letters."""
    counts = letter_counts(text)
    n = sum(counts.values())
    if n < 2:
        return 0.0
    return sum(f * (f - 1) for f in counts.values()) / (n * (n - 1))


def english_score(text: str) -> float:
    """Log-likelihood per letter under the English unigram model (higher is better)."""
    letters = letters_only(text)
    if not letters:
        return -math.inf
    return sum(math.log(ENGLISH_PROB[c]) for c in letters) / len(letters)


def friedman_estimate(text: str) -> float:
    """Friedman's estimate of a Vigenere key length from the ciphertext's IoC."""
    letters = letters_only(text)
    n = len(letters)
    ioc = index_of_coincidence(letters)
    denom = (n - 1) * ioc - n * RANDOM_IOC + ENGLISH_IOC
    if n < 2 or denom <= 0:
        return float("inf")
    return (ENGLISH_IOC - RANDOM_IOC) * n / denom
