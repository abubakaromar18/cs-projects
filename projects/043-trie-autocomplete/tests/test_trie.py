import random

import pytest

from trie_autocomplete import Trie


def brute_force(words: dict[str, int], prefix: str, k: int):
    hits = [(w, f) for w, f in words.items() if w.startswith(prefix)]
    return sorted(hits, key=lambda x: (-x[1], x[0]))[:k]


def test_insert_accumulates_frequency_and_len():
    t = Trie()
    assert t.insert("cat") == 1
    assert t.insert("cat", 4) == 5
    t.insert("car")
    assert len(t) == 2
    assert t.frequency("cat") == 5
    assert "car" in t and "ca" not in t


def test_case_insensitive_by_default():
    t = Trie(["Hello"])
    assert "hello" in t and "HELLO" in t
    s = Trie(["Hello"], case_sensitive=True)
    assert "Hello" in s and "hello" not in s


@pytest.mark.parametrize("bad", ["", None, 5])
def test_insert_rejects_bad_words(bad):
    with pytest.raises(ValueError):
        Trie().insert(bad)


def test_insert_rejects_non_positive_freq():
    with pytest.raises(ValueError):
        Trie().insert("x", 0)


def test_suggest_ranks_by_frequency_then_alpha():
    t = Trie()
    for w, f in {"the": 50, "this": 20, "that": 20, "then": 5, "tree": 30, "thx": 1}.items():
        t.insert(w, f)
    assert t.suggest("th", 3) == [("the", 50), ("that", 20), ("this", 20)]
    assert t.suggest("t", 2) == [("the", 50), ("tree", 30)]
    assert t.suggest("zz") == []
    assert t.suggest("th", 0) == []


def test_prefix_itself_is_a_candidate():
    t = Trie()
    t.insert("pro", 10)
    t.insert("program", 3)
    assert t.suggest("pro") == [("pro", 10), ("program", 3)]


def test_words_with_prefix_is_sorted():
    t = Trie(["b", "ab", "abc", "a", "ba"])
    assert list(t) == ["a", "ab", "abc", "b", "ba"]
    assert [w for w, _ in t.words_with_prefix("ab")] == ["ab", "abc"]
    assert list(t.words_with_prefix("q")) == []


def test_remove_prunes_and_updates_best():
    t = Trie()
    t.insert("car", 100)
    t.insert("cart", 2)
    t.insert("cat", 5)
    assert t.remove("car")
    assert not t.remove("car")
    assert not t.remove("ca")
    assert t.suggest("ca") == [("cat", 5), ("cart", 2)]
    nodes_before = t.node_count()
    t.remove("cart")
    assert t.node_count() == nodes_before - 2  # 'r' and 't' pruned
    t.remove("cat")
    assert len(t) == 0 and t.node_count() == 1
    assert not t.has_prefix("c")


def test_has_prefix_and_longest_common_prefix():
    t = Trie(["transform", "transport"])
    assert t.has_prefix("tran") and not t.has_prefix("tx")
    assert t.longest_common_prefix("t") == "trans"
    assert t.longest_common_prefix("transf") == "transform"
    assert t.longest_common_prefix("zz") == "zz"


def test_prefix_sharing_reduces_nodes():
    t = Trie(["test", "tests", "tester", "testing"])
    # t-e-s-t + s + e-r + i-n-g = 4+1+2+3 = 10 nodes plus root
    assert t.node_count() == 11


def test_unicode_words():
    t = Trie()
    t.insert("café", 3)
    t.insert("cafeteria", 1)
    assert t.suggest("caf") == [("café", 3), ("cafeteria", 1)]


def test_dict_roundtrip():
    t = Trie()
    t.insert("alpha", 3)
    t.insert("beta")
    clone = Trie.from_dict(t.to_dict())
    assert clone.to_dict() == t.to_dict()


@pytest.mark.parametrize("seed", range(5))
def test_suggest_matches_brute_force(seed):
    rng = random.Random(seed)
    words: dict[str, int] = {}
    t = Trie()
    for _ in range(400):
        w = "".join(rng.choice("abc") for _ in range(rng.randint(1, 6)))
        f = rng.randint(1, 5)
        words[w] = words.get(w, 0) + f
        t.insert(w, f)
    # remove some to exercise best-recomputation
    for w in rng.sample(sorted(words), 30):
        t.remove(w)
        del words[w]
    assert len(t) == len(words)
    for prefix in ["", "a", "b", "ab", "cab", "aaa", "cc"]:
        for k in (1, 3, 10, 1000):
            assert t.suggest(prefix, k) == brute_force(words, prefix, k)
