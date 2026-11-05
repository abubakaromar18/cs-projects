import random

from scrapepipe.fetcher import RateLimiter
from scrapepipe.scheduler import Scheduler


class FakeClock:
    """A virtual clock: sleeping just advances time."""

    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def __call__(self):
        return self.t

    def sleep(self, d):
        self.sleeps.append(round(d, 6))
        self.t += d


def test_fixed_rate_corrects_for_job_duration():
    clk = FakeClock()

    def job():
        clk.t += 3  # job takes 3s

    s = Scheduler(job, interval=10, clock=clk, sleep=clk.sleep)
    s.run_forever(max_runs=4)
    assert clk.sleeps == [7, 7, 7]  # not 10: no drift
    assert s.runs == 4 and s.failures == 0


def test_overrun_skips_missed_slots():
    clk = FakeClock()
    durations = iter([25, 1])

    def job():
        clk.t += next(durations)

    s = Scheduler(job, interval=10, clock=clk, sleep=clk.sleep)
    s.run_forever(max_runs=2)
    assert clk.sleeps == [5]  # ran 0..25, next slot is 30, not 10 and 20


def test_backoff_on_failure_then_recovers():
    clk = FakeClock()
    outcomes = iter([False, False, False, True, True])

    def job():
        if not next(outcomes):
            raise RuntimeError("boom")

    s = Scheduler(job, interval=100, retry_base=5, max_backoff=15, clock=clk, sleep=clk.sleep)
    s.run_forever(max_runs=5)
    assert clk.sleeps == [5, 10, 15, 100]  # 5, 10, capped at 15, then normal cadence
    assert s.failures == 3


def test_jitter_stays_within_bounds():
    s = Scheduler(lambda: None, interval=60, jitter=5, rng=random.Random(1))
    delays = [s.next_delay(0, 0, 0) for _ in range(100)]
    assert all(55 <= d <= 65 for d in delays) and len(set(delays)) > 1


def test_stop_flag():
    clk = FakeClock()
    s = Scheduler(lambda: None, interval=1, clock=clk, sleep=clk.sleep)
    s.job = s.stop
    s.run_forever()
    assert s.runs == 1


def test_rate_limiter_spaces_requests_per_host():
    clk = FakeClock()
    rl = RateLimiter(min_interval=2, clock=clk, sleep=clk.sleep)
    assert rl.wait("a") == 0
    assert rl.wait("a") == 2
    assert rl.wait("b") == 0  # different host is independent
    clk.t += 5
    assert rl.wait("a") == 0
