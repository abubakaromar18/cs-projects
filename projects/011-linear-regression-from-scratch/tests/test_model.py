import numpy as np
import pytest

from linreg import LinearRegression, StandardScaler, make_regression, unscale_parameters


@pytest.fixture
def simple():
    # y = 3x + 4 with mild noise; x in [0, 10]
    return make_regression(n_samples=300, weights=[3.0], bias=4.0, noise=0.5, seed=1)


def test_normal_equation_recovers_true_parameters(simple):
    m = LinearRegression(solver="normal").fit(simple.X, simple.y)
    assert m.weights_[0] == pytest.approx(3.0, abs=0.05)
    assert m.bias_ == pytest.approx(4.0, abs=0.2)
    assert m.converged_


def test_batch_gd_matches_normal_equation(simple):
    ref = LinearRegression(solver="normal").fit(simple.X, simple.y)
    gd = LinearRegression(learning_rate=0.02, epochs=20000, solver="batch").fit(simple.X, simple.y)
    assert gd.weights_[0] == pytest.approx(ref.weights_[0], abs=1e-3)
    assert gd.bias_ == pytest.approx(ref.bias_, abs=1e-2)


@pytest.mark.parametrize("solver", ["sgd", "minibatch"])
def test_stochastic_solvers_get_close(simple, solver):
    scaler = StandardScaler()
    Xs = scaler.fit_transform(simple.X)
    m = LinearRegression(learning_rate=0.005, epochs=300, solver=solver, seed=3).fit(Xs, simple.y)
    w, b = unscale_parameters(m.weights_, m.bias_, scaler.mean_, scaler.std_)
    assert w[0] == pytest.approx(3.0, abs=0.15)
    assert b == pytest.approx(4.0, abs=0.6)
    assert m.score(Xs, simple.y) > 0.99


def test_multivariate_with_scaling():
    ds = make_regression(n_samples=500, weights=[2.0, -1.5, 0.5], bias=-3.0, noise=0.1, seed=7)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(ds.X)
    m = LinearRegression(learning_rate=0.1, epochs=5000).fit(Xs, ds.y)
    w, b = unscale_parameters(m.weights_, m.bias_, scaler.mean_, scaler.std_)
    np.testing.assert_allclose(w, [2.0, -1.5, 0.5], atol=0.02)
    assert b == pytest.approx(-3.0, abs=0.1)
    assert m.converged_


def test_loss_decreases_monotonically_for_batch_gd(simple):
    m = LinearRegression(learning_rate=0.01, epochs=200).fit(simple.X, simple.y)
    loss = np.array(m.history_.loss)
    assert len(loss) == m.n_iter_ + 1  # initial loss + one per epoch
    assert np.all(np.diff(loss) <= 1e-12)
    assert loss[-1] < loss[0] / 100


def test_history_records_parameters(simple):
    m = LinearRegression(learning_rate=0.01, epochs=10, tol=0).fit(simple.X, simple.y)
    assert len(m.history_.weights) == len(m.history_.bias) == 11
    assert m.history_.weights[0][0] == 0.0 and m.history_.bias[0] == 0.0
    np.testing.assert_allclose(m.history_.weights[-1], m.weights_)


def test_gradient_matches_finite_differences():
    rng = np.random.default_rng(0)
    X, y = rng.normal(size=(20, 3)), rng.normal(size=20)
    w, b = rng.normal(size=3), 0.7
    m = LinearRegression(alpha=0.3)
    gw, gb = m.gradients(X, y, w, b)
    eps = 1e-6
    for i in range(3):
        e = np.zeros(3)
        e[i] = eps
        num = (m.loss(X, y, w + e, b) - m.loss(X, y, w - e, b)) / (2 * eps)
        assert gw[i] == pytest.approx(num, rel=1e-5)
    num_b = (m.loss(X, y, w, b + eps) - m.loss(X, y, w, b - eps)) / (2 * eps)
    assert gb == pytest.approx(num_b, rel=1e-5)


def test_ridge_shrinks_weights_and_gd_agrees_with_closed_form(simple):
    Xs = StandardScaler().fit_transform(simple.X)
    plain = LinearRegression(solver="normal").fit(Xs, simple.y)
    ridge = LinearRegression(solver="normal", alpha=1.0).fit(Xs, simple.y)
    gd = LinearRegression(learning_rate=0.05, epochs=5000, alpha=1.0).fit(Xs, simple.y)
    assert abs(ridge.weights_[0]) < abs(plain.weights_[0])
    assert gd.weights_[0] == pytest.approx(ridge.weights_[0], abs=1e-4)
    assert gd.bias_ == pytest.approx(ridge.bias_, abs=1e-4)


def test_divergence_raises():
    ds = make_regression(n_samples=50, weights=[3.0], noise=0.1, x_range=(0, 1000))
    with pytest.raises(FloatingPointError, match="diverged"):
        LinearRegression(learning_rate=1.0, epochs=500).fit(ds.X, ds.y)


def test_early_stopping(simple):
    Xs = StandardScaler().fit_transform(simple.X)
    m = LinearRegression(learning_rate=0.1, epochs=100000, tol=1e-9).fit(Xs, simple.y)
    assert m.converged_
    assert m.n_iter_ < 100000


def test_accepts_1d_x_and_predicts(simple):
    x = simple.X[:, 0]
    m = LinearRegression(solver="normal").fit(x, simple.y)
    assert m.predict([0.0, 1.0]) == pytest.approx([m.bias_, m.bias_ + m.weights_[0]])


@pytest.mark.parametrize(
    "kwargs",
    [{"solver": "adam"}, {"learning_rate": 0}, {"epochs": 0}, {"batch_size": 0}, {"alpha": -1}],
)
def test_invalid_hyperparameters(kwargs):
    with pytest.raises(ValueError):
        LinearRegression(**kwargs)


def test_errors_on_bad_usage(simple):
    m = LinearRegression()
    with pytest.raises(RuntimeError):
        m.predict(simple.X)
    with pytest.raises(ValueError):
        m.fit(simple.X, simple.y[:-1])
    m.fit(simple.X, simple.y)
    with pytest.raises(ValueError, match="features"):
        m.predict(np.ones((3, 2)))


def test_unscale_parameters_roundtrip():
    rng = np.random.default_rng(5)
    X = rng.normal(10, 3, size=(40, 2))
    scaler = StandardScaler().fit(X)
    w_s, b_s = np.array([1.5, -2.0]), 0.25
    w, b = unscale_parameters(w_s, b_s, scaler.mean_, scaler.std_)
    np.testing.assert_allclose(scaler.transform(X) @ w_s + b_s, X @ w + b)
