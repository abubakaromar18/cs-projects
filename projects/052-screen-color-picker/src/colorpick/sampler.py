"""Reading pixels off the screen.

Tkinter itself cannot read arbitrary screen pixels, so screen capture is
delegated to Pillow's ``ImageGrab`` (Windows, macOS, and X11 Linux).  The
sampling math is written against a tiny ``PixelSource`` protocol so it can
be tested with a fake image and no display.
"""
from __future__ import annotations

from typing import Callable, Protocol

from .colors import RGB


class PixelSource(Protocol):
    """Anything with a ``size`` and a ``getpixel((x, y))`` — e.g. a PIL Image."""

    size: tuple[int, int]

    def getpixel(self, xy: tuple[int, int]): ...


class CaptureUnavailable(RuntimeError):
    """Raised when no screen-capture backend works on this system."""


def _to_rgb(px) -> RGB:
    # PIL returns ints for 'L' images and 3/4-tuples for RGB(A).
    if isinstance(px, int):
        return RGB(px, px, px)
    return RGB(int(px[0]), int(px[1]), int(px[2]))


def sample(src: PixelSource, x: int, y: int, radius: int = 0) -> RGB:
    """Average the (2r+1)² block centred on (x, y), clipped to the image.

    ``radius=0`` reads a single pixel; a small radius smooths out
    anti-aliasing and dithering, which is what most designers want.
    """
    w, h = src.size
    if not (0 <= x < w and 0 <= y < h):
        raise ValueError(f"point ({x}, {y}) outside {w}x{h} image")
    if radius < 0:
        raise ValueError("radius must be >= 0")
    tr = tg = tb = n = 0
    for yy in range(max(0, y - radius), min(h, y + radius + 1)):
        for xx in range(max(0, x - radius), min(w, x + radius + 1)):
            c = _to_rgb(src.getpixel((xx, yy)))
            tr, tg, tb, n = tr + c.r, tg + c.g, tb + c.b, n + 1
    return RGB(round(tr / n), round(tg / n), round(tb / n))


def magnify(src: PixelSource, x: int, y: int, half: int = 5) -> list[list[RGB | None]]:
    """Return a (2·half+1)² grid of pixels around (x, y) for the loupe.

    Pixels outside the image are ``None`` so the UI can draw them as empty.
    """
    w, h = src.size
    grid: list[list[RGB | None]] = []
    for yy in range(y - half, y + half + 1):
        row: list[RGB | None] = []
        for xx in range(x - half, x + half + 1):
            row.append(_to_rgb(src.getpixel((xx, yy))) if 0 <= xx < w and 0 <= yy < h else None)
        grid.append(row)
    return grid


def default_grabber() -> Callable[[], PixelSource]:
    """Return a zero-arg function that captures the whole screen.

    Imported lazily so the rest of the app (and the tests) work without
    Pillow installed.
    """
    try:
        from PIL import ImageGrab  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise CaptureUnavailable("Install Pillow to pick colors from the screen: pip install pillow") from exc

    def grab() -> PixelSource:
        try:
            return ImageGrab.grab(all_screens=True).convert("RGB")
        except Exception as exc:  # pragma: no cover - platform specific
            raise CaptureUnavailable(f"screen capture failed: {exc}") from exc

    return grab
