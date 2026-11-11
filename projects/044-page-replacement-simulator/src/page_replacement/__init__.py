"""Page replacement simulator: FIFO, LRU, Clock and OPT under demand paging."""

from .policies import FIFO, LRU, OPT, POLICIES, Clock, Policy, make_policy
from .simulator import Result, Step, compare, simulate

__all__ = [
    "FIFO", "LRU", "OPT", "Clock", "Policy", "POLICIES", "make_policy",
    "Result", "Step", "compare", "simulate",
]
__version__ = "1.0.0"
