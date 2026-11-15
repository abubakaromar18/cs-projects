"""Pure color-space math: no Tkinter, no I/O, fully unit-testable.

All conversions go through an immutable :class:`RGB` value (0-255 per
channel).  Floating-point spaces (HSV, HSL, CMYK) use the conventional
ranges: hue in degrees [0, 360), everything else in [0, 1].
"""
from __future__ import annotations

import colorsys
import math
import re
from dataclasses import dataclass

__all__ = [
    "RGB",
    "parse_color",
    "contrast_ratio",
    "relative_luminance",
    "nearest_named",
    "harmonies",
    "NAMED_COLORS",
]


def _clamp_byte(v: float) -> int:
    """Round and clamp a number into 0..255."""
    return max(0, min(255, int(round(v))))


@dataclass(frozen=True, slots=True)
class RGB:
    """An sRGB color with 8-bit channels."""

    r: int
    g: int
    b: int

    def __post_init__(self) -> None:
        for name in ("r", "g", "b"):
            v = getattr(self, name)
            if not isinstance(v, int) or not 0 <= v <= 255:
                raise ValueError(f"channel {name}={v!r} must be an int in 0..255")

    # ---------- constructors ----------
    @classmethod
    def from_hex(cls, text: str) -> "RGB":
        """Parse ``#rgb``, ``#rrggbb`` (leading ``#`` optional)."""
        s = text.strip().lstrip("#")
        if not re.fullmatch(r"[0-9a-fA-F]{3}|[0-9a-fA-F]{6}", s):
            raise ValueError(f"invalid hex color: {text!r}")
        if len(s) == 3:
            s = "".join(c * 2 for c in s)
        return cls(int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))

    @classmethod
    def from_hsv(cls, h: float, s: float, v: float) -> "RGB":
        r, g, b = colorsys.hsv_to_rgb((h % 360) / 360, s, v)
        return cls(_clamp_byte(r * 255), _clamp_byte(g * 255), _clamp_byte(b * 255))

    @classmethod
    def from_hsl(cls, h: float, s: float, l: float) -> "RGB":
        # colorsys uses HLS ordering.
        r, g, b = colorsys.hls_to_rgb((h % 360) / 360, l, s)
        return cls(_clamp_byte(r * 255), _clamp_byte(g * 255), _clamp_byte(b * 255))

    @classmethod
    def from_cmyk(cls, c: float, m: float, y: float, k: float) -> "RGB":
        return cls(
            _clamp_byte(255 * (1 - c) * (1 - k)),
            _clamp_byte(255 * (1 - m) * (1 - k)),
            _clamp_byte(255 * (1 - y) * (1 - k)),
        )

    # ---------- conversions ----------
    @property
    def hex(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    def as_tuple(self) -> tuple[int, int, int]:
        return (self.r, self.g, self.b)

    def _unit(self) -> tuple[float, float, float]:
        return (self.r / 255, self.g / 255, self.b / 255)

    def to_hsv(self) -> tuple[float, float, float]:
        h, s, v = colorsys.rgb_to_hsv(*self._unit())
        return (h * 360, s, v)

    def to_hsl(self) -> tuple[float, float, float]:
        h, l, s = colorsys.rgb_to_hls(*self._unit())
        return (h * 360, s, l)

    def to_cmyk(self) -> tuple[float, float, float, float]:
        r, g, b = self._unit()
        k = 1 - max(r, g, b)
        if k >= 1.0:  # pure black: C/M/Y are undefined, use 0 by convention
            return (0.0, 0.0, 0.0, 1.0)
        return ((1 - r - k) / (1 - k), (1 - g - k) / (1 - k), (1 - b - k) / (1 - k), k)

    def inverted(self) -> "RGB":
        return RGB(255 - self.r, 255 - self.g, 255 - self.b)

    def mix(self, other: "RGB", t: float = 0.5) -> "RGB":
        """Linear interpolation in sRGB space; t=0 → self, t=1 → other."""
        return RGB(
            _clamp_byte(self.r + (other.r - self.r) * t),
            _clamp_byte(self.g + (other.g - self.g) * t),
            _clamp_byte(self.b + (other.b - self.b) * t),
        )

    def formats(self) -> dict[str, str]:
        """Every supported textual representation, ready to copy."""
        h, s, v = self.to_hsv()
        hh, ss, ll = self.to_hsl()
        c, m, y, k = self.to_cmyk()
        return {
            "HEX": self.hex.upper(),
            "RGB": f"rgb({self.r}, {self.g}, {self.b})",
            "HSL": f"hsl({hh:.0f}, {ss * 100:.0f}%, {ll * 100:.0f}%)",
            "HSV": f"hsv({h:.0f}, {s * 100:.0f}%, {v * 100:.0f}%)",
            "CMYK": f"cmyk({c * 100:.0f}%, {m * 100:.0f}%, {y * 100:.0f}%, {k * 100:.0f}%)",
            "Name": nearest_named(self)[0],
        }


# ---------------------------------------------------------------- parsing
_FUNC_RE = re.compile(r"^\s*(rgb|hsl|hsv)\s*\(\s*([^)]*)\)\s*$", re.I)


def _num(token: str, *, percent_scale: float) -> float:
    token = token.strip()
    if token.endswith("%"):
        return float(token[:-1]) / 100 * percent_scale
    return float(token)


def parse_color(text: str) -> RGB:
    """Parse any user-entered color.

    Accepts hex (``#f80``, ``ff8800``), CSS-style functions
    (``rgb(255, 136, 0)``, ``hsl(32, 100%, 50%)``, ``hsv(32, 100%, 100%)``)
    and any name in :data:`NAMED_COLORS`.
    """
    s = text.strip()
    if not s:
        raise ValueError("empty color")
    if s.lower() in NAMED_COLORS:
        return RGB.from_hex(NAMED_COLORS[s.lower()])
    m = _FUNC_RE.match(s)
    if m:
        kind = m.group(1).lower()
        parts = [p for p in re.split(r"[,\s]+", m.group(2).strip()) if p]
        if len(parts) != 3:
            raise ValueError(f"{kind}() needs 3 components: {text!r}")
        if kind == "rgb":
            vals = [_num(p, percent_scale=255) for p in parts]
            if any(not 0 <= v <= 255 for v in vals):
                raise ValueError(f"rgb component out of range: {text!r}")
            return RGB(*(_clamp_byte(v) for v in vals))
        h = float(parts[0].rstrip("°"))
        def unit(tok: str) -> float:
            v = _num(tok, percent_scale=1)
            # Bare numbers > 1 are treated as percentages ("hsl(0, 100, 50)").
            return v / 100 if not tok.endswith("%") and v > 1 else v

        a, b = unit(parts[1]), unit(parts[2])
        if not (0 <= a <= 1 and 0 <= b <= 1):
            raise ValueError(f"{kind} component out of range: {text!r}")
        return RGB.from_hsl(h, a, b) if kind == "hsl" else RGB.from_hsv(h, a, b)
    return RGB.from_hex(s)


# ---------------------------------------------------------------- accessibility
def relative_luminance(c: RGB) -> float:
    """WCAG 2.x relative luminance (0 = black, 1 = white)."""

    def lin(u: float) -> float:
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(x) for x in c._unit())
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: RGB, b: RGB) -> float:
    """WCAG contrast ratio in [1, 21]. ≥4.5 passes AA for body text."""
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def readable_text_color(bg: RGB) -> RGB:
    """Black or white — whichever contrasts more with *bg*."""
    black, white = RGB(0, 0, 0), RGB(255, 255, 255)
    return black if contrast_ratio(bg, black) >= contrast_ratio(bg, white) else white


