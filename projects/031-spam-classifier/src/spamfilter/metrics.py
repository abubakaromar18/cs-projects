"""Binary classification metrics, with spam as the positive class.

Accuracy alone is misleading on imbalanced data: predicting "ham" for every
message of the UCI set scores ~87% accuracy while catching zero spam. So we
report precision (of what we flagged, how much was spam), recall (of all
spam, how much we caught) and their harmonic mean, F1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .dataset import Message


@dataclass
class Report:
    tp: int = 0   # spam flagged as spam
    fp: int = 0   # ham flagged as spam  (the costly mistake)
    tn: int = 0   # ham passed as ham
    fn: int = 0   # spam passed as ham

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.tn + self.fn

    @property
    def accuracy(self) -> float:
        return (self.tp + self.tn) / self.total if self.total else 0.0

    @property
    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 0.0

    @property
    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0

    def __add__(self, other: "Report") -> "Report":
        return Report(self.tp + other.tp, self.fp + other.fp,
                      self.tn + other.tn, self.fn + other.fn)

    def format(self) -> str:
        return (
            f"messages  : {self.total}\n"
            f"accuracy  : {self.accuracy:.3f}\n"
            f"precision : {self.precision:.3f}\n"
            f"recall    : {self.recall:.3f}\n"
            f"f1        : {self.f1:.3f}\n"
            f"\n               predicted\n"
            f"               ham    spam\n"
            f"actual ham  {self.tn:6d}  {self.fp:6d}\n"
            f"actual spam {self.fn:6d}  {self.tp:6d}"
        )


def evaluate(model, messages: Iterable[Message], threshold: float = 0.5) -> Report:
    r = Report()
    for m in messages:
        pred = model.predict(m.text, threshold=threshold)
        if m.label == "spam":
            if pred == "spam": r.tp += 1
            else: r.fn += 1
        else:
            if pred == "spam": r.fp += 1
            else: r.tn += 1
    return r
