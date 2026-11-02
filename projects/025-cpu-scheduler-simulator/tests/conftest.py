import pytest

from cpusched import Process


@pytest.fixture
def classic():
    """The textbook workload (Silberschatz et al.): P1..P4 arriving 0..3."""
    return [Process("P1", 0, 8), Process("P2", 1, 4), Process("P3", 2, 9), Process("P4", 3, 5)]


def timeline(schedule):
    """Compact form of a schedule for assertions: [(pid, start, end), ...]."""
    return [(s.pid, s.start, s.end) for s in schedule.slices]
