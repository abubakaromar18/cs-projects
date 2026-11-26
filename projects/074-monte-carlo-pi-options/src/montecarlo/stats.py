"""Statistics shared by every estimator.

A Monte Carlo estimate is the sample mean of i.i.d. draws X_1..X_n. By the
Central Limit Theorem the mean is approximately Normal with standard error
sigma / sqrt(n), so a 95% confidence interval is mean +/- 1.96 * SE. The
1/sqrt(n) rate is the defining (and limiting) property of Monte Carlo:
to gain one more decimal digit you need 100x more samples.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np

# Two-sided z-scores for common confidence levels (avoids a SciPy dependency).
_Z_SCORES = {0.90: 1.6448536269514722, 0.95: 1.959963984540054, 0.99: 2.5758293035489004}


def z_score(confidence: float) -> float:
    """Return the two-sided Normal critical value for ``confidence``."""
    try:
        return _Z_SCORES[round(confidence, 2)]
    except KeyError as exc:
        raise ValueError(f"unsupported confidence level {confidence}; use 0.90, 0.95 or 0.99") from exc


@dataclass(frozen=True)
class Estimate:
    """A point estimate with its sampling uncertainty."""

    value: float
    std_error: float
    samples: int
    confidence: float = 0.95

    @property
    def half_width(self) -> float:
        return z_score(self.confidence) * self.std_error

    @property
    def ci(self) -> tuple[float, float]:
        """Confidence interval (low, high)."""
        return (self.value - self.half_width, self.value + self.half_width)

    def contains(self, x: float) -> bool:
        low, high = self.ci
        return low <= x <= high

    def __str__(self) -> str:
        low, high = self.ci
        pct = int(round(self.confidence * 100))
        return (f"{self.value:.6f} ± {self.half_width:.6f} "
                f"({pct}% CI [{low:.6f}, {high:.6f}], n={self.samples:,})")


def estimate_from_samples(samples: np.ndarray, confidence: float = 0.95) -> Estimate:
    """Build an :class:`Estimate` from i.i.d. draws using the sample mean and std."""
    samples = np.asarray(samples, dtype=float)
    n = samples.size
    if n < 2:
        raise ValueError("need at least two samples to estimate a standard error")
    mean = float(samples.mean())
    std = float(samples.std(ddof=1))  # unbiased sample standard deviation
    return Estimate(mean, std / sqrt(n), n, confidence)
