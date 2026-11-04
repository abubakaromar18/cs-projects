import random

import pytest

from cipherbreak import caesar_encrypt, crack_caesar, crack_vigenere, vigenere_encrypt
from cipherbreak.crack import (columns, guess_key_length, kasiski_distances, kasiski_factor_counts,
                               minimal_period)
from cipherbreak.stats import letters_only


@pytest.mark.parametrize("shift", range(26))
def test_crack_caesar_every_shift(sample, shift):
    best = crack_caesar(caesar_encrypt(sample, shift))[0]
    assert best.shift == shift
    assert best.plaintext == sample


def test_crack_caesar_short_message():
    msg = "Meet me near the old clock tower at seven tonight."
    assert crack_caesar(caesar_encrypt(msg, 20))[0].plaintext == msg


def test_crack_caesar_returns_all_candidates_sorted(sample):
    cands = crack_caesar(sample)
    assert len(cands) == 26 and {c.shift for c in cands} == set(range(26))
    assert [c.chi2 for c in cands] == sorted(c.chi2 for c in cands)


def test_columns():
    assert columns("ABCDEFG", 3) == ["ADG", "BE", "CF"]


def test_minimal_period():
    assert minimal_period("KEYKEYKEY") == "KEY"
    assert minimal_period("ABAB") == "AB"
    assert minimal_period("ABCA") == "ABCA"
    assert minimal_period("ZZZ") == "Z"


def test_kasiski_finds_known_repeat():
    # "THE" at 0 and 9 -> distance 9
    assert 9 in kasiski_distances("THEXXXXXXTHE")
    counts = kasiski_factor_counts("THEXXXXXXTHE", 10)
    assert counts[3] >= 1 and counts[9] >= 1


@pytest.mark.parametrize("key", ["LEMON", "KEY", "QUIZ", "BACKDOOR", "FREQUENCY", "CRYPTOGRAPHY"])
def test_guess_key_length(sample, key):
    assert guess_key_length(letters_only(vigenere_encrypt(sample, key))) == len(key)


@pytest.mark.parametrize("key", ["LEMON", "KEY", "QUIZ", "BACKDOOR", "FREQUENCY", "CRYPTOGRAPHY", "A"])
def test_crack_vigenere(sample, key):
    res = crack_vigenere(vigenere_encrypt(sample, key))
    assert res.key == key
    assert res.plaintext == sample
    assert res.looks_english


def test_crack_vigenere_collapses_repeated_key(sample):
    assert crack_vigenere(vigenere_encrypt(sample, "ZZ")).key == "Z"


def test_crack_vigenere_random_keys(sample):
    rng = random.Random(30)
    for _ in range(15):
        key = "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(rng.randint(2, 10)))
        res = crack_vigenere(vigenere_encrypt(sample, key))
        assert res.plaintext == sample, key
        assert minimal_period(key) == res.key


def test_crack_vigenere_with_known_length(sample):
    res = crack_vigenere(vigenere_encrypt(sample, "LEMON"), key_len=5)
    assert res.key == "LEMON"


def test_crack_vigenere_rejects_empty():
    with pytest.raises(ValueError):
        crack_vigenere("1234 !!")
