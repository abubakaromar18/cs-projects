import numpy as np
import pytest

from linreg import StandardScaler, load_csv, mae, make_regression, mse, r2_score, rmse, train_test_split


# ---------------------------------------------------------------- metrics

def test_metrics_known_values():
    y, y_hat = [1, 2, 3, 4], [1, 2, 3, 6]
    assert mse(y, y_hat) == pytest.approx(1.0)
    assert rmse(y, y_hat) == pytest.approx(1.0)
    assert mae(y, y_hat) == pytest.approx(0.5)
    # SS_tot = 5, SS_res = 4
    assert r2_score(y, y_hat) == pytest.approx(0.2)


def test_r2_edge_cases():
    assert r2_score([1, 2, 3], [1, 2, 3]) == 1.0
    assert r2_score([1, 2, 3], [2, 2, 2]) == pytest.approx(0.0)
    assert r2_score([1, 2, 3], [3, 2, 1]) < 0
    assert r2_score([5, 5], [5, 5]) == 1.0
    assert r2_score([5, 5], [4, 6]) == 0.0


def test_metrics_validate_input():
    with pytest.raises(ValueError):
        mse([1, 2], [1])
    with pytest.raises(ValueError):
        mae([], [])


# ---------------------------------------------------------------- data

def test_make_regression_shape_and_determinism():
    a = make_regression(50, [1.0, 2.0], seed=3)
    b = make_regression(50, [1.0, 2.0], seed=3)
    assert a.X.shape == (50, 2) and a.y.shape == (50,)
    assert a.feature_names == ["x1", "x2"]
    np.testing.assert_array_equal(a.X, b.X)


def test_make_regression_noiseless_is_exact():
    ds = make_regression(20, [2.0], bias=1.0, noise=0.0)
    np.testing.assert_allclose(ds.y, 2.0 * ds.X[:, 0] + 1.0)


def test_train_test_split_partitions_rows():
    X = np.arange(20).reshape(10, 2)
    y = np.arange(10)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, seed=1)
    assert len(Xte) == 3 and len(Xtr) == 7
    assert sorted(np.concatenate([ytr, yte]).tolist()) == list(range(10))
    np.testing.assert_array_equal(Xtr[:, 0] // 2, ytr)  # rows stay aligned
    with pytest.raises(ValueError):
        train_test_split(X, y, test_size=1.5)


def test_scaler_zero_mean_unit_variance_and_inverse():
    rng = np.random.default_rng(0)
    X = rng.normal([5, -2, 100], [1, 4, 30], size=(200, 3))
    s = StandardScaler()
    Z = s.fit_transform(X)
    np.testing.assert_allclose(Z.mean(axis=0), 0, atol=1e-12)
    np.testing.assert_allclose(Z.std(axis=0), 1, atol=1e-12)
    np.testing.assert_allclose(s.inverse_transform(Z), X)


def test_scaler_constant_column_and_unfitted():
    s = StandardScaler().fit(np.array([[1.0, 3.0], [2.0, 3.0]]))
    assert np.all(np.isfinite(s.transform([[1.5, 3.0]])))
    with pytest.raises(RuntimeError):
        StandardScaler().transform([[1.0]])


def test_load_csv(tmp_path):
    p = tmp_path / "d.csv"
    p.write_text("a,target,b\n1,10,2\n3,30,4\n\n")
    ds = load_csv(p, target="target")
    assert ds.feature_names == ["a", "b"]
    np.testing.assert_array_equal(ds.X, [[1, 2], [3, 4]])
    np.testing.assert_array_equal(ds.y, [10, 30])
    assert load_csv(p).target_name == "b"  # default: last column


@pytest.mark.parametrize(
    "content, msg",
    [("", "empty"), ("a,b\n", "no data"), ("a,b\n1,x\n", "non-numeric"), ("a\n1\n", "at least")],
)
def test_load_csv_errors(tmp_path, content, msg):
    p = tmp_path / "bad.csv"
    p.write_text(content)
    with pytest.raises(ValueError, match=msg):
        load_csv(p)


def test_load_csv_missing_target(tmp_path):
    p = tmp_path / "d.csv"
    p.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError, match="not in header"):
        load_csv(p, target="zzz")
