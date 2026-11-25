import numpy as np
import pytest
from PIL import Image

from pixelsort import SortConfig, sort_array, sort_image
from pixelsort.cli import main
from pixelsort.generate import plasma, stripes
from pixelsort.keys import lightness


def _row_multisets_equal(a, b):
    for ra, rb in zip(a, b):
        assert sorted(map(tuple, ra)) == sorted(map(tuple, rb))


def test_full_sort_is_monotonic_and_preserves_pixels():
    rng = np.random.default_rng(0)
    rgb = rng.integers(0, 256, size=(10, 30, 3), dtype=np.uint8)
    out = sort_array(rgb, SortConfig(interval="full"))
    vals = lightness(out)
    assert (np.diff(vals, axis=1) >= 0).all()
    _row_multisets_equal(rgb, out)


def test_reverse_sorts_descending():
    rng = np.random.default_rng(0)
    rgb = rng.integers(0, 256, size=(5, 30, 3), dtype=np.uint8)
    out = sort_array(rgb, SortConfig(interval="full", reverse=True, key="red"))
    assert (np.diff(out[..., 0].astype(int), axis=1) <= 0).all()


def test_threshold_leaves_out_of_range_pixels_in_place():
    rgb = np.array([[[250] * 3, [100] * 3, [50] * 3, [5] * 3, [200] * 3, [150] * 3]], dtype=np.uint8)
    out = sort_array(rgb, SortConfig(interval="threshold", lower=0.1, upper=0.9))
    # 250 and 5 are outside [0.1, 0.9]; they stay put and act as boundaries.
    assert out[0, :, 0].tolist() == [250, 50, 100, 5, 150, 200]


def test_vertical_sort_sorts_columns():
    img = stripes(40, 60, seed=1)
    out = np.asarray(sort_image(img, SortConfig(interval="full", angle=90)))
    vals = lightness(out)
    # angle=90 means "top -> bottom": every column ascends downwards.
    assert (np.diff(vals, axis=0) >= 0).all()
    _row_multisets_equal(np.asarray(img).transpose(1, 0, 2), out.transpose(1, 0, 2))


def test_arbitrary_angle_keeps_size_and_alpha():
    img = plasma(64, 48).convert("RGBA")
    img.putalpha(128)
    out = sort_image(img, SortConfig(interval="threshold", angle=30))
    assert out.size == img.size and out.mode == "RGBA"
    assert np.asarray(out.getchannel("A")).min() == 128


def test_sort_array_rejects_bad_shape():
    with pytest.raises(ValueError):
        sort_array(np.zeros((4, 4), np.uint8))


def test_cli_demo(tmp_path, capsys):
    out = tmp_path / "o.png"
    src = tmp_path / "s.png"
    assert main(["--demo", "plasma", "-o", str(out), "--save-source", str(src), "-k", "hue", "--seed", "4"]) == 0
    assert Image.open(out).size == Image.open(src).size
    assert "wrote" in capsys.readouterr().out


def test_cli_file_input_and_bad_threshold(tmp_path):
    src = tmp_path / "in.png"
    stripes(32, 32).save(src)
    assert main([str(src), "-o", str(tmp_path / "o.png"), "-i", "edges"]) == 0
    assert main([str(src), "-o", str(tmp_path / "o2.png"), "--lower", "0.9", "--upper", "0.1"]) == 2
