import colorsys

import numpy as np
import pytest

from pixelsort.keys import KEYS, get_key, hue, lightness, luminance, saturation


def test_all_keys_in_unit_range():
    rng = np.random.default_rng(1)
    rgb = rng.integers(0, 256, size=(20, 20, 3), dtype=np.uint8)
    for name, fn in KEYS.items():
        v = fn(rgb)
        assert v.shape == (20, 20), name
        assert v.min() >= 0 and v.max() <= 1, name


def test_hue_and_saturation_match_colorsys():
    rng = np.random.default_rng(2)
    rgb = rng.integers(0, 256, size=(200, 3), dtype=np.uint8)
    rgb = np.vstack([rgb, [[255, 255, 0], [0, 255, 255], [255, 0, 255], [10, 10, 10]]]).astype(np.uint8)
    h, s = hue(rgb), saturation(rgb)
    for i, (r, g, b) in enumerate(rgb / 255.0):
        eh, es, _ = colorsys.rgb_to_hsv(r, g, b)
        assert h[i] == pytest.approx(eh, abs=1e-9)
        assert s[i] == pytest.approx(es, abs=1e-9)


def test_lightness_and_luminance_extremes():
    rgb = np.array([[0, 0, 0], [255, 255, 255]], dtype=np.uint8)
    assert lightness(rgb).tolist() == [0, 1]
    assert luminance(rgb) == pytest.approx([0, 1])


def test_unknown_key():
    with pytest.raises(ValueError):
        get_key("nope")
