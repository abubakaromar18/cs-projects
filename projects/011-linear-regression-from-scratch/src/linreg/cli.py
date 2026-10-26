"""Command-line interface: fit a model, print metrics, and save plots.

Examples::

    linreg                                   # synthetic y = 3x + 4 + noise
    linreg --data examples/house_prices.csv --target price --scale
    linreg --compare --plots plots/          # batch vs SGD vs mini-batch
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from . import metrics
from .data import StandardScaler, load_csv, make_regression, train_test_split
from .model import SOLVERS, LinearRegression, unscale_parameters


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="linreg", description="Linear regression from scratch with gradient descent."
    )
    src = p.add_argument_group("data")
    src.add_argument("--data", type=Path, help="CSV file with a header row (default: synthetic)")
    src.add_argument("--target", help="target column in the CSV (default: last column)")
    src.add_argument("--samples", type=int, default=200, help="synthetic sample count")
    src.add_argument("--true-weights", type=float, nargs="+", default=[3.0],
                     help="synthetic true weights (one per feature)")
    src.add_argument("--true-bias", type=float, default=4.0, help="synthetic true bias")
    src.add_argument("--noise", type=float, default=2.0, help="synthetic noise std-dev")
    src.add_argument("--test-size", type=float, default=0.2)
    src.add_argument("--seed", type=int, default=0)

    tr = p.add_argument_group("training")
    tr.add_argument("--solver", choices=SOLVERS, default="batch")
    tr.add_argument("--lr", type=float, default=0.01, help="learning rate")
    tr.add_argument("--epochs", type=int, default=2000)
    tr.add_argument("--batch-size", type=int, default=16)
    tr.add_argument("--alpha", type=float, default=0.0, help="L2 regularisation strength")
    tr.add_argument("--scale", action="store_true", help="standardise features before training")
    tr.add_argument("--compare", action="store_true",
                    help="train batch, SGD, mini-batch and normal-equation models side by side")

    p.add_argument("--plots", type=Path, help="directory to write PNG plots into")
    return p


def _train(args, solver, X_train, y_train) -> LinearRegression:
    model = LinearRegression(
        learning_rate=args.lr, epochs=args.epochs, solver=solver,
        batch_size=args.batch_size, alpha=args.alpha, seed=args.seed,
    )
    return model.fit(X_train, y_train)


def run(argv: list[str] | None = None, out=sys.stdout) -> int:
    args = build_parser().parse_args(argv)

    if args.data:
        ds = load_csv(args.data, args.target)
        source = str(args.data)
    else:
        ds = make_regression(args.samples, args.true_weights, args.true_bias,
                             args.noise, seed=args.seed)
        terms = " + ".join(f"{w:g}·{n}" for w, n in zip(args.true_weights, ds.feature_names))
        source = f"synthetic: {ds.target_name} = {terms} + {args.true_bias:g} + N(0, {args.noise:g}²)"

    X_train, X_test, y_train, y_test = train_test_split(ds.X, ds.y, args.test_size, args.seed)
    scaler = None
    if args.scale:
        scaler = StandardScaler().fit(X_train)
        X_train, X_test = scaler.transform(X_train), scaler.transform(X_test)

    print(f"Data: {source}", file=out)
    print(f"      {len(ds)} samples, {ds.X.shape[1]} feature(s), "
          f"{len(y_train)} train / {len(y_test)} test", file=out)

    solvers = ["batch", "sgd", "minibatch", "normal"] if args.compare else [args.solver]
    models: dict[str, LinearRegression] = {}
    for solver in solvers:
        try:
            models[solver] = _train(args, solver, X_train, y_train)
        except FloatingPointError as exc:
            print(f"error ({solver}): {exc}", file=out)
            return 1

    print(file=out)
    header = f"{'solver':<10} {'epochs':>7} {'train MSE':>11} {'test RMSE':>10} {'test R²':>8}"
    print(header, file=out)
    print("-" * len(header), file=out)
    for name, m in models.items():
        train_mse = metrics.mse(y_train, m.predict(X_train))
        y_hat = m.predict(X_test)
        print(f"{name:<10} {m.n_iter_:>7} {train_mse:>11.5g} "
              f"{metrics.rmse(y_test, y_hat):>10.5g} {metrics.r2_score(y_test, y_hat):>8.4f}",
              file=out)

    primary = models[solvers[0]]
    w, b = primary.weights_, primary.bias_
    if scaler is not None:
        w, b = unscale_parameters(w, b, scaler.mean_, scaler.std_)
    print(f"\nLearned parameters ({solvers[0]}, original units):", file=out)
    for name, wi in zip(ds.feature_names, w):
        print(f"  {name:<12} {wi: .4f}", file=out)
    print(f"  {'(bias)':<12} {b: .4f}", file=out)

    if args.plots:
        _write_plots(args.plots, models, primary, X_train, y_train, X_test, y_test, ds, out)
    return 0


def _write_plots(directory, models, primary, X_train, y_train, X_test, y_test, ds, out):
    from . import plotting  # imported lazily so the CLI starts fast without plots

    written = []
    histories = {k: m.history_.loss for k, m in models.items() if k != "normal"}
    if histories:
        p = directory / "loss_curve.png"
        plotting.plot_loss_curve(histories, p)
        written.append(p)
    if X_train.shape[1] == 1:
        p = directory / "fit.png"
        plotting.plot_fit(primary, np.vstack([X_train, X_test]), np.concatenate([y_train, y_test]),
                          p, xlabel=ds.feature_names[0], ylabel=ds.target_name)
        written.append(p)
        if primary.solver != "normal":
            p = directory / "loss_surface.png"
            plotting.plot_loss_surface(primary, X_train, y_train, p)
            written.append(p)
    p = directory / "predictions.png"
    plotting.plot_predictions(primary, X_test, y_test, p)
    written.append(p)
    plotting.close_all()
    print("\nPlots written:", file=out)
    for p in written:
        print(f"  {p}", file=out)


def main() -> None:
    try:
        sys.exit(run())
    except (ValueError, OSError) as exc:
        print(f"linreg: error: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
