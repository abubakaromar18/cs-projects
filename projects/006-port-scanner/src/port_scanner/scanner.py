"""The asyncio TCP connect scanner.

A *connect scan* performs the full three-way handshake for each port using an
ordinary socket — no raw packets or root privileges needed:

* handshake completes            -> ``open``
* peer answers with RST          -> ``closed``   (ConnectionRefusedError)
* no answer before the timeout   -> ``filtered`` (a firewall dropped the SYN)
* any other OS error             -> ``error``

Concurrency comes from asyncio: each port is a coroutine, and an
``asyncio.Semaphore`` caps how many connections are in flight at once so we
don't exhaust file descriptors or flood the target.
"""

from __future__ import annotations

import asyncio
import errno
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterable

from .ports import service_name
from .targets import Target


class PortState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"
    ERROR = "error"


@dataclass(frozen=True)
class PortResult:
    port: int
    state: PortState
    latency_ms: float | None = None
    banner: str | None = None
    detail: str | None = None

    @property
    def service(self) -> str:
        return service_name(self.port)


@dataclass
class ScanReport:
    target: Target
    results: list[PortResult] = field(default_factory=list)
    elapsed_s: float = 0.0

    def by_state(self, state: PortState) -> list[PortResult]:
        return [r for r in self.results if r.state is state]

    @property
    def open_ports(self) -> list[int]:
        return [r.port for r in self.by_state(PortState.OPEN)]

    def counts(self) -> dict[str, int]:
        return {s.value: len(self.by_state(s)) for s in PortState}


@dataclass(frozen=True)
class ScanConfig:
    timeout: float = 1.0        # seconds per connection attempt
    concurrency: int = 200      # max simultaneous connection attempts
    grab_banner: bool = False   # read a greeting from open ports
    banner_timeout: float = 0.5
    banner_bytes: int = 128


async def _read_banner(reader: asyncio.StreamReader, cfg: ScanConfig) -> str | None:
    """Many services (SSH, SMTP, FTP, Redis errors…) speak first; capture that."""
    try:
        data = await asyncio.wait_for(reader.read(cfg.banner_bytes), cfg.banner_timeout)
    except (asyncio.TimeoutError, OSError):
        return None
    text = data.decode("utf-8", errors="replace").strip()
    # Keep it to one printable line for tidy reports.
    text = "".join(ch if ch.isprintable() else " " for ch in text.splitlines()[0]) if text else ""
    return text or None


async def probe(target: Target, port: int, cfg: ScanConfig) -> PortResult:
    """Attempt a single TCP connection and classify the outcome."""
    host = str(target.address)
    start = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, family=target.family), cfg.timeout
        )
    except asyncio.TimeoutError:
        return PortResult(port, PortState.FILTERED, detail="timeout")
    except ConnectionRefusedError:
        return PortResult(port, PortState.CLOSED,
                          latency_ms=(time.perf_counter() - start) * 1000)
    except OSError as exc:
        # Unreachable host/network behaves like a filter from our viewpoint.
        if exc.errno in (errno.EHOSTUNREACH, errno.ENETUNREACH):
            return PortResult(port, PortState.FILTERED, detail=exc.strerror)
        return PortResult(port, PortState.ERROR, detail=exc.strerror or str(exc))

    latency = (time.perf_counter() - start) * 1000
    banner = await _read_banner(reader, cfg) if cfg.grab_banner else None
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        pass  # peer may already have reset the connection
    return PortResult(port, PortState.OPEN, latency_ms=latency, banner=banner)


async def scan_async(
    target: Target,
    ports: Iterable[int],
    cfg: ScanConfig = ScanConfig(),
    on_result: Callable[[PortResult], None] | None = None,
) -> ScanReport:
    """Scan *ports* on *target* concurrently, bounded by ``cfg.concurrency``."""
    if cfg.concurrency < 1:
        raise ValueError("concurrency must be >= 1")
    if cfg.timeout <= 0:
        raise ValueError("timeout must be > 0")

    sem = asyncio.Semaphore(cfg.concurrency)

    async def bounded(port: int) -> PortResult:
        async with sem:
            result = await probe(target, port, cfg)
        if on_result is not None:
            on_result(result)
        return result

    start = time.perf_counter()
    results = await asyncio.gather(*(bounded(p) for p in ports))
    return ScanReport(
        target=target,
        results=sorted(results, key=lambda r: r.port),
        elapsed_s=time.perf_counter() - start,
    )


def scan(target: Target, ports: Iterable[int], cfg: ScanConfig = ScanConfig(),
         on_result: Callable[[PortResult], None] | None = None) -> ScanReport:
    """Synchronous convenience wrapper around :func:`scan_async`."""
    return asyncio.run(scan_async(target, list(ports), cfg, on_result))
