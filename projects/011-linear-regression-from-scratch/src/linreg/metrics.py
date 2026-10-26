"""Regression metrics implemented directly with NumPy.

All functions take 1-D arrays of true targets ``y`` and predictions ``y_hat``
of equal length.
"""

from __future__ import annotations

import numpy as np


def _check(y: np.ndarray, y_hat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y, dtype=float).ravel()
    y_hat = np.asarray(y_hat, dtype=float).ravel()
    if y.shape != y_hat.shape:
        raise ValueError(f"shape mismatch: {y.shape} vs {y_hat.shape}")
    if y.size == 0:
        raise ValueError("empty input")
    return y, y_hat


def mse(y, y_hat) -> float:
    """Mean squared error: (1/n) * sum((y - y_hat)^2)."""
    y, y_hat = _check(y, y_hat)
    return float(np.mean((y - y_hat) ** 2))


def rmse(y, y_hat) -> float:
    """Root mean squared error, in the same units as the target."""
    return float(np.sqrt(mse(y, y_hat)))


def mae(y, y_hat) -> float:
    """Mean absolute error: less sensitive to outliers than MSE."""
    y, y_hat = _check(y, y_hat)
    return float(np.mean(np.abs(y - y_hat)))


def r2_score(y, y_hat) -> float:
    """Coefficient of determination R^2 = 1 - SS_res / SS_tot.

    1.0 is a perfect fit, 0.0 means "no better than predicting the mean",
    and negative values are worse than the mean. If ``y`` is constant the
    score is 1.0 for a perfect prediction and 0.0 otherwise.
    """
    y, y_hat = _check(y, y_hat)
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    if ss_tot == 0.0:
        return 1.0 if ss_res == 0.0 else 0.0
    return 1.0 - ss_res / ss_tot
