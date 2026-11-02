"""cpusched: a discrete-event CPU scheduling simulator."""

from .algorithms import ALGORITHMS, fcfs, mlfq, round_robin, sjf, srtf
from .gantt import ascii_gantt, svg_gantt
from .metrics import ProcessStats, Summary, summarize
from .models import IDLE, Process, Schedule, Slice
from .workload import load_workload, parse_workload, random_workload

__all__ = [
    "ALGORITHMS", "fcfs", "sjf", "srtf", "round_robin", "mlfq",
    "ascii_gantt", "svg_gantt", "ProcessStats", "Summary", "summarize",
    "IDLE", "Process", "Schedule", "Slice",
    "load_workload", "parse_workload", "random_workload",
]
__version__ = "1.0.0"
