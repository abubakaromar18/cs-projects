"""Invariants every scheduler must satisfy, checked on many random workloads.

``summarize`` asserts that slices don't overlap, nobody runs before it
arrives, and every process gets exactly its burst; here we add
algorithm-independent facts from scheduling theory.
"""

import pytest

from cpusched import fcfs, mlfq, random_workload, round_robin, sjf, srtf, summarize

ALL = [fcfs, sjf, srtf, lambda p: round_robin(p, 3), lambda p: mlfq(p, (2, 4, None), boost=15)]
SEEDS = range(60)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("algo", ALL)
def test_schedule_is_valid_and_work_conserving(algo, seed):
    procs = random_workload(8, seed=seed)
    sched = algo(procs)
    summary = summarize(sched)  # raises on malformed schedules
    # Work-conserving: every scheduler here keeps the CPU busy whenever a job
    # is ready, so they all finish at the same instant as FCFS.
    assert sched.makespan == fcfs(procs).makespan
    for s in summary.per_process:
        assert s.waiting >= 0 and s.response >= 0
        assert s.response <= s.waiting


@pytest.mark.parametrize("seed", SEEDS)
def test_srtf_minimises_average_waiting(seed):
    procs = random_workload(8, seed=seed)
    best = summarize(srtf(procs)).avg_waiting
    for algo in ALL:
        assert best <= summarize(algo(procs)).avg_waiting + 1e-9


@pytest.mark.parametrize("seed", SEEDS)
def test_sjf_beats_fcfs_when_all_arrive_together(seed):
    procs = random_workload(8, seed=seed, max_arrival=0)
    assert summarize(sjf(procs)).avg_waiting <= summarize(fcfs(procs)).avg_waiting


def test_random_workload_is_reproducible():
    assert random_workload(5, seed=42) == random_workload(5, seed=42)
