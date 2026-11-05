"""Multinomial Naive Bayes, implemented from scratch.

Bayes' rule gives, for a message with tokens w1..wn:

    P(spam | w) ∝ P(spam) · Π P(wi | spam)

The "naive" assumption is that tokens are conditionally independent given
the class. It is false for language, yet the resulting *ranking* of classes
is usually right, which is all a classifier needs.

Two practical details:

* **Laplace (additive) smoothing.** A word never seen in spam would give
  P(w|spam) = 0 and zero out the whole product. We add ``alpha`` to every
  count: P(w|c) = (count(w,c) + α) / (total(c) + α·|V|).
* **Log space.** Multiplying hundreds of small probabilities underflows a
  float. We sum log-probabilities instead and use log-sum-exp to recover a
  normalised posterior.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Callable, Iterable

from .dataset import Message
from .text import tokenize

Tokenizer = Callable[[str], list[str]]


class NaiveBayes:
    def __init__(self, alpha: float = 1.0, tokenizer: Tokenizer = tokenize):
        if alpha <= 0:
            raise ValueError("alpha must be > 0")
        self.alpha = alpha
        self.tokenizer = tokenizer
        self.class_docs: Counter[str] = Counter()          # documents per class
        self.word_counts: dict[str, Counter[str]] = {}     # class -> token -> count
        self.total_words: Counter[str] = Counter()         # class -> token total
        self.vocab: set[str] = set()

    # ------------------------------------------------------------ training
    def fit(self, messages: Iterable[Message]) -> "NaiveBayes":
        self.class_docs.clear(); self.word_counts.clear()
        self.total_words.clear(); self.vocab.clear()
        return self.partial_fit(messages)

    def partial_fit(self, messages: Iterable[Message]) -> "NaiveBayes":
        """Add more training data. NB training is just counting, so it is
        naturally incremental - useful for 'mark as spam' feedback loops."""
        for m in messages:
            tokens = self.tokenizer(m.text)
            self.class_docs[m.label] += 1
            self.word_counts.setdefault(m.label, Counter()).update(tokens)
            self.total_words[m.label] += len(tokens)
            self.vocab.update(tokens)
        return self

    @property
    def classes(self) -> list[str]:
        return sorted(self.class_docs)

    def _check_fitted(self) -> None:
        if len(self.class_docs) < 2:
            raise RuntimeError("model needs training examples from at least two classes")

    # ----------------------------------------------------------- inference
    def log_prior(self, c: str) -> float:
        return math.log(self.class_docs[c] / sum(self.class_docs.values()))

    def log_likelihood(self, token: str, c: str) -> float:
        num = self.word_counts[c][token] + self.alpha
        den = self.total_words[c] + self.alpha * len(self.vocab)
        return math.log(num / den)

    def joint_log_scores(self, text: str) -> dict[str, float]:
        """Unnormalised log P(c) + Σ log P(w|c) for each class.

        Tokens never seen in training are skipped: they carry no information
        and would only add the same smoothing constant to every class.
        """
        self._check_fitted()
        tokens = [t for t in self.tokenizer(text) if t in self.vocab]
        return {
            c: self.log_prior(c) + sum(self.log_likelihood(t, c) for t in tokens)
            for c in self.classes
        }

    def predict_proba(self, text: str) -> dict[str, float]:
        scores = self.joint_log_scores(text)
        m = max(scores.values())                      # log-sum-exp trick
        z = m + math.log(sum(math.exp(s - m) for s in scores.values()))
        return {c: math.exp(s - z) for c, s in scores.items()}

    def predict(self, text: str, threshold: float = 0.5) -> str:
        """Return the predicted label. With ham/spam, ``threshold`` is the spam
        probability required to say spam - raise it to avoid false positives
        (losing a real message is usually worse than seeing one more ad)."""
        proba = self.predict_proba(text)
        if set(proba) == {"ham", "spam"}:
            return "spam" if proba["spam"] >= threshold else "ham"
        return max(proba, key=proba.__getitem__)

    def explain(self, text: str, positive: str = "spam",
                negative: str = "ham") -> list[tuple[str, float]]:
        """Per-token log-likelihood ratios log P(t|pos) - log P(t|neg),
        sorted by influence. Positive values push towards ``positive``."""
        self._check_fitted()
        seen = dict.fromkeys(t for t in self.tokenizer(text) if t in self.vocab)
        contrib = [(t, self.log_likelihood(t, positive) - self.log_likelihood(t, negative))
                   for t in seen]
        return sorted(contrib, key=lambda p: -abs(p[1]))

    def top_tokens(self, c: str, other: str, n: int = 10,
                   min_count: int = 2) -> list[tuple[str, float]]:
        """The tokens most indicative of class ``c`` versus ``other``."""
        self._check_fitted()
        cand = [t for t in self.vocab
                if self.word_counts[c][t] + self.word_counts[other][t] >= min_count]
        ranked = sorted(cand, key=lambda t: self.log_likelihood(t, c) - self.log_likelihood(t, other),
                        reverse=True)
        return [(t, self.log_likelihood(t, c) - self.log_likelihood(t, other)) for t in ranked[:n]]

    # --------------------------------------------------------- persistence
    def to_dict(self) -> dict:
        return {
            "format": "spamfilter-nb/1",
            "alpha": self.alpha,
            "class_docs": dict(self.class_docs),
            "word_counts": {c: dict(wc) for c, wc in self.word_counts.items()},
        }

    @classmethod
    def from_dict(cls, d: dict, tokenizer: Tokenizer = tokenize) -> "NaiveBayes":
        if d.get("format") != "spamfilter-nb/1":
            raise ValueError("not a spamfilter model file")
        nb = cls(alpha=d["alpha"], tokenizer=tokenizer)
        nb.class_docs = Counter(d["class_docs"])
        for c, wc in d["word_counts"].items():
            nb.word_counts[c] = Counter(wc)
            nb.total_words[c] = sum(wc.values())
            nb.vocab.update(wc)
        return nb

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "NaiveBayes":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
