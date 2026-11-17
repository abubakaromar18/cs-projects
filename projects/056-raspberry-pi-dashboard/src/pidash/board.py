"""The Board: named pins, current state, and an audit log of every change.

A ``Board`` sits between the web layer and the GPIO backend. It owns the pin
configuration (loaded from JSON), turns friendly names like "Porch light" into
BCM numbers, enforces per-pin rules, and records an event history the dashboard
displays. Keeping this logic here means the HTTP handler stays a thin router
and everything interesting is testable without sockets.
"""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .gpio import GPIOBackend, GPIOError, PinMode, validate_pin


@dataclass
class PinConfig:
    pin: int
    name: str
    mode: PinMode
    pull_up: bool = False

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PinConfig":
        try:
            pin = int(raw["pin"])
            mode = PinMode(raw.get("mode", "output"))
        except (KeyError, ValueError, TypeError) as exc:
            raise GPIOError(f"bad pin entry {raw!r}: {exc}") from exc
        validate_pin(pin)
        return cls(
            pin=pin,
            name=str(raw.get("name") or f"GPIO{pin}"),
            mode=mode,
            pull_up=bool(raw.get("pull_up", False)),
        )


@dataclass
class Event:
    timestamp: float
    pin: int
    name: str
    action: str
    value: Any


@dataclass
class Board:
    backend: GPIOBackend
    pins: dict[int, PinConfig] = field(default_factory=dict)
    history_size: int = 50

    def __post_init__(self) -> None:
        self._lock = threading.RLock()
        self._history: deque[Event] = deque(maxlen=self.history_size)

    # --- construction --------------------------------------------------------
    @classmethod
    def from_configs(
        cls, backend: GPIOBackend, configs: Iterable[PinConfig], history_size: int = 50
    ) -> "Board":
        board = cls(backend=backend, history_size=history_size)
        for cfg in configs:
            board.add_pin(cfg)
        return board

    @classmethod
    def from_json_file(cls, backend: GPIOBackend, path: str | Path) -> "Board":
        data = json.loads(Path(path).read_text())
        entries = data["pins"] if isinstance(data, dict) else data
        return cls.from_configs(backend, (PinConfig.from_dict(e) for e in entries))

    def add_pin(self, cfg: PinConfig) -> None:
        with self._lock:
            if cfg.pin in self.pins:
                raise GPIOError(f"GPIO{cfg.pin} configured twice")
            self.backend.setup(cfg.pin, cfg.mode, cfg.pull_up)
            self.pins[cfg.pin] = cfg

    # --- operations ----------------------------------------------------------
    def _get(self, pin: int) -> PinConfig:
        cfg = self.pins.get(pin)
        if cfg is None:
            raise KeyError(pin)
        return cfg

    def _log(self, cfg: PinConfig, action: str, value: Any) -> None:
        self._history.append(Event(time.time(), cfg.pin, cfg.name, action, value))

    def set(self, pin: int, value: bool) -> dict[str, Any]:
        with self._lock:
            cfg = self._get(pin)
            if cfg.mode is not PinMode.OUTPUT:
                raise GPIOError(f"{cfg.name} is an {cfg.mode.value} pin; it cannot be set")
            self.backend.write(pin, bool(value))
            self._log(cfg, "set", bool(value))
            return self.pin_state(pin)

    def toggle(self, pin: int) -> dict[str, Any]:
        with self._lock:
            current = self.backend.read(self._get(pin).pin)
            return self.set(pin, not current)

    def set_duty(self, pin: int, duty: float) -> dict[str, Any]:
        with self._lock:
            cfg = self._get(pin)
            self.backend.set_duty(pin, duty)
            self._log(cfg, "duty", float(duty))
            return self.pin_state(pin)

    # --- views ---------------------------------------------------------------
    def pin_state(self, pin: int) -> dict[str, Any]:
        cfg = self._get(pin)
        state: dict[str, Any] = {
            "pin": cfg.pin,
            "name": cfg.name,
            "mode": cfg.mode.value,
            "value": self.backend.read(pin),
        }
        if cfg.mode is PinMode.PWM:
            state["duty"] = self.backend.get_duty(pin)
        return state

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self.pin_state(p) for p in sorted(self.pins)]

    def history(self) -> list[dict[str, Any]]:
        with self._lock:
            return [asdict(e) for e in reversed(self._history)]  # newest first
