import io
from pathlib import Path

import numpy as np
import pytest

from linreg import LinearRegression, make_regression
from linreg import plotting
from linreg.cli import run

EXAMPLE_CSV = Path(__file__).resolve().parent.parent / "examples" / "house_prices.csv"


def _run(*argv):
    out = io.StringIO()
    code = run(list(argv), out=out)
    return code, out.getvalue()


def test_cli_synthetic_default():
    code, text = _run("--epochs", "3000")
    assert code == 0
    assert "synthetic" in text and "batch" in text
    # learned weight printed in original units should be close to 3
    line = next(l for l in text.splitlines() if l.strip().startswith("x1"))
    assert float(line.split()[1]) == pytest.approx(3.0, abs=0.2)


def test_cli_compare_writes_plots(tmp_path):
    code, text = _run("--compare", "--scale", "--epochs", "300", "--plots", str(tmp_path))
    assert code == 0
    for solver in ("batch", "sgd", "minibatch", "normal"):
        assert solver in text
    for name in ("loss_curve.png", "fit.png", "loss_surface.png", "predictions.png"):
        f = tmp_path / name
        assert f.exists() and f.stat().st_size > 1000
        assert f.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_cli_csv_with_scaling(tmp_path):
    code, text = _run("--data", str(EXAMPLE_CSV), "--target", "price", "--scale",
                      "--lr", "0.05", "--epochs", "5000", "--plots", str(tmp_path))
    assert code == 0
    assert "sqft" in text and "age_years" in text
    r2 = float(next(l for l in text.splitlines() if l.startswith("batch")).split()[-1])
    assert r2 > 0.85
    assert (tmp_path / "predictions.png").exists()
    assert not (tmp_path / "fit.png").exists()  # multi-feature: no 2-D fit plot


def test_cli_reports_divergence():
    code, text = _run("--data", str(EXAMPLE_CSV), "--lr", "0.1", "--epochs", "200")
    assert code == 1
    assert "diverged" in text


def test_plot_functions_return_figures(tmp_path):
    ds = make_regression(60, [2.0], noise=1.0)
    m = LinearRegression(learning_rate=0.01, epochs=100).fit(ds.X, ds.y)
    assert plotting.plot_fit(m, ds.X, ds.y) is not None
    assert plotting.plot_loss_surface(m, ds.X, ds.y, tmp_path / "s.png") is not None
    assert (tmp_path / "s.png").exists()
    plotting.close_all()


def test_single_feature_plots_reject_multifeature():
    ds = make_regression(30, [1.0, 2.0])
    m = LinearRegression(solver="normal").fit(ds.X, ds.y)
    with pytest.raises(ValueError):
        plotting.plot_fit(m, ds.X, ds.y)
    with pytest.raises(ValueError):
        plotting.plot_loss_surface(m, ds.X, ds.y)
    assert plotting.plot_predictions(m, ds.X, ds.y) is not None
    plotting.close_all()
