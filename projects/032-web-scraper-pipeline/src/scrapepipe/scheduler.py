"""A small interval scheduler with drift correction, jitter and backoff.

Why not just ``while True: job(); sleep(interval)``? Because the job's own
running time makes every cycle drift later. Here each run is scheduled at
``start + k * interval`` (fixed-rate), and if a run overruns we skip missed
slots rather than firing a burst to "catch up".

On failure the next attempt is delayed with exponential backoff (capped),
and the normal cadence resumes after the next success.

Clock and sleep are injected so the whole thing is deterministic in tests.
"""

from __future__ import annotations

import logging
import random
import signal
import time
from dataclasses import dataclass, field
from typing import Callable

log = logging.getLogger("scrapepipe.scheduler")


@dataclass
class Scheduler:
    job: Callable[[], object]
    interval: float
    jitter: float = 0.0  # +/- seconds of random offset, spreads load
    retry_base: float = 5.0  # first retry delay after a failure
    max_backoff: float = 3600.0
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    rng: random.Random = field(default_factory=random.Random)

    runs: int = 0
    failures: int = 0
    _stop: bool = False

    def stop(self, *_):
        self._stop = True

    def next_delay(self, start: float, now: float, consecutive_failures: int) -> float:
        """Seconds to wait before the next run. Pure given its inputs (+rng)."""
        if consecutive_failures:
            # Exponential backoff: retry_base, 2x, 4x, ... capped.
            return min(self.retry_base * 2 ** (consecutive_failures - 1), self.max_backoff)
        # Fixed-rate: the first slot start + k*interval strictly after now.
        slots = int((now - start) // self.interval) + 1
        target = start + slots * self.interval
        if self.jitter:
            target += self.rng.uniform(-self.jitter, self.jitter)
        return max(0.0, target - now)

    def run_forever(self, max_runs: int | None = None, install_signals: bool = False) -> None:
        if install_signals:
            signal.signal(signal.SIGINT, self.stop)
            signal.signal(signal.SIGTERM, self.stop)
        start = self.clock()
        consecutive = 0
        while not self._stop:
            try:
                result = self.job()
                consecutive = 0
                log.info("run %d ok: %s", self.runs + 1, result)
            except Exception as e:  # keep the scheduler alive
                consecutive += 1
                self.failures += 1
                log.error("run %d failed (%d in a row): %s", self.runs + 1, consecutive, e)
            self.runs += 1
            if max_runs is not None and self.runs >= max_runs:
                break
            now = self.clock()
            delay = self.next_delay(start, now, consecutive)
            if consecutive:
                start = now + delay  # after a retry, cadence restarts from it
            self.sleep(delay)