# ---------------------------------------------------------------- harmonies
def harmonies(c: RGB) -> dict[str, list[RGB]]:
    """Classic color-wheel schemes obtained by rotating hue in HSL space."""
    h, s, l = c.to_hsl()

    def rot(deg: float) -> RGB:
        return RGB.from_hsl((h + deg) % 360, s, l)

    return {
        "complementary": [c, rot(180)],
        "analogous": [rot(-30), c, rot(30)],
        "triadic": [c, rot(120), rot(240)],
        "split-complementary": [c, rot(150), rot(210)],
        "tetradic": [c, rot(90), rot(180), rot(270)],
        "shades": [RGB.from_hsl(h, s, max(0.0, l - d)) for d in (0.0, 0.15, 0.3)],
        "tints": [RGB.from_hsl(h, s, min(1.0, l + d)) for d in (0.0, 0.15, 0.3)],
    }


# ---------------------------------------------------------------- naming
# A curated subset of the CSS named colors — enough to give a useful label.
NAMED_COLORS: dict[str, str] = {
    "black": "#000000", "white": "#ffffff", "gray": "#808080", "silver": "#c0c0c0",
    "dimgray": "#696969", "lightgray": "#d3d3d3", "gainsboro": "#dcdcdc",
    "red": "#ff0000", "maroon": "#800000", "darkred": "#8b0000", "crimson": "#dc143c",
    "firebrick": "#b22222", "salmon": "#fa8072", "tomato": "#ff6347", "coral": "#ff7f50",
    "orangered": "#ff4500", "orange": "#ffa500", "darkorange": "#ff8c00", "gold": "#ffd700",
    "yellow": "#ffff00", "khaki": "#f0e68c", "olive": "#808000", "beige": "#f5f5dc",
    "lime": "#00ff00", "green": "#008000", "darkgreen": "#006400", "forestgreen": "#228b22",
    "seagreen": "#2e8b57", "limegreen": "#32cd32", "lightgreen": "#90ee90",
    "chartreuse": "#7fff00", "olivedrab": "#6b8e23", "teal": "#008080", "cyan": "#00ffff",
    "turquoise": "#40e0d0", "aquamarine": "#7fffd4", "cadetblue": "#5f9ea0",
    "blue": "#0000ff", "navy": "#000080", "darkblue": "#00008b", "royalblue": "#4169e1",
    "steelblue": "#4682b4", "dodgerblue": "#1e90ff", "deepskyblue": "#00bfff",
    "skyblue": "#87ceeb", "lightblue": "#add8e6", "slateblue": "#6a5acd",
    "indigo": "#4b0082", "purple": "#800080", "violet": "#ee82ee", "magenta": "#ff00ff",
    "orchid": "#da70d6", "plum": "#dda0dd", "lavender": "#e6e6fa", "pink": "#ffc0cb",
    "hotpink": "#ff69b4", "deeppink": "#ff1493", "brown": "#a52a2a", "chocolate": "#d2691e",
    "sienna": "#a0522d", "peru": "#cd853f", "tan": "#d2b48c", "wheat": "#f5deb3",
    "ivory": "#fffff0", "slategray": "#708090", "midnightblue": "#191970",
}

_NAMED_RGB = {name: RGB.from_hex(h) for name, h in NAMED_COLORS.items()}


def _redmean_distance(a: RGB, b: RGB) -> float:
    """'Redmean' weighted Euclidean distance — a cheap perceptual
    approximation that is noticeably better than plain RGB distance."""
    rmean = (a.r + b.r) / 2
    dr, dg, db = a.r - b.r, a.g - b.g, a.b - b.b
    return math.sqrt((2 + rmean / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rmean) / 256) * db * db)


def nearest_named(c: RGB) -> tuple[str, float]:
    """Return ``(name, distance)`` of the closest named color (linear scan)."""
    best = min(_NAMED_RGB.items(), key=lambda kv: _redmean_distance(c, kv[1]))
    return best[0], _redmean_distance(c, best[1])
