"""UI-independent application state (a tiny observable model).

The Tkinter view subscribes to changes; tests drive the model directly.
This is the Observer pattern: one source of truth, many listeners, so the
sliders, hex box, swatch and format list can never disagree.
"""
from __future__ import annotations

from typing import Callable

from .colors import RGB, parse_color
from .history import History

Listener = Callable[[RGB], None]


class PickerModel:
    def __init__(self, initial: RGB = RGB(255, 136, 0), history: History | None = None) -> None:
        self._color = initial
        self.history = history if history is not None else History()
        self._listeners: list[Listener] = []

    @property
    def color(self) -> RGB:
        return self._color

    def subscribe(self, fn: Listener) -> Callable[[], None]:
        """Register *fn*; returns an unsubscribe function."""
        self._listeners.append(fn)
        fn(self._color)
        return lambda: self._listeners.remove(fn)

    def set_color(self, c: RGB, *, remember: bool = False) -> None:
        changed = c != self._color
        self._color = c
        if remember:
            self.history.add(c)
        if changed or remember:
            for fn in list(self._listeners):
                fn(c)

    def set_text(self, text: str) -> bool:
        """Set from user-typed text. Returns False (state unchanged) on bad input."""
        try:
            c = parse_color(text)
        except ValueError:
            return False
        self.set_color(c, remember=True)
        return True

    def set_channel(self, channel: str, value: int) -> None:
        r, g, b = self._color.as_tuple()
        vals = {"r": r, "g": g, "b": b}
        if channel not in vals:
            raise KeyError(channel)
        vals[channel] = max(0, min(255, int(value)))
        self.set_color(RGB(vals["r"], vals["g"], vals["b"]))
