# 062 · Network Speed Tester

A small **iperf-style** client/server tool that measures **latency**, **jitter**,
**throughput** (download and upload) and **UDP packet loss** between two machines
you control. It ships its own server, so it never touches a third-party speed
test service. Pure Python standard library, no runtime dependencies.

```
$ make demo
netspeed → 127.0.0.1:40303

TCP latency (20 samples)
  min/avg/median/p95/max  0.006 / 0.006 / 0.006 / 0.007 / 0.009 ms
  stdev 0.001 ms   jitter 0.000 ms   jitter(RFC 3550) 0.000 ms

Download     17.14 Gbit/s   (2.0 GiB in 1.00 s)
Upload       19.82 Gbit/s   (2.3 GiB in 1.00 s)

UDP probes: 100/100 returned, loss 0.0%, 0 reordered, 0 duplicates
UDP latency (100 samples)
  min/avg/median/p95/max  0.133 / 0.372 / 0.368 / 0.461 / 1.835 ms
  stdev 0.169 ms   jitter 0.088 ms   jitter(RFC 3550) 0.063 ms
```

(Loopback numbers are huge because no real network is involved. Run the server on
another machine on your LAN to see realistic figures.)

## CS concepts

| Concept | Where |
|---|---|
| **Length-prefixed binary framing** over a TCP byte stream; network byte order with `struct` | `protocol.py` |
| Why `recv` can return **partial reads**, and the `recv_exact` loop that fixes it | `protocol.recv_exact` |
| **Nagle's algorithm** and `TCP_NODELAY` for small, latency-sensitive messages | `server.py`, `client.py` |
| Application-level **RTT** measurement with a monotonic, nanosecond clock | `SpeedClient.ping` |
| **Throughput** = bits ÷ seconds; SI (Mbit/s) versus IEC (MiB) units | `stats.py` |
| Why upload timing waits for an **acknowledgement**: `sendall` only fills the kernel send buffer | `SpeedClient.upload` |
| **TCP slow start** warm-up excluded from fixed-duration tests | `SpeedClient.timed_transfer` |
| **Jitter** two ways: mean absolute delta (PDV) and the **RFC 3550** EWMA estimator | `stats.py` |
| Percentiles with linear interpolation; Bessel-corrected standard deviation | `stats.py` |
| **UDP** for loss measurement: sequence numbers detect loss, duplicates and reordering | `client.udp_probe` |
| Non-blocking sockets with `select` so packets are timestamped on arrival | `client.udp_probe` |
| Thread-per-connection server with `socketserver` mixins | `server.py` |

## Layout

```
src/netspeed/
  protocol.py  wire format + recv_exact / drain / send_bulk helpers
  server.py    SpeedServer: TCP command handler + UDP echo on one port
  client.py    SpeedClient (ping, download, upload, timed_transfer) and udp_probe
  stats.py     mean/stdev/percentile/jitter, LatencySummary, unit formatting
  cli.py       `netspeed serve | test | demo`
tests/test_netspeed.py   26 tests: pure stats, framing, and end-to-end on localhost
```

### Protocol

Every TCP request is a 9-byte header: a 1-byte command and an 8-byte big-endian
argument.

| Cmd | Argument | Server response |
|---|---|---|
| `P` ping | random nonce | echoes the same 9 bytes |
| `D` download | byte count *n* | streams *n* bytes |
| `U` upload | byte count *n* | reads *n* bytes, replies with an 8-byte count received |
| `Q` quit | (ignored) | closes the connection |

UDP datagrams carry `seq (u32) + send_time_ns (u64) + padding` and are echoed
back unchanged, so only the client's clock is used.

## Build, run, test

Requires Python 3.10+.

```bash
make test                    # python3 -m pytest (needs pytest)
make demo                    # start a server on a random loopback port and test it

# Two terminals / two machines you own:
PYTHONPATH=src python3 -m netspeed serve --host 0.0.0.0 --port 5201
PYTHONPATH=src python3 -m netspeed test --host 192.168.1.20 -t 5 -n 50

# Or install it:
pip install -e '.[dev]'
netspeed demo --json
```

Options for `test` / `demo`: `-n/--pings`, `-t/--duration` (seconds per direction),
`--udp` (number of probes), `--json`.

## Safety

This is a measurement tool for **your own machines**. The server binds to
`127.0.0.1` by default, and `netspeed test` refuses public IP addresses unless you
pass `--allow-public` to say you run that server. The server also caps a single
transfer at 4 GiB. Don't point it at hosts you don't own or aren't allowed to
test: saturating someone else's link is abuse.

## Possible extensions

- Parallel streams (like `iperf -P`) to fill high bandwidth-delay-product links.
- Report TCP internals (`TCP_INFO`: cwnd, retransmits, smoothed RTT) on Linux.
- Measure **bufferbloat**: run pings during a saturating transfer and compare
  latency under load against idle latency.
- Bidirectional simultaneous tests, and UDP throughput at a target bitrate.
- An `asyncio` server so thousands of clients can share one thread.
- Live progress bar and history saved to CSV for plotting over time.
