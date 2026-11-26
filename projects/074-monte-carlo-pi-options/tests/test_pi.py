from math import pi

import numpy as np
import pytest

from montecarlo import estimate_pi, estimate_pi_stratified
from montecarlo.stats import Estimate, estimate_from_samples, z_score


def test_crude_pi_close_and_ci_covers_truth():
    est = estimate_pi(400_000, seed=1)
    assert abs(est.value - pi) < 0.02
    assert est.contains(pi)


def test_reproducible_with_seed():
    assert estimate_pi(10_000, seed=5) == estimate_pi(10_000, seed=5)


def test_batching_does_not_change_result():
    a = estimate_pi(50_000, seed=3, batch_size=50_000)
    b = estimate_pi(50_000, seed=3, batch_size=7_000)
    # Different batch boundaries draw the same stream in a different shape,
    # so values should agree statistically, and sample counts exactly.
    assert a.samples == b.samples == 50_000
    assert abs(a.value - b.value) < 5 * a.std_error


def test_std_error_shrinks_like_inverse_sqrt_n():
    small = estimate_pi(10_000, seed=0)
    large = estimate_pi(1_000_000, seed=0)
    ratio = small.std_error / large.std_error
    assert 8 < ratio < 12  # 100x samples -> ~10x smaller SE


def test_ci_coverage_is_about_95_percent():
    rng = np.random.default_rng(2024)
    covered = sum(estimate_pi(2_000, seed=rng).contains(pi) for _ in range(400))
    assert 0.91 <= covered / 400 <= 0.99


def test_stratified_is_more_accurate_than_crude():
    strat = estimate_pi_stratified(250_000, seed=11)
    crude = estimate_pi(250_000, seed=11)
    assert abs(strat.value - pi) < 0.002
    assert strat.std_error < crude.std_error / 5


def test_invalid_inputs():
    with pytest.raises(ValueError):
        estimate_pi(1)
    with pytest.raises(ValueError):
        estimate_pi_stratified(3)
    with pytest.raises(ValueError):
        z_score(0.42)


def test_estimate_from_samples_and_formatting():
    est = estimate_from_samples(np.array([1.0, 2.0, 3.0, 4.0]))
    assert est.value == pytest.approx(2.5)
    assert est.std_error == pytest.approx(np.std([1, 2, 3, 4], ddof=1) / 2)
    low, high = est.ci
    assert low < 2.5 < high
    assert "95% CI" in str(est)
    assert Estimate(1.0, 0.1, 10, 0.99).half_width == pytest.approx(0.2575829, rel=1e-6)
