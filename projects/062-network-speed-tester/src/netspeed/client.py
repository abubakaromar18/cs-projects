"""Measurement client: latency, jitter, throughput and UDP packet loss."""

from __future__ import annotations

import os
import select
import socket
import time
from dataclasses import dataclass, field

from . import protocol as p
from .stats import LatencySummary, bits_per_second


@dataclass(frozen=True)
class ThroughputResult:
    direction: str  # "download" or "upload"
    bytes: int
    seconds: float

    @property
    def bps(self) -> float:
        return bits_per_second(self.bytes, self.seconds)


@dataclass(frozen=True)
class UDPResult:
    sent: int
    received: int
    duplicates: int
    reordered: int
    rtts_ms: list[float] = field(repr=False)

    @property
    def loss(self) -> float:
        """Fraction of probes that never came back, in [0, 1]."""
        return 0.0 if self.sent == 0 else (self.sent - self.received) / self.sent

    @property
    def latency(self) -> LatencySummary | None:
        return LatencySummary.from_samples(self.rtts_ms) if self.rtts_ms else None


class SpeedClient:
    """Holds one TCP connection to a :class:`~netspeed.server.SpeedServer`."""

    def __init__(self, host: str = "127.0.0.1", port: int = p.DEFAULT_PORT, timeout: float = 5.0):
        self.host, self.port, self.timeout = host, port, timeout
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    # -- latency ----------------------------------------------------------

    def ping(self) -> float:
        """One application-level round trip over TCP; returns RTT in ms."""
        nonce = int.from_bytes(os.urandom(8), "big")
        t0 = time.perf_counter_ns()
        self.sock.sendall(p.HEADER.pack(p.CMD_PING, nonce))
        cmd, echoed = p.HEADER.unpack(p.recv_exact(self.sock, p.HEADER.size))
        t1 = time.perf_counter_ns()
        if cmd != p.CMD_PING or echoed != nonce:
            raise ConnectionError("PING reply did not match request")
        return (t1 - t0) / 1e6

    def measure_latency(self, count: int = 20, interval: float = 0.0, warmup: int = 2) -> LatencySummary:
        """Send ``count`` pings and summarise them.

        A few warm-up pings are discarded first: the very first exchange pays
        for things like page faults and cold caches, not network delay.
        """
        for _ in range(warmup):
            self.ping()
        samples = []
        for i in range(count):
            samples.append(self.ping())
            if interval and i < count - 1:
                time.sleep(interval)
        return LatencySummary.from_samples(samples)

    # -- throughput -------------------------------------------------------

    def download(self, nbytes: int) -> ThroughputResult:
        """Ask the server to send ``nbytes`` and time how long it takes."""
        t0 = time.perf_counter()
        self.sock.sendall(p.HEADER.pack(p.CMD_DOWNLOAD, nbytes))
        got = p.drain(self.sock, nbytes)
        elapsed = time.perf_counter() - t0
        if got != nbytes:
            raise ConnectionError(f"download truncated: {got}/{nbytes} bytes")
        return ThroughputResult("download", got, elapsed)

    def upload(self, nbytes: int) -> ThroughputResult:
        """Send ``nbytes`` to the server; stop the clock at its acknowledgement.

        Timing until the ack (not just until ``sendall`` returns) matters:
        ``sendall`` only means the data reached our kernel's send buffer, which
        can hold megabytes. Waiting for the ack measures bytes delivered.
        """
        t0 = time.perf_counter()
        self.sock.sendall(p.HEADER.pack(p.CMD_UPLOAD, nbytes))
        p.send_bulk(self.sock, nbytes)
        (acked,) = p.COUNT.unpack(p.recv_exact(self.sock, p.COUNT.size))
        elapsed = time.perf_counter() - t0
        if acked != nbytes:
            raise ConnectionError(f"upload acknowledged {acked}/{nbytes} bytes")
        return ThroughputResult("upload", acked, elapsed)

    def timed_transfer(self, direction: str, seconds: float, chunk: int = 4 * 1024 * 1024) -> ThroughputResult:
        """Repeat transfers of ``chunk`` bytes until ``seconds`` have elapsed.

        Fixed-duration tests adapt to link speed: a slow link moves few bytes,
        a fast one many, but each test takes about the same wall time. The
        first chunk is treated as TCP slow-start warm-up and excluded.
        """
        op = self.download if direction == "download" else self.upload
        op(chunk)  # warm-up: let the congestion window open
        total, start = 0, time.perf_counter()
        while True:
            total += op(chunk).bytes
            elapsed = time.perf_counter() - start
            if elapsed >= seconds:
                return ThroughputResult(direction, total, elapsed)

    # -- lifecycle --------------------------------------------------------

    def close(self) -> None:
        try:
            self.sock.sendall(p.HEADER.pack(p.CMD_QUIT, 0))
        except OSError:
            pass
        self.sock.close()

    def __enter__(self) -> "SpeedClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def udp_probe(
    host: str = "127.0.0.1",
    port: int = p.DEFAULT_PORT,
    count: int = 100,
    interval: float = 0.005,
    size: int = 64,
    timeout: float = 1.0,
) -> UDPResult:
    """Fire ``count`` numbered UDP datagrams and collect the echoes.

    UDP has no retransmission, so lost datagrams stay lost; that makes it the
    right transport for measuring packet loss and delay variation.
    Sequence numbers let us detect duplicates and out-of-order arrivals.
    """
    size = max(size, p.UDP_PROBE.size)
    pad = b"\x00" * (size - p.UDP_PROBE.size)
    rtts: dict[int, float] = {}
    dupes = reordered = 0
    highest = -1

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect((host, port))
        s.setblocking(False)

        def wait_and_collect(seconds: float) -> None:
            """Block up to ``seconds`` waiting for echoes, timestamping each
            one as soon as it arrives (a plain sleep would inflate RTTs)."""
            end = time.perf_counter() + seconds
            while True:
                left = end - time.perf_counter()
                if left <= 0:
                    return
                ready, _, _ = select.select([s], [], [], left)
                if ready:
                    collect()

        def collect() -> None:
            nonlocal dupes, reordered, highest
            while True:
                try:
                    data = s.recv(65535)
                except (BlockingIOError, ConnectionRefusedError):
                    return
                now = time.perf_counter_ns()
                if len(data) < p.UDP_PROBE.size:
                    continue
                seq, sent_ns = p.UDP_PROBE.unpack_from(data)
                if seq in rtts:
                    dupes += 1
                    continue
                if seq < highest:
                    reordered += 1
                highest = max(highest, seq)
                rtts[seq] = (now - sent_ns) / 1e6

        for seq in range(count):
            s.send(p.UDP_PROBE.pack(seq, time.perf_counter_ns()) + pad)
            collect()
            if interval:
                wait_and_collect(interval)

        # Grace period for stragglers still in flight.
        deadline = time.perf_counter() + timeout
        while len(rtts) < count and time.perf_counter() < deadline:
            wait_and_collect(min(0.01, deadline - time.perf_counter()))

    ordered = [rtts[k] for k in sorted(rtts)]
    return UDPResult(count, len(rtts), dupes, reordered, ordered)
