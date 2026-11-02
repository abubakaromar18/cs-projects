"""CPU scheduling algorithms.

Every function has the signature ``f(processes, ...) -> Schedule`` and is a
pure simulation: no wall-clock time, no threads, just a virtual clock that
jumps from event to event (an arrival, a completion, or a quantum expiry).

Tie-breaking is deterministic everywhere so results are reproducible:
when two processes are otherwise equal, the one that arrived earlier wins,
and after that the one listed first in the input.

Context-switch cost is assumed to be zero.
"""

from __future__ import annotations

import heapq
from collections import deque

from .models import IDLE, Process, Schedule, validate_processes


def _arrival_order(processes: list[Process]) -> list[Process]:
    """Processes sorted by arrival time, stable on input order."""
    return sorted(processes, key=lambda p: p.arrival)


# --------------------------------------------------------------------------
# Non-preemptive algorithms
# --------------------------------------------------------------------------

def fcfs(processes: list[Process]) -> Schedule:
    """First-Come, First-Served: run jobs to completion in arrival order.

    Simple and fair in a queueing sense, but a long job at the head of the
    queue makes every short job behind it wait (the *convoy effect*).
    """
    validate_processes(processes)
    sched = Schedule("FCFS", list(processes))
    clock = 0
    for p in _arrival_order(processes):
        if clock < p.arrival:  # CPU sits idle until the next job shows up
            sched.add(IDLE, clock, p.arrival)
            clock = p.arrival
        sched.add(p.pid, clock, clock + p.burst)
        clock += p.burst
    return sched


def sjf(processes: list[Process]) -> Schedule:
    """Shortest Job First (non-preemptive).

    Whenever the CPU becomes free, pick the ready job with the smallest burst.
    Provably minimises average waiting time among non-preemptive schedules
    when all jobs arrive together -- but it needs to know burst lengths in
    advance, and long jobs can starve if short ones keep arriving.
    """
    validate_processes(processes)
    sched = Schedule("SJF", list(processes))
    pending = deque(_arrival_order(processes))
    order = {p.pid: i for i, p in enumerate(processes)}
    ready: list[tuple[int, int, int, Process]] = []  # min-heap on (burst, arrival, input index)
    clock = 0

    while pending or ready:
        # Admit everything that has arrived by now.
        while pending and pending[0].arrival <= clock:
            p = pending.popleft()
            heapq.heappush(ready, (p.burst, p.arrival, order[p.pid], p))
        if not ready:  # nothing to do: jump the clock to the next arrival
            nxt = pending[0].arrival
            sched.add(IDLE, clock, nxt)
            clock = nxt
            continue
        *_, p = heapq.heappop(ready)
        sched.add(p.pid, clock, clock + p.burst)
        clock += p.burst
    return sched


# --------------------------------------------------------------------------
# Preemptive algorithms
# --------------------------------------------------------------------------

def srtf(processes: list[Process]) -> Schedule:
    """Shortest Remaining Time First: the preemptive version of SJF.

    The decision is re-made at every arrival: if a new job needs less time
    than what the running job has left, the running job is preempted. This
    is optimal for average waiting time over all schedules.
    """
    validate_processes(processes)
    sched = Schedule("SRTF", list(processes))
    pending = deque(_arrival_order(processes))
    order = {p.pid: i for i, p in enumerate(processes)}
    remaining = {p.pid: p.burst for p in processes}
    ready: list[tuple[int, int, int, str]] = []  # (remaining, arrival, index, pid)
    clock = 0

    while pending or ready:
        while pending and pending[0].arrival <= clock:
            p = pending.popleft()
            heapq.heappush(ready, (remaining[p.pid], p.arrival, order[p.pid], p.pid))
        if not ready:
            nxt = pending[0].arrival
            sched.add(IDLE, clock, nxt)
            clock = nxt
            continue

        rem, arr, idx, pid = heapq.heappop(ready)
        # Run until the job finishes or the next arrival forces a re-decision.
        run_until = clock + rem
        if pending:
            run_until = min(run_until, pending[0].arrival)
        sched.add(pid, clock, run_until)
        remaining[pid] -= run_until - clock
        clock = run_until
        if remaining[pid] > 0:
            heapq.heappush(ready, (remaining[pid], arr, idx, pid))
    return sched


def round_robin(processes: list[Process], quantum: int = 2) -> Schedule:
    """Round Robin with a fixed time quantum.

    Ready jobs wait in a FIFO queue; each gets at most ``quantum`` units
    before going to the back of the line. Bounded response time makes it the
    classic time-sharing scheduler. A huge quantum degenerates into FCFS; a
    tiny one gives great response time but (in real systems) many context
    switches.

    Convention: a job that arrives at the exact instant another job's
    quantum expires joins the queue *ahead of* the preempted job.
    """
    if quantum <= 0:
        raise ValueError("quantum must be > 0")
    validate_processes(processes)
    sched = Schedule(f"RR (q={quantum})", list(processes))
    pending = deque(_arrival_order(processes))
    remaining = {p.pid: p.burst for p in processes}
    ready: deque[str] = deque()
    clock = 0

    def admit(now: int) -> None:
        while pending and pending[0].arrival <= now:
            ready.append(pending.popleft().pid)

    admit(clock)
    while ready or pending:
        if not ready:
            nxt = pending[0].arrival
            sched.add(IDLE, clock, nxt)
            clock = nxt
            admit(clock)
            continue
        pid = ready.popleft()
        run = min(quantum, remaining[pid])
        sched.add(pid, clock, clock + run)
        clock += run
        remaining[pid] -= run
        admit(clock)  # newcomers first...
        if remaining[pid] > 0:
            ready.append(pid)  # ...then the preempted job
    return sched


