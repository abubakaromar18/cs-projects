import pytest

from colorpick.cli import main


def test_convert(capsys):
    assert main(["convert", "rgb(255,136,0)"]) == 0
    out = capsys.readouterr().out
    assert "HEX   #FF8800" in out and "hsl(32, 100%, 50%)" in out


def test_contrast(capsys):
    main(["contrast", "black", "white"])
    assert capsys.readouterr().out.strip() == "21.00:1  AAA"


def test_harmony(capsys):
    main(["harmony", "red"])
    assert "complementary        #FF0000 #00FFFF" in capsys.readouterr().out


def test_bad_color_exits():
    with pytest.raises(SystemExit):
        main(["convert", "bogus"])
