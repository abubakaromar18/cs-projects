import json

import pytest

from trie_autocomplete import load, save, tokenize, train


def test_tokenize():
    assert list(tokenize("Don't stop—e-mail 42 times, OK?")) == ["don't", "stop", "e-mail", "times", "ok"]
    assert list(tokenize("It’s")) == ["it's"]


def test_train_counts_and_min_length():
    t = train(["the cat and the hat", "The end. a"], min_length=2)
    assert t.frequency("the") == 3
    assert "a" not in t
    assert t.suggest("th", 1) == [("the", 3)]


def test_train_extends_existing():
    t = train(["one two"])
    train(["two three"], t)
    assert t.frequency("two") == 2 and len(t) == 3


def test_save_load_roundtrip(tmp_path):
    p = tmp_path / "sub" / "w.trie.json"
    t = train(["alpha beta beta"])
    save(t, p)
    assert json.loads(p.read_text())["words"] == {"alpha": 1, "beta": 2}
    assert load(p).to_dict() == t.to_dict()
    assert list(p.parent.iterdir()) == [p]  # no temp files left behind


def test_load_missing_returns_empty(tmp_path):
    assert len(load(tmp_path / "nope.json")) == 0


def test_load_rejects_garbage(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("[1, 2]")
    with pytest.raises(ValueError):
        load(p)