def mlfq(
    processes: list[Process],
    quanta: tuple[int | None, ...] = (2, 4, None),
    boost: int | None = None,
) -> Schedule:
    """Multi-Level Feedback Queue, following the rules in OSTEP chapter 8.

    * There is one FIFO queue per level; level 0 has the highest priority.
      ``quanta[i]`` is the time allotment at level ``i``; ``None`` (or 0)
      means unlimited, i.e. the bottom queue is FCFS.
    * Rule 1/2: the CPU always runs the head of the highest non-empty queue.
    * Rule 3: a new job enters at level 0.
    * Rule 4: once a job has used up its allotment at a level (across any
      number of turns) it is demoted one level and goes to the back.
    * Rule 5: every ``boost`` time units all jobs move back to level 0, so
      long-running jobs cannot starve and jobs that turn interactive regain
      priority.

    Preemption: when a job arrives at a higher level than the one currently
    running, the running job is interrupted and placed at the *front* of its
    own queue, keeping the allotment it has already used.

    Because these jobs are purely CPU-bound, MLFQ here learns that long jobs
    are long and pushes them down, approximating SJF without knowing bursts.
    """
    if not quanta:
        raise ValueError("MLFQ needs at least one level")
    levels = [None if (q is None or q == 0) else q for q in quanta]
    if any(q is not None and q < 0 for q in levels):
        raise ValueError("quanta must be positive (0/None = unlimited)")
    if any(q is None for q in levels[:-1]):
        raise ValueError("only the bottom MLFQ level may have an unlimited quantum")
    if boost is not None and boost <= 0:
        raise ValueError("boost period must be > 0")
    validate_processes(processes)

    name = "MLFQ (" + "/".join("∞" if q is None else str(q) for q in levels)
    name += f", boost={boost})" if boost else ")"
    sched = Schedule(name, list(processes))

    pending = deque(_arrival_order(processes))
    remaining = {p.pid: p.burst for p in processes}
    level_of: dict[str, int] = {}
    used: dict[str, int] = {}  # allotment consumed at the current level
    queues: list[deque[str]] = [deque() for _ in levels]
    clock = 0
    next_boost = boost if boost else None

    def admit(now: int) -> None:
        while pending and pending[0].arrival <= now:
            pid = pending.popleft().pid
            level_of[pid], used[pid] = 0, 0
            queues[0].append(pid)

    def do_boost() -> None:
        # Preserve relative order: higher levels first, FIFO within a level.
        everyone = [pid for q in queues for pid in q]
        for q in queues:
            q.clear()
        for pid in everyone:
            level_of[pid], used[pid] = 0, 0
            queues[0].append(pid)

    def top_level() -> int | None:
        return next((i for i, q in enumerate(queues) if q), None)

    admit(clock)
    while pending or any(queues):
        lvl = top_level()
        if lvl is None:  # idle until the next arrival (boosts are no-ops on an empty system)
            nxt = pending[0].arrival
            sched.add(IDLE, clock, nxt)
            clock = nxt
            while next_boost is not None and next_boost <= clock:
                next_boost += boost  # type: ignore[operator]
            admit(clock)
            continue

        pid = queues[lvl].popleft()
        # The job runs until the first of: it finishes, its allotment runs
        # out, a new job arrives (may preempt), or a priority boost fires.
        events = [clock + remaining[pid]]
        if levels[lvl] is not None:
            events.append(clock + levels[lvl] - used[pid])
        if pending:
            events.append(pending[0].arrival)
        if next_boost is not None:
            events.append(next_boost)
        stop = min(events)

        sched.add(pid, clock, stop, level=lvl)
        ran = stop - clock
        clock = stop
        remaining[pid] -= ran
        used[pid] += ran

        admit(clock)
        if remaining[pid] == 0:
            pass  # done
        elif levels[lvl] is not None and used[pid] >= levels[lvl]:
            new = min(lvl + 1, len(levels) - 1)  # Rule 4: demote
            level_of[pid], used[pid] = new, 0
            queues[new].append(pid)
        else:
            # Interrupted mid-allotment (arrival or boost): resume first.
            queues[lvl].appendleft(pid)

        if next_boost is not None and clock >= next_boost:
            do_boost()
            next_boost += boost  # type: ignore[operator]
    return sched


ALGORITHMS = {
    "fcfs": fcfs,
    "sjf": sjf,
    "srtf": srtf,
    "rr": round_robin,
    "mlfq": mlfq,
}
