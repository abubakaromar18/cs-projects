"""Loading the SMS Spam Collection format and splitting it for evaluation.

The UCI SMS Spam Collection is a tab-separated file with one message per
line: ``<label>\\t<text>`` where label is ``ham`` or ``spam``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

LABELS = ("ham", "spam")


@dataclass(frozen=True)
class Message:
    label: str
    text: str


def parse_lines(lines: Iterable[str]) -> list[Message]:
    """Parse ``label<TAB>text`` lines, skipping blanks; raise on bad labels."""
    out: list[Message] = []
    for lineno, raw in enumerate(lines, 1):
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue
        label, sep, text = line.partition("\t")
        label = label.strip().lower()
        if not sep or label not in LABELS:
            raise ValueError(f"line {lineno}: expected 'ham|spam<TAB>text', got {line[:40]!r}")
        out.append(Message(label, text))
    return out


def load_tsv(path: str | Path) -> list[Message]:
    # The original UCI file contains a few non-UTF-8 bytes; be lenient.
    with open(path, encoding="utf-8", errors="replace") as fh:
        return parse_lines(fh)


def stratified_split(data: list[Message], test_ratio: float = 0.25,
                     seed: int = 0) -> tuple[list[Message], list[Message]]:
    """Split so that train and test keep the same ham/spam proportion.

    Spam is the minority class (~13% in the UCI set). A plain random split
    can leave the test set with very few spam messages, making recall noisy.
    """
    if not 0 < test_ratio < 1:
        raise ValueError("test_ratio must be between 0 and 1")
    rng = random.Random(seed)
    train: list[Message] = []
    test: list[Message] = []
    for label in LABELS:
        group = [m for m in data if m.label == label]
        rng.shuffle(group)
        n_test = round(len(group) * test_ratio)
        test.extend(group[:n_test])
        train.extend(group[n_test:])
    rng.shuffle(train)
    rng.shuffle(test)
    return train, test


def k_fold(data: list[Message], k: int = 5,
           seed: int = 0) -> Iterator[tuple[list[Message], list[Message]]]:
    """Yield ``k`` stratified (train, test) folds covering every message once."""
    if k < 2:
        raise ValueError("k must be >= 2")
    rng = random.Random(seed)
    folds: list[list[Message]] = [[] for _ in range(k)]
    for label in LABELS:
        group = [m for m in data if m.label == label]
        rng.shuffle(group)
        for i, m in enumerate(group):
            folds[i % k].append(m)
    for i in range(k):
        train = [m for j, f in enumerate(folds) if j != i for m in f]
        yield train, folds[i]
