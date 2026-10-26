"""Matplotlib visualisations of the model and of gradient descent itself.

Every function returns the Figure and, if ``path`` is given, saves a PNG.
The non-interactive Agg backend is selected so plots work on headless
machines and in CI.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .model import LinearRegression  # noqa: E402


def _save(fig, path: str | Path | None):
    if path is not None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=110, bbox_inches="tight")
    return fig


def plot_fit(model: LinearRegression, X, y, path=None, title="Linear fit",
             xlabel="x", ylabel="y"):
    """Scatter the data and draw the fitted line (single-feature only)."""
    X = np.asarray(X, dtype=float).reshape(len(y), -1)
    if X.shape[1] != 1:
        raise ValueError("plot_fit needs exactly one feature; use plot_predictions instead")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(X[:, 0], y, s=14, alpha=0.6, label="data")
    xs = np.linspace(X[:, 0].min(), X[:, 0].max(), 200).reshape(-1, 1)
    w, b = float(model.weights_[0]), model.bias_
    ax.plot(xs[:, 0], model.predict(xs), color="C3", lw=2,
            label=f"y = {w:.3f}·x + {b:.3f}")
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    ax.legend()
    ax.grid(alpha=0.3)
    return _save(fig, path)


def plot_predictions(model: LinearRegression, X, y, path=None, title="Predicted vs actual"):
    """Predicted-vs-actual scatter; points on the diagonal are perfect."""
    y_hat = model.predict(X)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(y, y_hat, s=14, alpha=0.6)
    lo, hi = float(min(y.min(), y_hat.min())), float(max(y.max(), y_hat.max()))
    ax.plot([lo, hi], [lo, hi], "k--", lw=1, label="perfect")
    ax.set(title=title, xlabel="actual", ylabel="predicted")
    ax.legend()
    ax.grid(alpha=0.3)
    return _save(fig, path)


def plot_loss_curve(histories: dict[str, list[float]], path=None, log_scale=True,
                    title="Training loss"):
    """Loss per epoch for one or more solvers, e.g. {"batch": [...], "sgd": [...]}."""
    fig, ax = plt.subplots(figsize=(6, 4))
    for label, loss in histories.items():
        ax.plot(range(len(loss)), loss, label=label, lw=1.6)
    if log_scale:
        ax.set_yscale("log")
    ax.set(title=title, xlabel="epoch", ylabel="MSE loss")
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    return _save(fig, path)


def plot_loss_surface(model: LinearRegression, X, y, path=None, padding=1.5, resolution=120,
                      title="Loss surface and gradient-descent path"):
    """Contour plot of J(w, b) with the path gradient descent took across it.

    Only defined for a single feature, since the surface has to be 2-D
    (one axis for w, one for b).
    """
    X = np.asarray(X, dtype=float).reshape(len(y), -1)
    if X.shape[1] != 1:
        raise ValueError("plot_loss_surface needs exactly one feature")
    ws = np.array([w[0] for w in model.history_.weights])
    bs = np.array(model.history_.bias)

    w_lo, w_hi = min(ws.min(), model.weights_[0]), max(ws.max(), model.weights_[0])
    b_lo, b_hi = min(bs.min(), model.bias_), max(bs.max(), model.bias_)
    w_pad = max(w_hi - w_lo, 1.0) * (padding - 1) + 0.5
    b_pad = max(b_hi - b_lo, 1.0) * (padding - 1) + 0.5
    W, B = np.meshgrid(
        np.linspace(w_lo - w_pad, w_hi + w_pad, resolution),
        np.linspace(b_lo - b_pad, b_hi + b_pad, resolution),
    )
    # Vectorised loss over the whole grid: residual[i, j, k] for sample k.
    x = X[:, 0]
    resid = W[..., None] * x + B[..., None] - y
    J = np.mean(resid**2, axis=-1) + model.alpha * W**2

    fig, ax = plt.subplots(figsize=(6, 5))
    levels = np.logspace(np.log10(J.min() + 1e-12), np.log10(J.max()), 25)
    cs = ax.contour(W, B, J, levels=levels, cmap="viridis", linewidths=0.8)
    fig.colorbar(cs, ax=ax, label="loss")
    ax.plot(ws, bs, "o-", color="C3", ms=2.5, lw=1, label="GD path")
    ax.plot(ws[0], bs[0], "s", color="k", label="start")
    ax.plot(model.weights_[0], model.bias_, "*", color="gold", ms=14,
            markeredgecolor="k", label="final")
    ax.set(title=title, xlabel="weight w", ylabel="bias b")
    ax.legend(loc="best")
    return _save(fig, path)


def close_all() -> None:
    plt.close("all")
