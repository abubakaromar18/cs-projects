import numpy as np
import pytest

from pixelsort.intervals import edges, full, random_runs, runs, threshold


def test_runs_basic():
    m = np.array([1, 1, 0, 1, 0, 0, 1, 1, 1], dtype=bool)
    assert runs(m) == [(0, 2), (3, 4), (6, 9)]
    assert runs(np.zeros(4, bool)) == []
    assert runs(np.ones(4, bool)) == [(0, 4)]


def test_threshold():
    v = np.array([[0.1, 0.3, 0.5, 0.9]])
    assert threshold(v, lower=0.2, upper=0.6).tolist() == [[False, True, True, False]]
    with pytest.raises(ValueError):
        threshold(v, lower=0.7, upper=0.2)


def test_edges_breaks_at_jumps():
    v = np.array([[0.1, 0.1, 0.9, 0.9]])
    assert edges(v, edge_threshold=0.5).tolist() == [[True, True, False, True]]


def test_full_and_random_runs():
    v = np.zeros((50, 1000))
    assert full(v).all()
    m = random_runs(v, mean_length=20, seed=3)
    boundary_rate = 1 - m.mean()
    assert boundary_rate == pytest.approx(1 / 20, rel=0.15)
    assert (random_runs(v, mean_length=20, seed=3) == m).all()  # deterministic
