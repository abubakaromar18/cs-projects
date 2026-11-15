import json

import pytest

from colorpick.colors import RGB
from colorpick.history import History
from colorpick.model import PickerModel
from colorpick.sampler import magnify, sample


class FakeImage:
    """A 4x3 test image: pixel value encodes its coordinates."""

    def __init__(self, w=4, h=3):
        self.size = (w, h)

    def getpixel(self, xy):
        x, y = xy
        return (x * 10, y * 10, 200, 255)  # RGBA, alpha ignored


def test_sample_single_pixel():
    assert sample(FakeImage(), 2, 1) == RGB(20, 10, 200)


def test_sample_average_is_clipped_at_edges():
    # 3x3 around (0,0) clips to the 2x2 block {0,1}x{0,1}.
    assert sample(FakeImage(), 0, 0, radius=1) == RGB(5, 5, 200)
    # Interior 3x3 around (2,1): x in 1..3, y in 0..2 → mean x*10 = 20, mean y*10 = 10
    assert sample(FakeImage(), 2, 1, radius=1) == RGB(20, 10, 200)


def test_sample_grayscale_int_pixels():
    class Gray:
        size = (1, 1)

        def getpixel(self, xy):
            return 77

    assert sample(Gray(), 0, 0) == RGB(77, 77, 77)


def test_sample_out_of_bounds():
    with pytest.raises(ValueError):
        sample(FakeImage(), 4, 0)
    with pytest.raises(ValueError):
        sample(FakeImage(), 0, 0, radius=-1)


def test_magnify_grid():
    g = magnify(FakeImage(), 0, 0, half=1)
    assert len(g) == 3 and all(len(r) == 3 for r in g)
    assert g[0] == [None, None, None]          # row y=-1 is off-image
    assert g[1][0] is None                     # column x=-1 is off-image
    assert g[1][1] == RGB(0, 0, 200)           # centre
    assert g[2][2] == RGB(10, 10, 200)


def test_history_mru_and_capacity():
    h = History(capacity=3)
    for c in [RGB(1, 1, 1), RGB(2, 2, 2), RGB(3, 3, 3)]:
        h.add(c)
    h.add(RGB(1, 1, 1))  # moves to front, no duplicate
    assert list(h) == [RGB(1, 1, 1), RGB(3, 3, 3), RGB(2, 2, 2)]
    h.add(RGB(4, 4, 4))  # evicts least recent
    assert list(h) == [RGB(4, 4, 4), RGB(1, 1, 1), RGB(3, 3, 3)]
    with pytest.raises(ValueError):
        History(capacity=0)


def test_history_persistence(tmp_path):
    p = tmp_path / "sub" / "hist.json"
    h = History(path=p)
    h.add(RGB(1, 2, 3))
    h.add(RGB(255, 0, 0))
    h.save()
    assert json.loads(p.read_text()) == ["#ff0000", "#010203"]
    h2 = History(path=p)
    h2.load()
    assert list(h2) == list(h)


def test_history_load_tolerates_garbage(tmp_path):
    p = tmp_path / "h.json"
    p.write_text("{not json")
    h = History(path=p)
    h.add(RGB(9, 9, 9))
    h.load()
    assert list(h) == [RGB(9, 9, 9)]  # unchanged


def test_model_notifies_and_records():
    m = PickerModel(RGB(0, 0, 0))
    seen = []
    unsub = m.subscribe(seen.append)
    assert seen == [RGB(0, 0, 0)]            # immediate callback on subscribe
    m.set_channel("g", 300)                  # clamped
    assert m.color == RGB(0, 255, 0)
    assert m.set_text("not a color") is False
    assert m.color == RGB(0, 255, 0)
    assert m.set_text("#123456") is True
    assert m.history[0] == RGB(0x12, 0x34, 0x56)
    m.set_color(RGB(0x12, 0x34, 0x56))       # no change → no notification
    assert len(seen) == 3
    unsub()
    m.set_color(RGB(1, 1, 1))
    assert len(seen) == 3
    with pytest.raises(KeyError):
        m.set_channel("a", 1)
