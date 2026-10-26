"""Dataset helpers: synthetic generation, CSV loading, splitting and scaling."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Dataset:
    """Feature matrix ``X`` (n_samples, n_features) and target vector ``y``."""

    X: np.ndarray
    y: np.ndarray
    feature_names: list[str]
    target_name: str = "y"

    def __len__(self) -> int:
        return self.X.shape[0]


def make_regression(
    n_samples: int = 100,
    weights: list[float] | np.ndarray = (3.0,),
    bias: float = 4.0,
    noise: float = 1.0,
    x_range: tuple[float, float] = (0.0, 10.0),
    seed: int | None = 0,
) -> Dataset:
    """Generate ``y = X @ weights + bias + N(0, noise^2)`` with uniform ``X``.

    Knowing the true parameters lets us check that gradient descent recovers
    them, which is exactly what the tests do.
    """
    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")
    if noise < 0:
        raise ValueError("noise must be non-negative")
    rng = np.random.default_rng(seed)
    w = np.asarray(weights, dtype=float).ravel()
    X = rng.uniform(x_range[0], x_range[1], size=(n_samples, w.size))
    y = X @ w + bias + rng.normal(0.0, noise, size=n_samples)
    names = [f"x{i + 1}" for i in range(w.size)]
    return Dataset(X=X, y=y, feature_names=names)


def load_csv(path: str | Path, target: str | None = None) -> Dataset:
    """Load a numeric CSV with a header row.

    ``target`` names the column to predict; by default it is the last column.
    Every other column becomes a feature.
    """
    path = Path(path)
    with path.open(newline="") as fh:
        reader = csv.reader(fh)
        try:
            header = [h.strip() for h in next(reader)]
        except StopIteration:
            raise ValueError(f"{path}: file is empty") from None
        rows = [row for row in reader if row and any(c.strip() for c in row)]

    if len(header) < 2:
        raise ValueError(f"{path}: need at least one feature column and one target column")
    if not rows:
        raise ValueError(f"{path}: no data rows")

    target = target or header[-1]
    if target not in header:
        raise ValueError(f"{path}: target column {target!r} not in header {header}")
    t_idx = header.index(target)

    try:
        data = np.array([[float(c) for c in row] for row in rows], dtype=float)
    except ValueError as exc:
        raise ValueError(f"{path}: non-numeric value ({exc})") from None
    if data.shape[1] != len(header):
        raise ValueError(f"{path}: rows do not match header width")

    feat_idx = [i for i in range(len(header)) if i != t_idx]
    return Dataset(
        X=data[:, feat_idx],
        y=data[:, t_idx],
        feature_names=[header[i] for i in feat_idx],
        target_name=target,
    )


def train_test_split(
    X: np.ndarray, y: np.ndarray, test_size: float = 0.2, seed: int | None = 0
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Shuffle and split into ``X_train, X_test, y_train, y_test``."""
    if not 0.0 < test_size < 1.0:
        raise ValueError("test_size must be in (0, 1)")
    n = X.shape[0]
    n_test = max(1, int(round(n * test_size)))
    if n_test >= n:
        raise ValueError("not enough samples to split")
    idx = np.random.default_rng(seed).permutation(n)
    test, train = idx[:n_test], idx[n_test:]
    return X[train], X[test], y[train], y[test]


class StandardScaler:
    """Rescale each feature to zero mean and unit variance.

    Gradient descent converges far faster when features share a scale,
    because the loss surface becomes rounder instead of a long thin valley.
    Constant features get a std of 1 so we never divide by zero.
    """

    def __init__(self) -> None:
        self.mean_: np.ndarray | None = None
        self.std_: np.ndarray | None = None

    def fit(self, X: np.ndarray) -> "StandardScaler":
        X = np.asarray(X, dtype=float)
        self.mean_ = X.mean(axis=0)
        std = X.std(axis=0)
        self.std_ = np.where(std == 0, 1.0, std)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.std_ is None:
            raise RuntimeError("StandardScaler is not fitted")
        return (np.asarray(X, dtype=float) - self.mean_) / self.std_

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.std_ is None:
            raise RuntimeError("StandardScaler is not fitted")
        return np.asarray(X, dtype=float) * self.std_ + self.mean_
