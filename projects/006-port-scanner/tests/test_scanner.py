import asyncio

import pytest

from port_scanner import scanner
from port_scanner.scanner import PortState, ScanConfig, scan
from port_scanner.targets import make_target

LOCAL = make_target("127.0.0.1")


def test_open_and_closed(server, closed_port):
    report = scan(LOCAL, [server.port, closed_port], ScanConfig(timeout=1))
    states = {r.port: r.state for r in report.results}
    assert states[server.port] is PortState.OPEN
    assert states[closed_port] is PortState.CLOSED
    assert report.open_ports == [server.port]
    assert report.counts()["open"] == 1


def test_results_sorted_by_port(server, closed_port):
    report = scan(LOCAL, [max(server.port, closed_port), min(server.port, closed_port)])
    assert [r.port for r in report.results] == sorted([server.port, closed_port])


def test_banner_grab_takes_first_line(banner_server):
    report = scan(LOCAL, [banner_server.port], ScanConfig(grab_banner=True))
    (r,) = report.results
    assert r.state is PortState.OPEN
    assert r.banner == "SSH-2.0-TestServer_1.0"


def test_no_banner_when_disabled(banner_server):
    (r,) = scan(LOCAL, [banner_server.port]).results
    assert r.banner is None


def test_timeout_is_reported_as_filtered(monkeypatch):
    async def hang(*args, **kwargs):
        await asyncio.sleep(10)
    monkeypatch.setattr(scanner.asyncio, "open_connection", hang)
    (r,) = scan(LOCAL, [9], ScanConfig(timeout=0.05)).results
    assert r.state is PortState.FILTERED and r.detail == "timeout"


def test_other_oserror_is_error(monkeypatch):
    async def boom(*args, **kwargs):
        raise OSError(99, "Cannot assign requested address")
    monkeypatch.setattr(scanner.asyncio, "open_connection", boom)
    (r,) = scan(LOCAL, [9]).results
    assert r.state is PortState.ERROR


def test_concurrency_limit_is_respected(monkeypatch):
    in_flight = peak = 0

    async def fake(*args, **kwargs):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        raise ConnectionRefusedError

    monkeypatch.setattr(scanner.asyncio, "open_connection", fake)
    report = scan(LOCAL, range(1, 101), ScanConfig(concurrency=7))
    assert len(report.results) == 100
    assert peak == 7


def test_callback_sees_every_result(server, closed_port):
    seen = []
    scan(LOCAL, [server.port, closed_port], on_result=seen.append)
    assert sorted(r.port for r in seen) == sorted([server.port, closed_port])


@pytest.mark.parametrize("cfg", [ScanConfig(concurrency=0), ScanConfig(timeout=0)])
def test_invalid_config(cfg):
    with pytest.raises(ValueError):
        scan(LOCAL, [80], cfg)


def test_many_ports_quickly(server):
    report = scan(LOCAL, range(server.port - 50, server.port + 50), ScanConfig(timeout=0.5))
    assert server.port in report.open_ports
    assert report.elapsed_s < 5
