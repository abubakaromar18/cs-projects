import json
import math
import socket

import pytest

from netspeed import SpeedClient, SpeedServer, udp_probe
from netspeed import protocol as p
from netspeed import stats
from netspeed.cli import _is_private, main, render, run_tests


# ---------------------------------------------------------------- stats

def test_mean_and_stdev():
    xs = [2, 4, 4, 4, 5, 5, 7, 9]
    assert stats.mean(xs) == 5
    assert stats.stdev(xs) == pytest.approx(2.13809, rel=1e-4)
    assert stats.stdev([3.0]) == 0.0
    with pytest.raises(ValueError):
        stats.mean([])


@pytest.mark.parametrize("p_,expected", [(0, 1), (50, 2.5), (100, 4), (25, 1.75)])
def test_percentile_linear(p_, expected):
    assert stats.percentile([4, 1, 3, 2], p_) == pytest.approx(expected)


def test_percentile_rejects_bad_input():
    with pytest.raises(ValueError):
        stats.percentile([], 50)
    with pytest.raises(ValueError):
        stats.percentile([1], 101)


def test_jitter_measures():
    assert stats.mean_abs_delta([10, 10, 10]) == 0
    assert stats.mean_abs_delta([10, 12, 10, 12]) == 2
    # RFC 3550 EWMA: first step 2/16, then converges towards 2.
    j = stats.rfc3550_jitter([10, 12])
    assert j == pytest.approx(2 / 16)
    long = stats.rfc3550_jitter([10, 12] * 200)
    assert long == pytest.approx(2, rel=1e-3)


def test_latency_summary():
    s = stats.LatencySummary.from_samples([1.0, 2.0, 3.0, 4.0, 5.0])
    assert (s.count, s.min, s.max, s.median, s.mean) == (5, 1.0, 5.0, 3.0, 3.0)
    assert s.p95 == pytest.approx(4.8)
    assert s.jitter == 1.0


def test_rate_and_byte_formatting():
    assert stats.bits_per_second(125_000, 1.0) == 1_000_000
    assert stats.format_rate(999) == "999.00 bit/s"
    assert stats.format_rate(1_500_000) == "1.50 Mbit/s"
    assert stats.format_rate(2.5e9) == "2.50 Gbit/s"
    assert stats.format_bytes(512) == "512 B"
    assert stats.format_bytes(3 * 1024 * 1024) == "3.0 MiB"
    with pytest.raises(ValueError):
        stats.bits_per_second(1, 0)


# ---------------------------------------------------------------- protocol

def test_header_roundtrip_and_recv_exact():
    a, b = socket.socketpair()
    with a, b:
        frame = p.HEADER.pack(p.CMD_DOWNLOAD, 123456789)
        assert len(frame) == 9
        # Send in two pieces to prove recv_exact reassembles partial reads.
        a.sendall(frame[:4])
        a.sendall(frame[4:])
        assert p.HEADER.unpack(p.recv_exact(b, 9)) == (p.CMD_DOWNLOAD, 123456789)
        a.close()
        with pytest.raises(ConnectionError):
            p.recv_exact(b, 1)


def test_send_bulk_and_drain_counts():
    a, b = socket.socketpair()
    with a, b:
        n = 200_000
        import threading
        t = threading.Thread(target=p.send_bulk, args=(a, n))
        t.start()
        assert p.drain(b, n) == n
        t.join()


# ---------------------------------------------------------------- end to end

@pytest.fixture
def server():
    with SpeedServer("127.0.0.1", 0) as srv:
        yield srv


def test_ping_and_latency(server):
    with SpeedClient(server.host, server.port) as c:
        rtt = c.ping()
        assert 0 < rtt < 1000
        s = c.measure_latency(count=10, warmup=1)
        assert s.count == 10
        assert s.min <= s.median <= s.max
        assert s.jitter >= 0


@pytest.mark.parametrize("n", [0, 1, 70_000, 1_000_000])
def test_download_upload_exact_bytes(server, n):
    with SpeedClient(server.host, server.port) as c:
        d = c.download(n)
        u = c.upload(n)
    assert d.bytes == u.bytes == n
    assert d.seconds > 0 and u.seconds > 0


def test_timed_transfer_runs_for_duration(server):
    with SpeedClient(server.host, server.port) as c:
        r = c.timed_transfer("download", 0.2, chunk=256 * 1024)
    assert r.seconds >= 0.2
    assert r.bytes % (256 * 1024) == 0 and r.bytes > 0
    assert r.bps > 0


def test_many_requests_on_one_connection(server):
    with SpeedClient(server.host, server.port) as c:
        for _ in range(5):
            c.download(10_000)
            c.ping()
            c.upload(10_000)


def test_concurrent_clients(server):
    clients = [SpeedClient(server.host, server.port) for _ in range(3)]
    try:
        for c in clients:
            assert c.download(50_000).bytes == 50_000
    finally:
        for c in clients:
            c.close()


def test_udp_probe_no_loss_on_loopback(server):
    r = udp_probe(server.host, server.port, count=50, interval=0.0005, size=128)
    assert r.sent == 50
    assert r.received >= 48  # loopback should be lossless; allow tiny slack
    assert r.loss <= 0.04
    assert r.duplicates == 0
    assert r.latency is not None and r.latency.min >= 0


def test_udp_probe_counts_total_loss():
    # Bind a socket nobody answers on: every probe is lost.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as silent:
        silent.bind(("127.0.0.1", 0))
        port = silent.getsockname()[1]
        r = udp_probe("127.0.0.1", port, count=5, interval=0, timeout=0.1)
    assert r.received == 0 and r.loss == 1.0 and r.latency is None


def test_unknown_command_closes_connection(server):
    with socket.create_connection((server.host, server.port), timeout=2) as s:
        s.sendall(p.HEADER.pack(b"Z", 0))
        assert s.recv(1) == b""


# ---------------------------------------------------------------- CLI

def test_run_tests_and_render(server):
    res = run_tests(server.host, server.port, pings=5, duration=0.1, udp_count=10)
    assert res["download"]["bytes"] > 0 and res["upload"]["bytes"] > 0
    text = render(res)
    assert "TCP latency" in text and "Download" in text and "UDP probes" in text


def test_cli_demo_json(capsys):
    assert main(["demo", "-n", "3", "-t", "0.1", "--udp", "5", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["tcp_latency"]["count"] == 3
    assert math.isfinite(out["download"]["bps"])


def test_cli_refuses_public_host(capsys):
    assert main(["test", "--host", "8.8.8.8"]) == 2
    assert "refusing" in capsys.readouterr().err


def test_is_private():
    assert _is_private("127.0.0.1")
    assert _is_private("192.168.1.10")
    assert not _is_private("8.8.8.8")
