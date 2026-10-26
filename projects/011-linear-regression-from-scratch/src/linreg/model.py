"""Linear regression trained with gradient descent, written from scratch.

Model:      y_hat = X @ w + b
Loss (MSE): J(w, b) = (1/n) * ||X @ w + b - y||^2  +  alpha * ||w||^2
Gradients:  dJ/dw = (2/n) * X^T (y_hat - y) + 2 * alpha * w
            dJ/db = (2/n) * sum(y_hat - y)

The bias is never regularised (penalising it would pull predictions toward
zero rather than toward a simpler slope).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .metrics import r2_score

SOLVERS = ("batch", "sgd", "minibatch", "normal")


@dataclass
class TrainingHistory:
    """Per-epoch record of the training loss and parameters."""

    loss: list[float] = field(default_factory=list)
    weights: list[np.ndarray] = field(default_factory=list)
    bias: list[float] = field(default_factory=list)

    def record(self, loss: float, w: np.ndarray, b: float) -> None:
        self.loss.append(loss)
        self.weights.append(w.copy())
        self.bias.append(b)


class LinearRegression:
    """Ordinary least squares / ridge regression.

    Parameters
    ----------
    learning_rate:
        Step size for gradient descent. Too large diverges, too small crawls.
    epochs:
        Maximum number of passes over the training data.
    solver:
        ``"batch"`` (full-batch GD), ``"sgd"`` (one sample per step),
        ``"minibatch"`` (``batch_size`` samples per step) or ``"normal"``
        (closed-form normal equation, used as a ground-truth reference).
    batch_size:
        Mini-batch size for the ``"minibatch"`` solver.
    alpha:
        L2 (ridge) regularisation strength; 0 means plain least squares.
    tol:
        Stop early when the epoch loss improves by less than ``tol``.
    seed:
        RNG seed for shuffling in the stochastic solvers.
    """

    def __init__(
        self,
        learning_rate: float = 0.01,
        epochs: int = 1000,
        solver: str = "batch",
        batch_size: int = 16,
        alpha: float = 0.0,
        tol: float = 1e-10,
        seed: int | None = 0,
    ) -> None:
        if solver not in SOLVERS:
            raise ValueError(f"solver must be one of {SOLVERS}, got {solver!r}")
        if learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if epochs < 1:
            raise ValueError("epochs must be >= 1")
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        if alpha < 0:
            raise ValueError("alpha must be non-negative")
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.solver = solver
        self.batch_size = batch_size
        self.alpha = alpha
        self.tol = tol
        self.seed = seed

        self.weights_: np.ndarray | None = None
        self.bias_: float = 0.0
        self.history_ = TrainingHistory()
        self.n_iter_: int = 0
        self.converged_: bool = False

    # ------------------------------------------------------------------ core

    @staticmethod
    def _as_2d(X) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if X.ndim != 2:
            raise ValueError("X must be 1-D or 2-D")
        return X

    def loss(self, X, y, w: np.ndarray | None = None, b: float | None = None) -> float:
        """Regularised MSE for the given (or fitted) parameters."""
        X = self._as_2d(X)
        y = np.asarray(y, dtype=float).ravel()
        w = self.weights_ if w is None else w
        b = self.bias_ if b is None else b
        if w is None:
            raise RuntimeError("model is not fitted")
        # A diverging run overflows to inf; fit() detects that and raises a
        # helpful error, so silence NumPy's own overflow warnings here.
        with np.errstate(over="ignore", invalid="ignore"):
            residual = X @ w + b - y
            return float(np.mean(residual**2) + self.alpha * np.dot(w, w))

    def gradients(self, X: np.ndarray, y: np.ndarray, w: np.ndarray, b: float):
        """Return (dJ/dw, dJ/db) for a batch."""
        n = X.shape[0]
        error = X @ w + b - y
        grad_w = (2.0 / n) * (X.T @ error) + 2.0 * self.alpha * w
        grad_b = (2.0 / n) * float(np.sum(error))
        return grad_w, grad_b

    def fit(self, X, y) -> "LinearRegression":
        X = self._as_2d(X)
        y = np.asarray(y, dtype=float).ravel()
        if X.shape[0] != y.shape[0]:
            raise ValueError(f"X has {X.shape[0]} rows but y has {y.shape[0]}")
        if X.shape[0] == 0:
            raise ValueError("cannot fit on an empty dataset")

        self.history_ = TrainingHistory()
        self.converged_ = False

        if self.solver == "normal":
            self._fit_normal(X, y)
            return self

        n, d = X.shape
        w = np.zeros(d)
        b = 0.0
        rng = np.random.default_rng(self.seed)
        batch = {"batch": n, "sgd": 1, "minibatch": min(self.batch_size, n)}[self.solver]

        prev = self.loss(X, y, w, b)
        self.history_.record(prev, w, b)
        for epoch in range(1, self.epochs + 1):
            # Stochastic solvers visit samples in a fresh random order each epoch.
            order = rng.permutation(n) if batch < n else np.arange(n)
            for start in range(0, n, batch):
                idx = order[start : start + batch]
                with np.errstate(over="ignore", invalid="ignore"):
                    gw, gb = self.gradients(X[idx], y[idx], w, b)
                    w -= self.learning_rate * gw
                    b -= self.learning_rate * gb

            current = self.loss(X, y, w, b)
            self.history_.record(current, w, b)
            self.n_iter_ = epoch
            if not np.isfinite(current):
                raise FloatingPointError(
                    f"loss diverged at epoch {epoch}; try a smaller learning_rate "
                    "or standardise the features"
                )
            if abs(prev - current) < self.tol:
                self.converged_ = True
                break
            prev = current

        self.weights_, self.bias_ = w, b
        return self

    def _fit_normal(self, X: np.ndarray, y: np.ndarray) -> None:
        """Closed form: theta = (A^T A + alpha*n*I')^-1 A^T y, with A = [1 | X].

        The ``n`` factor matches the gradient-descent loss, which averages the
        squared error. I' is the identity with a 0 for the bias term so the
        intercept is not penalised. ``lstsq`` is used when alpha is 0 because it
        stays stable even for rank-deficient X.
        """
        n, d = X.shape
        A = np.hstack([np.ones((n, 1)), X])
        if self.alpha == 0:
            theta, *_ = np.linalg.lstsq(A, y, rcond=None)
        else:
            reg = self.alpha * n * np.eye(d + 1)
            reg[0, 0] = 0.0
            theta = np.linalg.solve(A.T @ A + reg, A.T @ y)
        self.bias_ = float(theta[0])
        self.weights_ = theta[1:]
        self.n_iter_ = 1
        self.converged_ = True
        self.history_.record(self.loss(X, y), self.weights_, self.bias_)

    # --------------------------------------------------------------- predict

    def predict(self, X) -> np.ndarray:
        if self.weights_ is None:
            raise RuntimeError("model is not fitted")
        X = self._as_2d(X)
        if X.shape[1] != self.weights_.size:
            raise ValueError(f"expected {self.weights_.size} features, got {X.shape[1]}")
        return X @ self.weights_ + self.bias_

    def score(self, X, y) -> float:
        """R^2 on the given data."""
        return r2_score(y, self.predict(X))

    def __repr__(self) -> str:
        return (
            f"LinearRegression(solver={self.solver!r}, learning_rate={self.learning_rate}, "
            f"epochs={self.epochs}, alpha={self.alpha})"
        )


def unscale_parameters(
    weights: np.ndarray, bias: float, mean: np.ndarray, std: np.ndarray
) -> tuple[np.ndarray, float]:
    """Convert parameters learned on standardised X back to original units.

    If x' = (x - mean) / std and y = w'·x' + b', then
    y = (w'/std)·x + (b' - sum(w' * mean / std)).
    """
    w = weights / std
    b = bias - float(np.sum(weights * mean / std))
    return w, b
