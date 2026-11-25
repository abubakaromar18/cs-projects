"""Sort keys: functions mapping an (..., 3) uint8 RGB array to a float score.

Every key returns values normalised to [0, 1] so that interval thresholds
mean the same thing regardless of which key is used.
"""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np

KeyFn = Callable[[np.ndarray], np.ndarray]


def _f(rgb: np.ndarray) -> np.ndarray:
    return rgb.astype(np.float64) / 255.0


def lightness(rgb: np.ndarray) -> np.ndarray:
    """HSL lightness: (max + min) / 2."""
    c = _f(rgb)
    return (c.max(axis=-1) + c.min(axis=-1)) / 2.0


def luminance(rgb: np.ndarray) -> np.ndarray:
    """Perceptual luma (Rec. 709 weights) — how bright a pixel *looks*."""
    c = _f(rgb)
    return c @ np.array([0.2126, 0.7152, 0.0722])


def hue(rgb: np.ndarray) -> np.ndarray:
    """HSV hue in [0, 1); grey pixels get hue 0."""
    c = _f(rgb)
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    mx, mn = c.max(axis=-1), c.min(axis=-1)
    delta = mx - mn
    safe = np.where(delta == 0, 1.0, delta)
    # Piecewise hue formula depending on which channel is the maximum.
    # Evaluated blue -> green -> red so that on ties red takes priority,
    # matching colorsys.rgb_to_hsv.
    h = (r - g) / safe + 4
    h = np.where(mx == g, (b - r) / safe + 2, h)
    h = np.where(mx == r, ((g - b) / safe) % 6, h)
    h = np.where(delta == 0, 0.0, h)
    return (h / 6.0) % 1.0


def saturation(rgb: np.ndarray) -> np.ndarray:
    """HSV saturation: (max - min) / max."""
    c = _f(rgb)
    mx, mn = c.max(axis=-1), c.min(axis=-1)
    return np.where(mx == 0, 0.0, (mx - mn) / np.where(mx == 0, 1.0, mx))


def red(rgb: np.ndarray) -> np.ndarray:
    return _f(rgb)[..., 0]


def green(rgb: np.ndarray) -> np.ndarray:
    return _f(rgb)[..., 1]


def blue(rgb: np.ndarray) -> np.ndarray:
    return _f(rgb)[..., 2]


KEYS: Dict[str, KeyFn] = {
    "lightness": lightness,
    "luminance": luminance,
    "hue": hue,
    "saturation": saturation,
    "red": red,
    "green": green,
    "blue": blue,
}


def get_key(name: str) -> KeyFn:
    try:
        return KEYS[name]
    except KeyError:
        raise ValueError(f"unknown sort key {name!r}; choose from {sorted(KEYS)}") from None
