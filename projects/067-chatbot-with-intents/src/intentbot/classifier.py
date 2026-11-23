"""Multinomial Naive Bayes, implemented from scratch.

For an utterance with feature counts f_1..f_n, Naive Bayes picks

    argmax_c  log P(c) + sum_i count(f_i) * log P(f_i | c)

assuming features are conditionally independent given the class. With
Laplace (add-alpha) smoothing,

    P(f | c) = (count(f, c) + alpha) / (total(c) + alpha * |V|)

Everything is kept in log space so long utterances don't underflow.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Iterable, Sequence

from .text import features as default_features

Featurizer = Callable[[str], list[str]]


class NaiveBayesClassifier:
    def __init__(self, alpha: float = 1.0, featurizer: Featurizer = default_features):
        if alpha <= 0:
            raise ValueError("alpha must be positive")
        self.alpha = alpha
        self.featurizer = featurizer
        self.class_docs: Counter[str] = Counter()
        self.feature_counts: dict[str, Counter[str]] = defaultdict(Counter)
        self.class_totals: Counter[str] = Counter()
        self.vocab: set[str] = set()

    # ---- training -------------------------------------------------------

    def fit(self, examples: Iterable[tuple[str, str]]) -> "NaiveBayesClassifier":
        """Train on (text, label) pairs. Can be called again to add data."""
        for text, label in examples:
            feats = self.featurizer(text)
            self.class_docs[label] += 1
            self.feature_counts[label].update(feats)
            self.class_totals[label] += len(feats)
            self.vocab.update(feats)
        return self

    @property
    def classes(self) -> list[str]:
        return sorted(self.class_docs)

    # ---- inference ------------------------------------------------------

    def log_scores(self, text: str) -> dict[str, float]:
        """Unnormalised log-posterior for every class."""
        if not self.class_docs:
            raise RuntimeError("classifier has not been trained")
        feats = Counter(self.featurizer(text))
        n_docs = sum(self.class_docs.values())
        v = len(self.vocab)
        scores: dict[str, float] = {}
        for c in self.class_docs:
            score = math.log(self.class_docs[c] / n_docs)
            denom = self.class_totals[c] + self.alpha * v
            counts = self.feature_counts[c]
            for f, k in feats.items():
                # Unknown features are skipped: they'd add the same
                # log(alpha/denom_c) to every class, but that differs by
                # class size and would just bias toward small classes.
                if f not in self.vocab:
                    continue
                score += k * math.log((counts[f] + self.alpha) / denom)
            scores[c] = score
        return scores

    def predict_proba(self, text: str) -> dict[str, float]:
        """Posterior probabilities via a numerically stable softmax."""
        scores = self.log_scores(text)
        top = max(scores.values())
        exps = {c: math.exp(s - top) for c, s in scores.items()}
        z = sum(exps.values())
        return {c: e / z for c, e in exps.items()}

    def predict(self, text: str) -> tuple[str, float]:
        """Best label and its probability."""
        probs = self.predict_proba(text)
        label = max(probs, key=probs.get)
        return label, probs[label]

    def known_fraction(self, text: str) -> float:
        """Share of the utterance's unigrams seen in training.

        Naive Bayes always produces *some* winner, even for gibberish.
        This lets the bot notice "I've never seen these words" and fall
        back instead of answering confidently.
        """
        feats = [f for f in self.featurizer(text) if "_" not in f]
        if not feats:
            return 0.0
        return sum(f in self.vocab for f in feats) / len(feats)

    # ---- persistence ----------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "alpha": self.alpha,
            "class_docs": dict(self.class_docs),
            "feature_counts": {c: dict(fc) for c, fc in self.feature_counts.items()},
            "class_totals": dict(self.class_totals),
        }

    @classmethod
    def from_dict(cls, data: dict, featurizer: Featurizer = default_features) -> "NaiveBayesClassifier":
        clf = cls(alpha=data["alpha"], featurizer=featurizer)
        clf.class_docs = Counter(data["class_docs"])
        clf.class_totals = Counter(data["class_totals"])
        for c, fc in data["feature_counts"].items():
            clf.feature_counts[c] = Counter(fc)
            clf.vocab.update(fc)
        return clf

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict()), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "NaiveBayesClassifier":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def cross_validate(
    examples: Sequence[tuple[str, str]], k: int = 5, alpha: float = 1.0
) -> float:
    """k-fold cross-validated accuracy.

    Folds are assigned round-robin within each label (stratified), so
    every fold sees every intent even with small datasets.
    """
    if k < 2:
        raise ValueError("k must be >= 2")
    by_label: dict[str, list[str]] = defaultdict(list)
    for text, label in examples:
        by_label[label].append(text)
    folds: list[list[tuple[str, str]]] = [[] for _ in range(k)]
    for label, texts in sorted(by_label.items()):
        for i, text in enumerate(texts):
            folds[i % k].append((text, label))

    correct = total = 0
    for i in range(k):
        train = [ex for j, fold in enumerate(folds) if j != i for ex in fold]
        test = folds[i]
        if not test or not train:
            continue
        clf = NaiveBayesClassifier(alpha=alpha).fit(train)
        for text, label in test:
            correct += clf.predict(text)[0] == label
            total += 1
    return correct / total if total else 0.0
