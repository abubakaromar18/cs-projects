import pytest

from page_replacement import simulate
from page_replacement.analysis import (
    find_anomalies, is_stack_inclusive, search_belady, sweep,
)
from page_replacement.refstrings import BELADY, TEXTBOOK, locality, parse, uniform


def test_steps_record_frames_and_evictions():
    r = simulate([1, 2, 3, 1, 4], 3, "fifo")
    assert [s.hit for s in r.steps] == [False, False, False, True, False]
    assert r.steps[2].frames == (1, 2, 3)
    last = r.steps[-1]
    assert last.evicted == 1 and last.frames == (4, 2, 3) and last.slot == 0
    assert r.evictions == 1 and r.hits == 1 and r.fault_rate == pytest.approx(0.8)


def test_pages_stay_in_their_slot_until_evicted():
    r = simulate(TEXTBOOK, 3, "lru")
    for prev, cur in zip(r.steps, r.steps[1:]):
        changed = [i for i in range(3) if prev.frames[i] != cur.frames[i]]
        assert len(changed) <= 1
        if cur.hit:
            assert not changed


def test_empty_and_invalid():
    assert simulate([], 3, "lru").faults == 0
    assert simulate([], 3, "lru").hit_ratio == 0.0
    with pytest.raises(ValueError):
        simulate([1], 0, "lru")


def test_record_false_still_counts():
    assert simulate(TEXTBOOK, 3, "opt", record=False).faults == 9


def test_sweep_and_anomaly_detection():
    curves = sweep(BELADY, ["fifo", "lru"], range(1, 6))
    assert curves["fifo"][3] == 9 and curves["fifo"][4] == 10
    anomalies = find_anomalies(curves)
    assert [(a.algorithm, a.frames, a.more_frames) for a in anomalies] == [
        ("fifo", 3, 4)
    ]


def test_search_finds_fifo_anomaly_but_not_lru():
    found = search_belady("fifo", seed=0)
    assert found is not None
    refs, a = found
    assert simulate(refs, a.more_frames, "fifo").faults > simulate(
        refs, a.frames, "fifo"
    ).faults
    assert search_belady("lru", tries=500, seed=0) is None
    assert search_belady("opt", tries=500, seed=0) is None


@pytest.mark.parametrize("algo, expected", [("lru", True), ("opt", True), ("fifo", False)])
def test_inclusion_property(algo, expected):
    assert is_stack_inclusive(BELADY, algo, 5) is expected


def test_parse():
    assert parse("7 0,1 ,, 2\n3") == (7, 0, 1, 2, 3)
    for bad in ("", "1 x 2", "1 -2"):
        with pytest.raises(ValueError):
            parse(bad)


def test_generators_are_deterministic_and_in_range():
    assert uniform(50, 6, seed=3) == uniform(50, 6, seed=3)
    assert set(uniform(500, 6, seed=3)) <= set(range(6))
    ws = locality(300, 30, working_set=3, phase=30, jump=0.0, seed=5)
    assert len(ws) == 300
    for i in range(0, 300, 30):
        assert len(set(ws[i:i + 30])) <= 3
    with pytest.raises(ValueError):
        locality(10, 3, working_set=5)


def test_locality_rewards_recency():
    refs = locality(2000, 30, working_set=4, seed=11)
    assert simulate(refs, 5, "lru").faults < simulate(refs, 5, "fifo").faults
