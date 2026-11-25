"""Procedural source images so the tool can demo itself with no input files."""

from __future__ import annotations

import numpy as np
from PIL import Image


def plasma(width: int = 480, height: int = 320, seed: int = 0) -> Image.Image:
    """Sum-of-sines 'plasma' — smooth colour fields with lots of hue variety."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:height, 0:width].astype(np.float64)
    f = rng.uniform(0.01, 0.04, size=4)
    p = rng.uniform(0, 2 * np.pi, size=4)
    v = (np.sin(x * f[0] + p[0]) + np.sin(y * f[1] + p[1])
         + np.sin((x + y) * f[2] + p[2]) + np.sin(np.hypot(x - width / 2, y - height / 2) * f[3] + p[3]))
    v = (v + 4) / 8  # -> [0, 1]
    rgb = np.stack([np.sin(2 * np.pi * v), np.sin(2 * np.pi * v + 2.1), np.sin(2 * np.pi * v + 4.2)], -1)
    return Image.fromarray(((rgb + 1) * 127.5).astype(np.uint8))


def stripes(width: int = 480, height: int = 320, seed: int = 0) -> Image.Image:
    """Random coloured horizontal bands with noise — shows thresholds clearly."""
    rng = np.random.default_rng(seed)
    bands = rng.integers(0, 256, size=(height // 16 + 1, 3))
    arr = np.repeat(bands, 16, axis=0)[:height, None, :].repeat(width, axis=1).astype(np.int16)
    arr += rng.integers(-60, 60, size=arr.shape)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


GENERATORS = {"plasma": plasma, "stripes": stripes}
