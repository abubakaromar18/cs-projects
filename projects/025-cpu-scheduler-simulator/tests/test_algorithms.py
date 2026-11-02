import pytest

from cpusched import IDLE, Process, fcfs, mlfq, round_robin, sjf, srtf, summarize
from conftest import timeline


# ---------------------------------------------------------------- FCFS / SJF

def test_fcfs_textbook(classic):
    s = fcfs(classic)
    assert timeline(s) == [("P1", 0, 8), ("P2", 8, 12), ("P3", 12, 21), ("P4", 21, 26)]
    assert summarize(s).avg_waiting == pytest.approx(8.75)


def test_fcfs_inserts_idle_gap():
    s = fcfs([Process("A", 0, 2), Process("B", 5, 1)])
    assert timeline(s) == [("A", 0, 2), (IDLE, 2, 5), ("B", 5, 6)]
    assert summarize(s).utilization == pytest.approx(3 / 6)


def test_fcfs_starts_idle_if_first_arrival_is_late():
    s = fcfs([Process("A", 3, 2)])
    assert timeline(s) == [(IDLE, 0, 3), ("A", 3, 5)]


def test_fcfs_ties_use_input_order():
    s = fcfs([Process("X", 0, 1), Process("Y", 0, 1), Process("Z", 0, 1)])
    assert [sl.pid for sl in s.slices] == ["X", "Y", "Z"]


def test_sjf_textbook(classic):
    s = sjf(classic)
    assert timeline(s) == [("P1", 0, 8), ("P2", 8, 12), ("P4", 12, 17), ("P3", 17, 26)]
    assert summarize(s).avg_waiting == pytest.approx(7.75)


def test_sjf_all_at_zero_sorts_by_burst():
    procs = [Process("A", 0, 6), Process("B", 0, 8), Process("C", 0, 7), Process("D", 0, 3)]
    assert [sl.pid for sl in sjf(procs).slices] == ["D", "A", "C", "B"]
    assert summarize(sjf(procs)).avg_waiting == pytest.approx(7.0)


def test_sjf_is_not_preemptive():
    s = sjf([Process("long", 0, 10), Process("short", 1, 1)])
    assert timeline(s) == [("long", 0, 10), ("short", 10, 11)]


# ---------------------------------------------------------------- SRTF

def test_srtf_textbook(classic):
    s = srtf(classic)
    assert timeline(s) == [("P1", 0, 1), ("P2", 1, 5), ("P4", 5, 10), ("P1", 10, 17), ("P3", 17, 26)]
    assert summarize(s).avg_waiting == pytest.approx(6.5)


def test_srtf_preempts_for_shorter_job():
    s = srtf([Process("long", 0, 10), Process("short", 1, 1)])
    assert timeline(s) == [("long", 0, 1), ("short", 1, 2), ("long", 2, 11)]


def test_srtf_does_not_preempt_for_equal_remaining():
    s = srtf([Process("A", 0, 4), Process("B", 2, 2)])  # at t=2 both need 2: A keeps going
    assert timeline(s) == [("A", 0, 4), ("B", 4, 6)]


# ---------------------------------------------------------------- Round Robin

def test_rr_textbook(classic):
    s = round_robin(classic, quantum=2)
    assert [sl.pid for sl in s.slices] == [
        "P1", "P2", "P3", "P1", "P4", "P2", "P3", "P1", "P4", "P3", "P1", "P4", "P3"]
    assert s.makespan == 26


def test_rr_newcomer_queued_before_preempted_job():
    # B arrives at t=2 exactly when A's quantum expires: B must run next.
    s = round_robin([Process("A", 0, 4), Process("B", 2, 2)], quantum=2)
    assert timeline(s) == [("A", 0, 2), ("B", 2, 4), ("A", 4, 6)]


def test_rr_single_job_is_merged_into_one_slice():
    s = round_robin([Process("A", 0, 7)], quantum=2)
    assert timeline(s) == [("A", 0, 7)]
    assert s.context_switches == 0


def test_rr_huge_quantum_equals_fcfs(classic):
    assert timeline(round_robin(classic, quantum=1000)) == timeline(fcfs(classic))


