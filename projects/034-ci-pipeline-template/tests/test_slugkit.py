import pytest

import slugkit
from slugkit.cli import main


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello World", "hello-world"),
        ("  Héllo, Wörld!  ", "hello-world"),
        ("C++ & Rust: 2024 edition", "c-rust-2024-edition"),
        ("already-a-slug", "already-a-slug"),
        ("!!!", ""),
        ("日本語", ""),
    ],
)
def test_slugify(text, expected):
    assert slugkit.slugify(text) == expected


def test_custom_separator():
    assert slugkit.slugify("Hello Big World", separator="_") == "hello_big_world"


def test_max_length_cuts_on_word_boundary():
    assert slugkit.slugify("the quick brown fox", max_length=12) == "the-quick"
    assert slugkit.slugify("the quick brown fox", max_length=9) == "the-quick"
    assert slugkit.slugify("supercalifragilistic", max_length=5) == "super"


@pytest.mark.parametrize("sep", ["", "a", "1"])
def test_bad_separator(sep):
    with pytest.raises(ValueError):
        slugkit.slugify("x", separator=sep)


def test_bad_max_length():
    with pytest.raises(ValueError):
        slugkit.slugify("x", max_length=0)


def test_unique_slug():
    assert slugkit.unique_slug("Post", []) == "post"
    assert slugkit.unique_slug("Post", ["post"]) == "post-2"
    assert slugkit.unique_slug("Post", ["post", "post-2", "post-3"]) == "post-4"
    assert slugkit.unique_slug("???", []) == "item"


def test_cli(capsys):
    assert main(["Hello", "CLI", "-s", "_"]) == 0
    assert capsys.readouterr().out.strip() == "hello_cli"
    assert main(["x", "-m", "0"]) == 2
    assert "error" in capsys.readouterr().err


def test_version_is_string():
    assert isinstance(slugkit.__version__, str)
