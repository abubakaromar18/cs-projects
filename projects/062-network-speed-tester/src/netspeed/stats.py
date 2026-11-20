"""Summary statistics for latency samples and throughput formatting.

Everything here is pure (no I/O) so it is easy to unit-test.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


def mean(xs: Sequence[float]) -> float:
    if not xs:
        raise ValueError("mean of empty sequence")
    return sum(xs) / len(xs)


def stdev(xs: Sequence[float]) -> float:
    """Sample standard deviation (Bessel-corrected, n-1)."""
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def percentile(xs: Sequence[float], p: float) -> float:
    """Percentile with linear interpolation between closest ranks.

    ``p`` is in [0, 100]. Matches numpy's default ("linear") method.
    """
    if not xs:
        raise ValueError("percentile of empty sequence")
    if not 0 <= p <= 100:
        raise ValueError("p must be in [0, 100]")
    s = sorted(xs)
    rank = (len(s) - 1) * p / 100
    lo = math.floor(rank)
    hi = math.ceil(rank)
    return s[lo] + (s[hi] - s[lo]) * (rank - lo)


def mean_abs_delta(xs: Sequence[float]) -> float:
    """Jitter as the mean absolute difference of consecutive samples.

    This is what most consumer speed tests report as "jitter" (packet delay
    variation, PDV). It ignores slow drift and reacts to sample-to-sample
    variation.
    """
    if len(xs) < 2:
        return 0.0
    return sum(abs(b - a) for a, b in zip(xs, xs[1:])) / (len(xs) - 1)


def rfc3550_jitter(xs: Sequence[float]) -> float:
    """Inter-arrival jitter estimator from RFC 3550 §6.4.1 (RTP).

    An exponentially weighted moving average with gain 1/16:
    ``J += (|D| - J) / 16``. Recent variation counts more than old variation,
    and a single outlier is smoothed rather than dominating.
    """
    j = 0.0
    for a, b in zip(xs, xs[1:]):
        j += (abs(b - a) - j) / 16
    return j


@dataclass(frozen=True)
class LatencySummary:
    count: int
    min: float
    mean: float
    median: float
    p95: float
    max: float
    stdev: float
    jitter: float
    jitter_rfc3550: float

    @classmethod
    def from_samples(cls, xs: Sequence[float]) -> "LatencySummary":
        return cls(
            count=len(xs),
            min=min(xs),
            mean=mean(xs),
            median=percentile(xs, 50),
            p95=percentile(xs, 95),
            max=max(xs),
            stdev=stdev(xs),
            jitter=mean_abs_delta(xs),
            jitter_rfc3550=rfc3550_jitter(xs),
        )


_UNITS = ["bit/s", "Kbit/s", "Mbit/s", "Gbit/s", "Tbit/s"]


def bits_per_second(nbytes: int, seconds: float) -> float:
    if seconds <= 0:
        raise ValueError("duration must be positive")
    return nbytes * 8 / seconds


def format_rate(bps: float) -> str:
    """Human-readable bit rate using SI (decimal, 1000) prefixes.

    Network rates are conventionally decimal: 1 Mbit/s = 1,000,000 bit/s.
    """
    i = 0
    while bps >= 1000 and i < len(_UNITS) - 1:
        bps /= 1000
        i += 1
    return f"{bps:.2f} {_UNITS[i]}"


def format_bytes(n: float) -> str:
    """Human-readable byte size using binary (IEC, 1024) prefixes."""
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TiB"
