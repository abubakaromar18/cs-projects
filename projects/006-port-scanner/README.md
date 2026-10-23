# 006 · Port Scanner

An educational **TCP connect scanner** written in Python with `asyncio`. It checks which TCP ports on *your own* machine (or, with an explicit flag, your own LAN devices) are accepting connections. Use it to see what services you're exposing.

> **Safety by design.** Targets are resolved to an IP address first, then checked against a fixed policy. Loopback (`127.0.0.0/8`, `::1`) is always allowed. Private and link-local ranges need `--allow-private`. Public internet addresses are refused, and no flag overrides that. Only scan systems you own or have permission to test.

## Features

- Concurrent scanning with `asyncio`, capped by a semaphore (`-c`, default 200 in flight)
- Each port is reported as `open`, `closed`, `filtered` (timed out) or `error`
- Optional banner grab (`-b`) to read the greeting that services like SSH, SMTP and FTP send first
- Port specs such as `22,80,8000-8100`, plus the keywords `top` (common ports) and `all`
- Text table or `--json` output, with live progress on stderr (`-v`)
- Shell-friendly exit codes: `0` if any port is open, `1` if none are, `2` on a usage or policy error
- Standard library only; `pytest` is needed just for the tests

## CS concepts demonstrated

| Concept | Where |
|---|---|
| **TCP three-way handshake**: SYN → SYN/ACK = open, RST = closed, silence = filtered | `scanner.probe` |
| **Async I/O and the event loop**: hundreds of sockets in flight on one thread | `scanner.scan_async` |
| **Bounded concurrency**: a semaphore limits open file descriptors and load on the target | `asyncio.Semaphore` in `scan_async` |
| **Timeouts as a signal**: a dropped packet looks the same as a slow host | `asyncio.wait_for` |
| **DNS resolution and IP address classes**: loopback, RFC 1918 private, link-local, public | `targets.py` |
| **Policy enforced after resolution**: blocks hostnames that resolve to public IPs | `targets.make_target` |
| **Parsing a small grammar**: lists and ranges, normalized to a sorted set | `ports.parse_ports` |

## Layout

```
src/port_scanner/
  ports.py     port-spec parser + service names
  targets.py   resolution + loopback/private/public safety policy
  scanner.py   asyncio connect scan, result types
  report.py    text table / JSON rendering
  cli.py       argparse front end (`portscan`)
tests/         48 pytest tests using throwaway servers on 127.0.0.1
```

## Build, run, test

Requires Python 3.10+.

```bash
make dev                                   # pip install -e '.[dev]'
make test                                  # python -m pytest
portscan -p top                            # after install
make run ARGS="127.0.0.1 -p 1-1024 -b"     # straight from source
```

Without make: `PYTHONPATH=src python3 -m port_scanner 127.0.0.1 -p 1-1024`.

## Example

```text
$ python3 -m http.server 8765 --bind 127.0.0.1 &
$ portscan -p 8700-8800
Scan report for 127.0.0.1
 PORT      STATE     SERVICE        LATENCY
 8765/tcp  open      ?                 4.2ms
101 ports scanned in 0.51s: 1 open, 100 closed

$ portscan 1.1.1.1
portscan: error: 1.1.1.1 is not a loopback or private address; this educational scanner only targets your own machines

$ portscan 192.168.1.20 --allow-private -p 22,80,443 --json
{ "host": "192.168.1.20", "counts": {"open": 1, ...}, "results": [ ... ] }
```

### Options

| Flag | Meaning |
|---|---|
| `-p, --ports` | Port spec (default `1-1024`) |
| `-t, --timeout` | Seconds per connection attempt (default 1.0) |
| `-c, --concurrency` | Maximum simultaneous connections (default 200) |
| `-b, --banner` | Read up to 128 bytes of greeting from each open port |
| `-a, --all` | Also list closed and filtered ports |
| `--json` | Machine-readable output |
| `--allow-private` | Allow RFC 1918 and link-local targets |
| `-v, --verbose` | Stream open ports to stderr as they're found |

## Testing approach

The tests start real listening sockets on ephemeral loopback ports, some of which send a fake SSH banner, and scan them. They also grab a free port to check the `closed` result. `asyncio.open_connection` is monkeypatched to cover the timeout (`filtered`) and error paths, and to measure the peak number of connections in flight, which proves the semaphore limit holds.

## Possible extensions

- Rate limiting in packets per second, plus random port order
- UDP probing with protocol-specific payloads (DNS, NTP)
- Service fingerprinting beyond the banner, e.g. sending `HEAD / HTTP/1.0` to HTTP ports
- Diffing two JSON reports to catch newly exposed services ("what changed since yesterday?")
- An IPv6 host sweep across your own `/64` with `--allow-private`
