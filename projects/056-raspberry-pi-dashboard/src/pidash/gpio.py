"""GPIO hardware abstraction layer.

The dashboard never talks to hardware directly. It talks to a ``GPIOBackend``,
an abstract interface with two implementations:

* ``MockBackend`` - a pure-Python simulation of a pin header. It lets the whole
  app (and its test suite) run on any laptop or CI machine.
* ``RPiBackend`` - a thin adapter over the ``RPi.GPIO`` library, imported lazily
  so the package still installs and imports on non-Pi machines.

Pins are always identified by their BCM (Broadcom SoC channel) number, which is
what ``RPi.GPIO`` calls ``GPIO.BCM`` mode and what most pinout diagrams label
as ``GPIOxx``.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from enum import Enum

# BCM channels exposed on the 40-pin header of every modern Pi (B+, 2, 3, 4, 5, Zero).
VALID_BCM_PINS: frozenset[int] = frozenset(range(2, 28))


class PinMode(str, Enum):
    INPUT = "input"
    OUTPUT = "output"
    PWM = "pwm"


class GPIOError(Exception):
    """Raised for invalid pin numbers, wrong modes, or out-of-range values."""


def validate_pin(pin: int) -> None:
    if pin not in VALID_BCM_PINS:
        raise GPIOError(f"GPIO{pin} is not a usable BCM pin (valid: 2-27)")


def validate_duty(duty: float) -> float:
    try:
        duty = float(duty)
    except (TypeError, ValueError) as exc:
        raise GPIOError("duty cycle must be a number") from exc
    if not 0.0 <= duty <= 100.0:
        raise GPIOError("duty cycle must be between 0 and 100")
    return duty


class GPIOBackend(ABC):
    """Interface every hardware backend implements."""

    name: str = "abstract"

    @abstractmethod
    def setup(self, pin: int, mode: PinMode, pull_up: bool = False) -> None: ...

    @abstractmethod
    def write(self, pin: int, value: bool) -> None: ...

    @abstractmethod
    def read(self, pin: int) -> bool: ...

    @abstractmethod
    def set_duty(self, pin: int, duty: float) -> None: ...

    @abstractmethod
    def get_duty(self, pin: int) -> float: ...

    def cleanup(self) -> None:  # optional hook
        pass


class MockBackend(GPIOBackend):
    """In-memory pin simulation.

    Output pins remember the value written to them. Input pins read whatever was
    last injected with :meth:`simulate_input` (default: the pull resistor's
    resting level - high with a pull-up, low otherwise), mimicking a button.
    """

    name = "mock"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._modes: dict[int, PinMode] = {}
        self._levels: dict[int, bool] = {}
        self._duty: dict[int, float] = {}

    def setup(self, pin: int, mode: PinMode, pull_up: bool = False) -> None:
        validate_pin(pin)
        with self._lock:
            self._modes[pin] = mode
            self._levels[pin] = pull_up if mode is PinMode.INPUT else False
            if mode is PinMode.PWM:
                self._duty[pin] = 0.0

    def _require(self, pin: int, *modes: PinMode) -> None:
        mode = self._modes.get(pin)
        if mode is None:
            raise GPIOError(f"GPIO{pin} has not been set up")
        if mode not in modes:
            raise GPIOError(f"GPIO{pin} is in {mode.value} mode")

    def write(self, pin: int, value: bool) -> None:
        with self._lock:
            self._require(pin, PinMode.OUTPUT)
            self._levels[pin] = bool(value)

    def read(self, pin: int) -> bool:
        with self._lock:
            self._require(pin, *PinMode)
            if self._modes[pin] is PinMode.PWM:
                return self._duty[pin] > 0
            return self._levels[pin]

    def set_duty(self, pin: int, duty: float) -> None:
        duty = validate_duty(duty)
        with self._lock:
            self._require(pin, PinMode.PWM)
            self._duty[pin] = duty

    # --- test / demo helpers -------------------------------------------------
    def simulate_input(self, pin: int, level: bool) -> None:
        """Pretend an external circuit drove an input pin high or low."""
        with self._lock:
            self._require(pin, PinMode.INPUT)
            self._levels[pin] = bool(level)

    def get_duty(self, pin: int) -> float:
        with self._lock:
            return self._duty.get(pin, 0.0)


class RPiBackend(GPIOBackend):  # pragma: no cover - needs real hardware
    """Adapter over the RPi.GPIO C extension. Only works on a Raspberry Pi."""

    name = "rpi"
    PWM_FREQUENCY_HZ = 1000

    def __init__(self) -> None:
        try:
            import RPi.GPIO as GPIO  # type: ignore[import-not-found]
        except ImportError as exc:
            raise GPIOError(
                "RPi.GPIO is not available - install it on the Pi "
                "(pip install RPi.GPIO) or run with --backend mock"
            ) from exc
        self._gpio = GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        self._pwm: dict[int, object] = {}
        self._duty: dict[int, float] = {}

    def setup(self, pin: int, mode: PinMode, pull_up: bool = False) -> None:
        validate_pin(pin)
        G = self._gpio
        if mode is PinMode.INPUT:
            G.setup(pin, G.IN, pull_up_down=G.PUD_UP if pull_up else G.PUD_DOWN)
        else:
            G.setup(pin, G.OUT, initial=G.LOW)
            if mode is PinMode.PWM:
                pwm = G.PWM(pin, self.PWM_FREQUENCY_HZ)
                pwm.start(0)
                self._pwm[pin] = pwm
                self._duty[pin] = 0.0

    def write(self, pin: int, value: bool) -> None:
        self._gpio.output(pin, self._gpio.HIGH if value else self._gpio.LOW)

    def read(self, pin: int) -> bool:
        if pin in self._pwm:
            return self._duty[pin] > 0
        return bool(self._gpio.input(pin))

    def set_duty(self, pin: int, duty: float) -> None:
        duty = validate_duty(duty)
        if pin not in self._pwm:
            raise GPIOError(f"GPIO{pin} is not in pwm mode")
        self._pwm[pin].ChangeDutyCycle(duty)  # type: ignore[attr-defined]
        self._duty[pin] = duty

    def get_duty(self, pin: int) -> float:
        return self._duty.get(pin, 0.0)

    def cleanup(self) -> None:
        for pwm in self._pwm.values():
            pwm.stop()  # type: ignore[attr-defined]
        self._gpio.cleanup()


def make_backend(name: str) -> GPIOBackend:
    """Factory used by the CLI: ``mock`` or ``rpi``."""
    if name == "mock":
        return MockBackend()
    if name == "rpi":
        return RPiBackend()
    raise GPIOError(f"unknown backend {name!r} (choose 'mock' or 'rpi')")
