"""Estimating pi by throwing random darts at the unit square.

A point (x, y) drawn uniformly from [0, 1)^2 lands inside the quarter circle
x^2 + y^2 <= 1 with probability pi/4. The indicator of "inside" is a
Bernoulli(pi/4) variable, so 4 * (fraction inside) is an unbiased estimator
of pi with variance 4^2 * p(1-p) / n.
"""

from __future__ import annotations

from math import sqrt

import numpy as np

from .stats import Estimate

_DEFAULT_BATCH = 1_000_000


def _rng(seed: int | np.random.Generator | None) -> np.random.Generator:
    return seed if isinstance(seed, np.random.Generator) else np.random.default_rng(seed)


def estimate_pi(samples: int, seed: int | np.random.Generator | None = None,
                confidence: float = 0.95, batch_size: int = _DEFAULT_BATCH) -> Estimate:
    """Plain (crude) Monte Carlo estimate of pi.

    Points are generated in batches so memory stays bounded even for
    hundreds of millions of samples; only the running hit count is kept.
    """
    if samples < 2:
        raise ValueError("samples must be >= 2")
    rng = _rng(seed)
    hits = 0
    remaining = samples
    while remaining > 0:
        n = min(batch_size, remaining)
        xy = rng.random((n, 2))
        hits += int(np.count_nonzero(np.einsum("ij,ij->i", xy, xy) <= 1.0))
        remaining -= n
    p = hits / samples
    # Bernoulli variance with Bessel's correction, scaled by 4.
    var = p * (1 - p) * samples / (samples - 1)
    return Estimate(4 * p, 4 * sqrt(var / samples), samples, confidence)


def estimate_pi_stratified(samples: int, seed: int | np.random.Generator | None = None,
                           confidence: float = 0.95) -> Estimate:
    """Stratified-sampling estimate of pi (a variance-reduction technique).

    The unit square is cut into a k x k grid and one point is drawn inside each
    cell. Every region of the square is then guaranteed to be sampled, which
    removes the between-strata part of the variance. The standard error is
    estimated from the per-cell indicators treated within strata.
    """
    k = int(sqrt(samples))
    if k < 2:
        raise ValueError("samples must be >= 4 for stratification")
    rng = _rng(seed)
    n = k * k
    ii, jj = np.meshgrid(np.arange(k), np.arange(k), indexing="ij")
    x = (ii.ravel() + rng.random(n)) / k
    y = (jj.ravel() + rng.random(n)) / k
    inside = (x * x + y * y <= 1.0).astype(float)
    estimate = float(inside.mean()) * 4
    # Within-stratum variance: only boundary cells contribute. We approximate
    # it by pairing neighbouring strata (a standard trick when each stratum
    # holds a single sample) - the paired differences have the right scale.
    paired = inside[: n - n % 2].reshape(-1, 2)
    within_var = float(np.mean((paired[:, 0] - paired[:, 1]) ** 2) / 2)
    std_error = 4 * sqrt(within_var / n)
    return Estimate(estimate, std_error, n, confidence)


def crude_samples_for_pi(samples: int, seed: int | None = None) -> np.ndarray:
    """Return the raw 4*indicator draws (handy for plotting / teaching)."""
    xy = _rng(seed).random((samples, 2))
    return 4.0 * ((xy ** 2).sum(axis=1) <= 1.0)


__all__ = ["estimate_pi", "estimate_pi_stratified", "crude_samples_for_pi"]
