import json

import pytest

from fileorg.rules import Rules, extension_of, load_rules


@pytest.mark.parametrize("name,ext", [
    ("photo.jpg", "jpg"),
    ("PHOTO.JPG", "jpg"),
    ("backup.tar.gz", "tar.gz"),
    ("README", ""),
    (".bashrc", ""),
    ("archive.", ""),
    ("my.report.pdf", "pdf"),
])
def test_extension_of(name, ext):
    assert extension_of(name) == ext


def test_default_classification():
    rules = Rules()
    assert rules.classify("a.PNG") == "Images"
    assert rules.classify("song.mp3") == "Audio"
    assert rules.classify("backup.tar.gz") == "Archives"  # falls back to "gz"
    assert rules.classify("unknown.xyz") == "Other"
    assert rules.classify("Makefile") == "Other"


def test_duplicate_extension_rejected():
    with pytest.raises(ValueError, match="both"):
        Rules(categories={"A": ["txt"], "B": [".TXT"]})


def test_load_custom_rules(tmp_path):
    f = tmp_path / "rules.json"
    f.write_text(json.dumps({"Photos": ["jpg"], "_fallback": "Misc"}))
    rules = load_rules(f)
    assert rules.classify("x.jpg") == "Photos"
    assert rules.classify("x.pdf") == "Misc"
    assert rules.folder_names == {"Photos", "Misc"}


def test_load_rules_validates(tmp_path):
    f = tmp_path / "rules.json"
    f.write_text(json.dumps({"Photos": "jpg"}))
    with pytest.raises(ValueError):
        load_rules(f)


def test_load_rules_none_gives_defaults():
    assert load_rules(None).classify("a.pdf") == "Documents"
