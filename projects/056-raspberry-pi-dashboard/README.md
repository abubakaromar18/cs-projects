# 056 · Raspberry Pi Dashboard

A small web dashboard for controlling a Raspberry Pi's GPIO pins from a browser. You can switch LEDs and relays, dim a PWM output with a slider, watch input pins such as buttons, and see the Pi's CPU temperature, load, memory and uptime. It uses only the Python standard library. A **mock backend** simulates the pin header, so you can develop and test on any laptop and then run the same code on a real Pi with `--backend rpi`.

```
┌──────────────┐  fetch() JSON  ┌──────────────────┐   ┌────────┐   ┌──────────────────────┐
│ index.html   │ ─────────────▶ │ server.py        │──▶│ Board  │──▶│ GPIOBackend          │
│ (vanilla JS) │ ◀───────────── │ ThreadingHTTPSrv │   │ names, │   │  ├─ MockBackend (sim) │
└──────────────┘  poll every 2s └──────────────────┘   │ rules, │   │  └─ RPiBackend       │
                                        │              │ history│   │      (RPi.GPIO)      │
                                        ▼              └────────┘   └──────────────────────┘
                                   system.py → /sys, /proc (CPU temp, uptime, memory)
```

## Key CS concepts

- **Hardware abstraction layer.** `GPIOBackend` is an abstract base class. The rest of the app depends on this interface and never on `RPi.GPIO` directly (dependency inversion). Swapping the simulation for real hardware is a single factory call.
- **Lazy, optional imports.** `RPi.GPIO` is imported only when the `rpi` backend is created, so the package installs and its tests run anywhere.
- **Pin modes as a state machine.** Each pin is set up once as `input`, `output` or `pwm`, and every operation checks that mode. For example, you can't drive an input pin high.
- **PWM (pulse-width modulation).** A digital pin "dims" an LED by switching on and off quickly. The duty cycle (0–100 %) is the share of time it spends on.
- **Pull-up resistors.** An input configured with `pull_up` rests at HIGH and drops to LOW when a button connects it to ground. The mock models this.
- **Concurrency.** `ThreadingHTTPServer` handles each request on its own thread. Board and backend state are guarded with locks so that two toggles can't race each other.
- **Ring buffer.** The activity log is a `collections.deque(maxlen=N)`, so it keeps only the latest N events in constant memory.
- **REST-ish JSON API with a closure-bound handler.** `make_handler()` returns a handler class that captures the board. This avoids globals and lets each test run an isolated server on port 0.
- **Linux pseudo-filesystems.** Vitals come from `/sys/class/thermal` (millidegrees Celsius) and `/proc/uptime` and `/proc/meminfo`.
- **Defensive web security for a device that switches real things:**
  - The server binds to `127.0.0.1` by default.
  - An optional bearer token is checked with `hmac.compare_digest`, a constant-time comparison.
  - State changes are accepted only as `POST` with `application/json`, so a stray `<img src>` or a cross-site form can't flip a relay.
  - Request bodies are capped in size, and responses send `nosniff` and `no-store` headers.

## Project layout

```
src/pidash/
  gpio.py      backend interface, MockBackend, RPiBackend, validation
  board.py     PinConfig, Board (named pins, rules, event history)
  system.py    CPU temp / uptime / memory / load readers
  server.py    HTTP routes, auth, JSON handling
  cli.py       argument parsing, startup
  static/      index.html dashboard + demo-pins.json
examples/pins.json   sample wiring config
tests/               unit + end-to-end HTTP tests (pytest)
```

## Build, run and test

You need Python 3.10 or newer. There are no runtime dependencies.

```bash
make test             # or: python3 -m pytest   (needs pytest)
make run              # simulated pins on http://127.0.0.1:8080/
```

To install it as a command:

```bash
pip install -e '.[dev]'
pidash --config examples/pins.json --port 8080
```

### On a real Raspberry Pi

```bash
pip install -e '.[pi]'                        # installs RPi.GPIO
export PIDASH_TOKEN="$(python3 -c 'import secrets;print(secrets.token_urlsafe(24))')"
pidash --backend rpi --config examples/pins.json --host 0.0.0.0
```

Enter the same token in the dashboard's **Token** box, which saves it in that browser. Keep the server on your own LAN. Don't port-forward it to the internet. For remote access, use a VPN such as WireGuard or Tailscale.

The tests run only against the mock backend. `RPiBackend` is a thin adapter that needs a physical Pi, so it isn't exercised in CI.

### Pin config

Pins are numbered in BCM mode (the `GPIOxx` labels), and the valid range is 2–27.

```json
{
  "pins": [
    {"pin": 17, "name": "Status LED", "mode": "output"},
    {"pin": 18, "name": "Dimmable LED", "mode": "pwm"},
    {"pin": 22, "name": "Door button", "mode": "input", "pull_up": true}
  ]
}
```

## Example usage

```console
$ make run
pidash [mock] serving 4 pins on http://127.0.0.1:8080/

$ curl -s localhost:8080/api/pins
[{"pin": 17, "name": "Status LED", "mode": "output", "value": false},
 {"pin": 18, "name": "Dimmable LED", "mode": "pwm", "value": false, "duty": 0.0},
 {"pin": 22, "name": "Door button", "mode": "input", "value": true},
 {"pin": 27, "name": "Relay: Fan", "mode": "output", "value": false}]

$ curl -s -X POST -H 'Content-Type: application/json' -d '{}' localhost:8080/api/pins/17/toggle
{"pin": 17, "name": "Status LED", "mode": "output", "value": true}

$ curl -s -X POST -H 'Content-Type: application/json' -d '{"duty": 60}' localhost:8080/api/pins/18
{"pin": 18, "name": "Dimmable LED", "mode": "pwm", "value": true, "duty": 60.0}

$ curl -s -X POST -H 'Content-Type: application/json' -d '{"value": true}' localhost:8080/api/pins/22
{"error": "Door button is an input pin; it cannot be set"}
```

| Endpoint | Method | Body |
|---|---|---|
| `/api/pins` | GET | – |
| `/api/pins/<n>` | GET / POST | `{"value": bool}` or `{"duty": 0-100}` |
| `/api/pins/<n>/toggle` | POST | `{}` |
| `/api/system` | GET | – |
| `/api/history` | GET | – |

## Possible extensions

- Push updates with Server-Sent Events instead of polling every 2 seconds.
- Use edge-triggered input callbacks (`GPIO.add_event_detect`) to log button presses as they happen.
- Add schedules, such as "fan on at 18:00", using a small scheduler thread.
- Read I²C/SPI sensors (BME280 temperature and humidity, for example) and draw history charts.
- Add a `gpiozero` or `lgpio` backend for the Raspberry Pi 5.
- Add per-user tokens and HTTPS with a self-signed certificate.
- Add a systemd unit file so the dashboard starts at boot.
