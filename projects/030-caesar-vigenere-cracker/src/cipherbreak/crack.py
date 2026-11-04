"""Ciphertext-only attacks on Caesar and Vigenere.

Caesar: only 26 keys, so try them all and rank by chi-squared against English.

Vigenere (key of unknown length L), in three steps:
  1. Estimate L. Two independent signals are combined:
     - Kasiski examination: repeated n-grams in the ciphertext are usually the
       same plaintext encrypted under the same key offset, so the distances
       between repeats tend to be multiples of L.
     - Index of coincidence: split the letters into L columns (every L-th
       letter). If L is right, each column is a plain Caesar cipher and its IoC
       looks like English (~0.066); otherwise it looks random (~0.038).
  2. Each column is then a Caesar cipher: crack it with chi-squared.
  3. Collapse a key that is a repetition of a shorter key (e.g. "KEYKEY").
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .ciphers import caesar_decrypt, shifts_to_key, vigenere_decrypt
from .stats import ENGLISH_IOC, RANDOM_IOC, chi_squared, index_of_coincidence, letters_only


@dataclass(frozen=True)
class CaesarCandidate:
    shift: int
    plaintext: str
    chi2: float


def crack_caesar(ciphertext: str) -> list[CaesarCandidate]:
    """All 26 decryptions, best (lowest chi-squared) first."""
    cands = []
    for shift in range(26):
        pt = caesar_decrypt(ciphertext, shift)
        cands.append(CaesarCandidate(shift, pt, chi_squared(pt)))
    return sorted(cands, key=lambda c: (c.chi2, c.shift))


def best_shift(column: str) -> int:
    """The Caesar shift that makes `column` (letters only) look most like English."""
    return min(range(26), key=lambda s: (chi_squared(caesar_decrypt(column, s)), s))


# ---------------------------------------------------------------- key length

def kasiski_distances(letters: str, min_len: int = 3, max_len: int = 5) -> list[int]:
    """Distances between consecutive occurrences of every repeated n-gram."""
    distances: list[int] = []
    for n in range(min_len, max_len + 1):
        positions: dict[str, list[int]] = defaultdict(list)
        for i in range(len(letters) - n + 1):
            positions[letters[i:i + n]].append(i)
        for pos in positions.values():
            distances.extend(b - a for a, b in zip(pos, pos[1:]))
    return distances


def kasiski_factor_counts(letters: str, max_key_len: int = 20) -> dict[int, int]:
    """How many repeat-distances each candidate key length (2..max) divides."""
    counts: Counter[int] = Counter()
    for d in kasiski_distances(letters):
        for k in range(2, max_key_len + 1):
            if d % k == 0:
                counts[k] += 1
    return dict(counts)


def columns(letters: str, key_len: int) -> list[str]:
    """Split letters into key_len interleaved columns: column j = letters[j::key_len]."""
    return [letters[j::key_len] for j in range(key_len)]


def mean_column_ioc(letters: str, key_len: int) -> float:
    cols = columns(letters, key_len)
    return sum(index_of_coincidence(c) for c in cols) / len(cols)


def rank_key_lengths(letters: str, max_key_len: int = 20) -> list[tuple[int, float]]:
    """(key_len, mean column IoC) for every feasible length, best first.

    A length is feasible if each column still has at least 2 letters.
    """
    max_key_len = max(1, min(max_key_len, len(letters) // 2))
    scored = [(k, mean_column_ioc(letters, k)) for k in range(1, max_key_len + 1)]
    return sorted(scored, key=lambda t: (-t[1], t[0]))


def guess_key_length(letters: str, max_key_len: int = 20) -> int:
    """Pick the most plausible key length.

    Multiples of the true length score as well as the true length (their
    columns are also single Caesar ciphers), so instead of the arg-max we take
    the *smallest* length whose column IoC is close to the best one. Kasiski
    factor counts break ties between close candidates.
    """
    ranked = rank_key_lengths(letters, max_key_len)
    best_ioc = ranked[0][1]
    # "close" = within 15% of the gap between random text and the best score
    threshold = best_ioc - 0.15 * (best_ioc - RANDOM_IOC)
    good = sorted(k for k, ioc in ranked if ioc >= threshold)
    if len(good) > 1:
        kas = kasiski_factor_counts(letters, max_key_len)
        smallest = good[0]
        # Prefer the smallest length unless Kasiski strongly favours another
        # candidate that is not merely a multiple of it.
        for k in good[1:]:
            if k % smallest and kas.get(k, 0) > 2 * kas.get(smallest, 0):
                return k
        return smallest
    return good[0]


def minimal_period(key: str) -> str:
    """Shortest string whose repetition gives `key` ("ABCABC" -> "ABC")."""
    n = len(key)
    for p in range(1, n + 1):
        if n % p == 0 and key[:p] * (n // p) == key:
            return key[:p]
    return key


# ---------------------------------------------------------------- full attack

@dataclass
class VigenereResult:
    key: str
    plaintext: str
    key_length_ranking: list[tuple[int, float]] = field(default_factory=list)
    kasiski: dict[int, int] = field(default_factory=dict)

    @property
    def looks_english(self) -> bool:
        """Rough sanity check: plaintext IoC nearer English than random."""
        ioc = index_of_coincidence(self.plaintext)
        return ioc > (ENGLISH_IOC + RANDOM_IOC) / 2


def crack_vigenere(ciphertext: str, max_key_len: int = 20, key_len: int | None = None) -> VigenereResult:
    """Recover a Vigenere key and plaintext from ciphertext alone.

    Pass `key_len` to skip estimation when the length is already known.
    Needs a reasonable amount of text: roughly 20+ letters per key character.
    """
    letters = letters_only(ciphertext)
    if not letters:
        raise ValueError("ciphertext contains no letters")
    ranking = rank_key_lengths(letters, max_key_len)
    length = key_len if key_len else guess_key_length(letters, max_key_len)
    key = minimal_period(shifts_to_key(best_shift(col) for col in columns(letters, length)))
    return VigenereResult(
        key=key,
        plaintext=vigenere_decrypt(ciphertext, key),
        key_length_ranking=ranking,
        kasiski=kasiski_factor_counts(letters, max_key_len),
    )
