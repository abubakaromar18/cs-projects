"""Core data types shared by every scheduler.

A scheduler takes a list of :class:`Process` objects and produces a
:class:`Schedule`: an ordered list of :class:`Slice` objects saying which
process held the CPU over which half-open time interval ``[start, end)``.
Everything else (metrics, Gantt charts) is derived from that timeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

IDLE = None  # pid used for slices where the CPU had nothing to run


@dataclass(frozen=True)
class Process:
    """A CPU-bound job: it arrives once and needs ``burst`` units of CPU."""

    pid: str
    arrival: int
    burst: int

    def __post_init__(self) -> None:
        if not self.pid:
            raise ValueError("process id must be non-empty")
        if self.arrival < 0:
            raise ValueError(f"{self.pid}: arrival must be >= 0")
        if self.burst <= 0:
            raise ValueError(f"{self.pid}: burst must be > 0")


@dataclass(frozen=True)
class Slice:
    """``pid`` ran on the CPU from ``start`` (inclusive) to ``end`` (exclusive).

    ``pid is IDLE`` marks a gap where no process was ready.
    ``level`` is the MLFQ queue the process ran from (``None`` elsewhere).
    """

    pid: str | None
    start: int
    end: int
    level: int | None = None

    @property
    def duration(self) -> int:
        return self.end - self.start

    @property
    def idle(self) -> bool:
        return self.pid is IDLE


@dataclass
class Schedule:
    """The output of a scheduling algorithm."""

    algorithm: str
    processes: list[Process]
    slices: list[Slice] = field(default_factory=list)

    def add(self, pid: str | None, start: int, end: int, level: int | None = None) -> None:
        """Append a slice, merging it with the previous one when contiguous.

        Merging keeps Gantt charts readable: a process that is picked again
        immediately (e.g. the only ready job in Round Robin) shows as one bar.
        """
        if end <= start:
            return
        if self.slices:
            last = self.slices[-1]
            if last.pid == pid and last.end == start and last.level == level:
                self.slices[-1] = Slice(pid, last.start, end, level)
                return
        self.slices.append(Slice(pid, start, end, level))

    @property
    def makespan(self) -> int:
        return self.slices[-1].end if self.slices else 0

    @property
    def context_switches(self) -> int:
        """Number of times the CPU switched from one process to a different one.

        Idle gaps are ignored: P1, idle, P1 counts as zero switches, while
        P1, idle, P2 counts as one.
        """
        busy = [s.pid for s in self.slices if not s.idle]
        return sum(1 for a, b in zip(busy, busy[1:]) if a != b)


def validate_processes(processes: list[Process]) -> list[Process]:
    """Reject empty workloads and duplicate ids; return the list unchanged."""
    if not processes:
        raise ValueError("workload has no processes")
    seen: set[str] = set()
    for p in processes:
        if p.pid in seen:
            raise ValueError(f"duplicate process id {p.pid!r}")
        seen.add(p.pid)
    return processes
