import math

import pytest

from password_checker.entropy import char_classes, estimate, naive_entropy, pool_size


def test_char_classes_and_pool():
    assert char_classes("aB3!") == {"lowercase", "uppercase", "digits", "symbols"}
    assert pool_size("abc") == 26
    assert pool_size("abc123") == 36
    assert pool_size("") == 0


def test_naive_entropy():
    assert naive_entropy("") == 0
    assert naive_entropy("abcd") == pytest.approx(4 * math.log2(26))


def test_effective_never_exceeds_naive():
    for pw in ["password", "xK9#mQ2$vLp7!zR4", "aaaa", "Summer1999!", "z"]:
        r = estimate(pw)
        assert r.effective_bits <= r.naive_bits + 1e-9


def test_random_password_keeps_full_entropy():
    r = estimate("xK9#mQ2$vLp7!zR4")
    assert r.matches == ()
    assert r.effective_bits == pytest.approx(r.naive_bits)


def test_patterned_password_much_weaker_than_naive():
    r = estimate("P4$$w0rd2024")
    assert r.naive_bits > 70
    assert r.effective_bits < 25
    assert [m.kind for m in r.matches] == ["common-password (leet)", "year"]


def test_selected_matches_do_not_overlap():
    r = estimate("qwertyqwerty1234abcd")
    spans = [(m.start, m.end) for m in r.matches]
    for (a1, b1), (a2, b2) in zip(spans, spans[1:]):
        assert b1 <= a2


def test_empty():
    r = estimate("")
    assert r.naive_bits == r.effective_bits == 0
