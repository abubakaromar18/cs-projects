"""Per-process and aggregate scheduling metrics, derived from a Schedule.

Definitions (all times in the simulator's abstract time units):

* completion  -- when the process's last slice ends
* turnaround  -- completion - arrival       (total time in the system)
* waiting     -- turnaround - burst          (time spent ready but not running)
* response    -- first run - arrival         (how long until it first got the CPU)
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Schedule


@dataclass(frozen=True)
class ProcessStats:
    pid: str
    arrival: int
    burst: int
    first_run: int
    completion: int

    @property
    def turnaround(self) -> int:
        return self.completion - self.arrival

    @property
    def waiting(self) -> int:
        return self.turnaround - self.burst

    @property
    def response(self) -> int:
        return self.first_run - self.arrival


@dataclass(frozen=True)
class Summary:
    algorithm: str
    per_process: list[ProcessStats]
    makespan: int
    busy_time: int
    context_switches: int

    def _avg(self, attr: str) -> float:
        return sum(getattr(s, attr) for s in self.per_process) / len(self.per_process)

    @property
    def avg_turnaround(self) -> float:
        return self._avg("turnaround")

    @property
    def avg_waiting(self) -> float:
        return self._avg("waiting")

    @property
    def avg_response(self) -> float:
        return self._avg("response")

    @property
    def utilization(self) -> float:
        """Fraction of [0, makespan) the CPU spent running a process."""
        return self.busy_time / self.makespan if self.makespan else 0.0

    @property
    def throughput(self) -> float:
        """Processes completed per time unit."""
        return len(self.per_process) / self.makespan if self.makespan else 0.0


def summarize(schedule: Schedule) -> Summary:
    """Compute metrics, and check the schedule is consistent while doing so.

    Raises ``AssertionError`` if the timeline is malformed (overlapping slices,
    a process running before it arrived, or running the wrong total time),
    which makes this function double as a test oracle for every algorithm.
    """
    first: dict[str, int] = {}
    last: dict[str, int] = {}
    ran: dict[str, int] = {}
    prev_end = 0
    for s in schedule.slices:
        assert s.start >= prev_end, f"overlapping slice at t={s.start}"
        assert s.end > s.start, f"empty slice at t={s.start}"
        prev_end = s.end
        if s.idle:
            continue
        first.setdefault(s.pid, s.start)
        last[s.pid] = s.end
        ran[s.pid] = ran.get(s.pid, 0) + s.duration

    stats = []
    for p in schedule.processes:
        assert p.pid in first, f"{p.pid} never ran"
        assert first[p.pid] >= p.arrival, f"{p.pid} ran before it arrived"
        assert ran[p.pid] == p.burst, f"{p.pid} ran {ran[p.pid]} units, needed {p.burst}"
        stats.append(ProcessStats(p.pid, p.arrival, p.burst, first[p.pid], last[p.pid]))

    return Summary(
        algorithm=schedule.algorithm,
        per_process=stats,
        makespan=schedule.makespan,
        busy_time=sum(ran.values()),
        context_switches=schedule.context_switches,
    )
