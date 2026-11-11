"""Turn raw text into word frequencies and load them into a trie."""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, Iterator, TextIO

from .trie import Trie

# Letters, optionally joined by internal apostrophes or hyphens: don't, e-mail.
_WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*")


def tokenize(text: str) -> Iterator[str]:
    """Yield lower-cased words from ``text``; numbers and punctuation are dropped."""
    for m in _WORD.finditer(text):
        yield m.group(0).replace("’", "'").lower()


def count_words(lines: Iterable[str], min_length: int = 1) -> Counter[str]:
    counts: Counter[str] = Counter()
    for line in lines:
        counts.update(w for w in tokenize(line) if len(w) >= min_length)
    return counts


def train(source: TextIO | Iterable[str], trie: Trie | None = None, min_length: int = 1) -> Trie:
    """Count words in ``source`` (a file or iterable of lines) and insert them."""
    trie = trie if trie is not None else Trie()
    for word, n in count_words(source, min_length).items():
        trie.insert(word, n)
    return trie