def test_rr_bounded_response_time():
    procs = [Process(f"P{i}", 0, 10) for i in range(5)]
    stats = summarize(round_robin(procs, quantum=3)).per_process
    # With n jobs ready together, nobody waits more than (n-1)*q to first run.
    assert max(s.response for s in stats) <= 4 * 3


def test_rr_rejects_bad_quantum(classic):
    with pytest.raises(ValueError):
        round_robin(classic, quantum=0)


# ---------------------------------------------------------------- MLFQ

def test_mlfq_demotes_after_allotment():
    s = mlfq([Process("A", 0, 10)], quanta=(2, 4, None))
    assert [(sl.start, sl.end, sl.level) for sl in s.slices] == [(0, 2, 0), (2, 6, 1), (6, 10, 2)]


def test_mlfq_short_jobs_finish_in_top_queue():
    procs = [Process("long", 0, 20), Process("i1", 5, 1), Process("i2", 6, 2)]
    s = mlfq(procs, quanta=(2, 4, None))
    short_levels = {sl.level for sl in s.slices if sl.pid in ("i1", "i2")}
    assert short_levels == {0}


def test_mlfq_arrival_preempts_lower_level():
    s = mlfq([Process("A", 0, 10), Process("B", 3, 1)], quanta=(2, 4, None))
    # A: L0 0-2, then L1 from 2; B arrives at 3 and preempts; A resumes its L1 slice.
    assert [(sl.pid, sl.start, sl.end, sl.level) for sl in s.slices] == [
        ("A", 0, 2, 0), ("A", 2, 3, 1), ("B", 3, 4, 0), ("A", 4, 7, 1), ("A", 7, 11, 2)]


def test_mlfq_preempted_job_keeps_used_allotment():
    s = mlfq([Process("A", 0, 10), Process("B", 3, 1)], quanta=(2, 4, None))
    level1_time = sum(sl.duration for sl in s.slices if sl.pid == "A" and sl.level == 1)
    assert level1_time == 4  # 1 before preemption + 3 after = the full L1 allotment


def test_mlfq_priority_boost_prevents_starvation():
    # A stream of short jobs keeps level 0 busy until t=30. Without a boost the
    # demoted long job gets no CPU at all in that window; with one it does.
    procs = [Process("long", 0, 10)] + [Process(f"s{i}", i * 2, 2) for i in range(1, 15)]

    def long_cpu_before(sched, t):
        return sum(min(sl.end, t) - sl.start for sl in sched.slices
                   if sl.pid == "long" and sl.start < t)

    assert long_cpu_before(mlfq(procs, quanta=(2, 4, None)), 30) == 2
    assert long_cpu_before(mlfq(procs, quanta=(2, 4, None), boost=8), 30) == 6


def test_mlfq_boost_resets_level():
    s = mlfq([Process("A", 0, 12)], quanta=(2, 4, None), boost=8)
    assert [(sl.start, sl.end, sl.level) for sl in s.slices] == [
        (0, 2, 0), (2, 6, 1), (6, 8, 2), (8, 10, 0), (10, 12, 1)]


def test_mlfq_single_level_is_round_robin(classic):
    m = mlfq(classic, quanta=(2,))  # one level, demotion stays at bottom = RR
    assert [sl.pid for sl in m.slices] == [sl.pid for sl in round_robin(classic, 2).slices]


@pytest.mark.parametrize("quanta", [(), (None, 2), (-1, 4)])
def test_mlfq_rejects_bad_config(classic, quanta):
    with pytest.raises(ValueError):
        mlfq(classic, quanta=quanta)


# ---------------------------------------------------------------- shared

def test_duplicate_pids_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        fcfs([Process("A", 0, 1), Process("A", 1, 1)])


def test_empty_workload_rejected():
    with pytest.raises(ValueError):
        sjf([])


@pytest.mark.parametrize("bad", [dict(arrival=-1, burst=1), dict(arrival=0, burst=0)])
def test_process_validation(bad):
    with pytest.raises(ValueError):
        Process("X", **bad)
