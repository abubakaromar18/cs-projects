"""Core pixel sorting engine.

Algorithm
---------
1. Rotate the image so the requested sort direction becomes horizontal.
2. Compute a scalar key per pixel (lightness, hue, ...).
3. Build a boolean mask of "sortable" pixels with an interval function.
4. For each row, find contiguous runs in the mask and stable-sort the
   pixels of each run by key (argsort, kind="stable").
5. Rotate back and crop away any padding introduced by the rotation.

Sorting a run is O(k log k) for run length k, so the whole image costs
O(N log L) where L is the longest run.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from PIL import Image

from .intervals import get_interval, runs
from .keys import get_key


@dataclass
class SortConfig:
    key: str = "lightness"
    interval: str = "threshold"
    angle: float = 0.0          # degrees; 0 = left->right, 90 = top->bottom
    reverse: bool = False
    lower: float = 0.25
    upper: float = 0.8
    edge_threshold: float = 0.1
    mean_length: int = 40
    seed: int | None = None
    extra: dict = field(default_factory=dict)

    def interval_kwargs(self) -> dict:
        return dict(lower=self.lower, upper=self.upper, edge_threshold=self.edge_threshold,
                    mean_length=self.mean_length, seed=self.seed, **self.extra)


def sort_array(rgb: np.ndarray, config: SortConfig | None = None, mask: np.ndarray | None = None) -> np.ndarray:
    """Sort runs within each row of an (H, W, 3) uint8 array horizontally.

    `mask` overrides the interval function when given. Returns a new array;
    the multiset of pixels in every row is preserved.
    """
    config = config or SortConfig()
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("expected an (H, W, 3) RGB array")
    key_fn = get_key(config.key)
    values = key_fn(rgb)
    if mask is None:
        mask = get_interval(config.interval)(values, **config.interval_kwargs())

    out = rgb.copy()
    for y in range(rgb.shape[0]):
        for start, end in runs(mask[y]):
            if end - start < 2:
                continue
            order = np.argsort(values[y, start:end], kind="stable")
            if config.reverse:
                order = order[::-1]
            out[y, start:end] = rgb[y, start:end][order]
    return out


def _rotate(img: Image.Image, angle: float) -> Image.Image:
    # Right angles are lossless transposes; anything else is a resampled rotation.
    a = angle % 360
    exact = {90: Image.Transpose.ROTATE_90, 180: Image.Transpose.ROTATE_180,
             270: Image.Transpose.ROTATE_270}
    if a == 0:
        return img
    if a in exact:
        return img.transpose(exact[a])
    return img.rotate(a, expand=True, resample=Image.Resampling.NEAREST)


def sort_image(img: Image.Image, config: SortConfig | None = None) -> Image.Image:
    """Pixel-sort a PIL image along `config.angle`. Alpha is preserved untouched."""
    config = config or SortConfig()
    alpha = img.getchannel("A") if img.mode == "RGBA" else None
    rgb_img = img.convert("RGB")
    w, h = rgb_img.size
    a = config.angle % 360

    rotated = _rotate(rgb_img, a)
    arr = np.asarray(rotated)
    if a not in (0, 90, 180, 270):
        # Exclude the black padding added by expand=True from sorting by
        # rotating an all-white mask the same way.
        pad = _rotate(Image.new("L", (w, h), 255), a)
        valid = np.asarray(pad) > 0
        values = get_key(config.key)(arr)
        mask = get_interval(config.interval)(values, **config.interval_kwargs()) & valid
        sorted_arr = sort_array(arr, config, mask=mask)
    else:
        sorted_arr = sort_array(arr, config)

    result = _rotate(Image.fromarray(sorted_arr), -a)
    if result.size != (w, h):
        # Crop the centre back to the original size after a non-right rotation.
        rw, rh = result.size
        left, top = (rw - w) // 2, (rh - h) // 2
        result = result.crop((left, top, left + w, top + h))
    if alpha is not None:
        result.putalpha(alpha)
    return result
