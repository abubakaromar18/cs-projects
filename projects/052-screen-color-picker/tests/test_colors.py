import pytest

from colorpick.colors import (
    RGB, contrast_ratio, harmonies, nearest_named, parse_color, readable_text_color, relative_luminance,
)


def test_hex_roundtrip_and_shorthand():
    assert RGB.from_hex("#ff8800") == RGB(255, 136, 0)
    assert RGB.from_hex("f80") == RGB(255, 136, 0)
    assert RGB(255, 136, 0).hex == "#ff8800"


@pytest.mark.parametrize("bad", ["", "#12", "#ggg", "1234567", "#12345"])
def test_bad_hex(bad):
    with pytest.raises(ValueError):
        RGB.from_hex(bad)


def test_channel_validation():
    with pytest.raises(ValueError):
        RGB(256, 0, 0)
    with pytest.raises(ValueError):
        RGB(-1, 0, 0)


@pytest.mark.parametrize("c", [RGB(0, 0, 0), RGB(255, 255, 255), RGB(255, 136, 0), RGB(12, 200, 99), RGB(1, 2, 3)])
def test_hsv_hsl_cmyk_roundtrip(c):
    assert RGB.from_hsv(*c.to_hsv()) == c
    assert RGB.from_hsl(*c.to_hsl()) == c
    assert RGB.from_cmyk(*c.to_cmyk()) == c


def test_known_values():
    h, s, l = RGB(255, 0, 0).to_hsl()
    assert (round(h), s, l) == (0, 1.0, 0.5)
    assert RGB(0, 0, 0).to_cmyk() == (0.0, 0.0, 0.0, 1.0)
    assert RGB(0, 255, 255).to_cmyk() == (1.0, 0.0, 0.0, 0.0)
    h, s, v = RGB(0, 0, 255).to_hsv()
    assert round(h) == 240 and s == 1 and v == 1


def test_formats():
    f = RGB(255, 136, 0).formats()
    assert f["HEX"] == "#FF8800"
    assert f["RGB"] == "rgb(255, 136, 0)"
    assert f["HSL"] == "hsl(32, 100%, 50%)"
    assert f["CMYK"] == "cmyk(0%, 47%, 100%, 0%)"
    assert f["Name"] == "darkorange"


@pytest.mark.parametrize("text,expected", [
    ("#00f", RGB(0, 0, 255)),
    ("rgb(10, 20, 30)", RGB(10, 20, 30)),
    ("RGB(100%, 0%, 50%)", RGB(255, 0, 128)),
    ("rgb(10 20 30)", RGB(10, 20, 30)),
    ("hsl(120, 100%, 50%)", RGB(0, 255, 0)),
    ("hsl(0, 100, 50)", RGB(255, 0, 0)),
    ("hsv(240, 100%, 100%)", RGB(0, 0, 255)),
    ("  Tomato ", RGB(255, 99, 71)),
])
def test_parse_color(text, expected):
    assert parse_color(text) == expected


@pytest.mark.parametrize("bad", ["", "rgb(1,2)", "rgb(300,0,0)", "hsl(0, 200%, 50%)", "notacolor"])
def test_parse_color_errors(bad):
    with pytest.raises(ValueError):
        parse_color(bad)


def test_wcag_contrast():
    black, white = RGB(0, 0, 0), RGB(255, 255, 255)
    assert relative_luminance(black) == 0
    assert relative_luminance(white) == pytest.approx(1)
    assert contrast_ratio(black, white) == pytest.approx(21)
    assert contrast_ratio(white, black) == contrast_ratio(black, white)
    # Classic reference value: #777 on white ≈ 4.48 (just fails AA).
    assert contrast_ratio(RGB.from_hex("#777"), white) == pytest.approx(4.48, abs=0.01)
    assert readable_text_color(RGB(250, 250, 0)) == black
    assert readable_text_color(RGB(0, 0, 120)) == white


def test_harmonies():
    red = RGB(255, 0, 0)
    h = harmonies(red)
    assert h["complementary"][1] == RGB(0, 255, 255)
    assert h["triadic"][1:] == [RGB(0, 255, 0), RGB(0, 0, 255)]
    assert len(h["tetradic"]) == 4
    # Shades get darker, tints lighter.
    assert [c.to_hsl()[2] for c in h["shades"]] == sorted((c.to_hsl()[2] for c in h["shades"]), reverse=True)
    assert [c.to_hsl()[2] for c in h["tints"]] == sorted(c.to_hsl()[2] for c in h["tints"])


def test_nearest_named():
    assert nearest_named(RGB(255, 0, 0)) == ("red", 0.0)
    assert nearest_named(RGB(250, 5, 5))[0] == "red"
    assert nearest_named(RGB(10, 10, 130))[0] in {"navy", "darkblue"}


def test_mix_and_invert():
    assert RGB(0, 0, 0).mix(RGB(255, 255, 255)) == RGB(128, 128, 128)
    assert RGB(10, 20, 30).inverted() == RGB(245, 235, 225)
