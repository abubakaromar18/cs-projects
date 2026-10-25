import math

from password_checker.patterns import (
    _case_bits, dictionary_matches, find_matches, keyboard_matches,
    load_wordlist, repeat_matches, sequence_matches, year_matches,
)

PC = math.log2(62)


def kinds(matches):
    return {(m.kind, m.token) for m in matches}


def test_wordlists_load_with_ranks():
    ranks = load_wordlist("common_passwords.txt")
    assert ranks["123456"] == 1
    assert ranks["password"] == 2
    assert all(not w.startswith("#") for w in ranks)


def test_dictionary_plain_and_leet():
    found = kinds(dictionary_matches("P4$$w0rd", PC))
    assert ("common-password (leet)", "P4$$w0rd") in found
    plain = kinds(dictionary_matches("qwerty123", PC))
    assert ("common-password", "qwerty123") in plain  # not mislabelled leet


def test_leet_costs_more_than_plain():
    plain = next(m for m in dictionary_matches("password", PC) if m.token == "password")
    leet = next(m for m in dictionary_matches("p4$$w0rd", PC) if m.token == "p4$$w0rd")
    assert leet.bits > plain.bits


def test_case_bits():
    assert _case_bits("hello") == 0
    assert _case_bits("Hello") == 1
    assert _case_bits("HELLO") == 1
    assert _case_bits("hElLo") > 1


def test_repeats():
    assert ("repeat", "aaaaaa") in kinds(repeat_matches("xaaaaaa", PC))
    assert ("repeat", "abcabcabc") in kinds(repeat_matches("abcabcabc", PC))


def test_sequences_both_directions():
    assert ("sequence", "abcdef") in kinds(sequence_matches("abcdef", PC))
    assert ("sequence", "9876") in kinds(sequence_matches("x9876", PC))
    assert not list(sequence_matches("acegik", PC))


def test_keyboard_walks():
    assert ("keyboard", "qwerty") in kinds(keyboard_matches("qwerty!", PC))
    assert ("keyboard", "lkjh") in kinds(keyboard_matches("lkjh", PC))
    assert not list(keyboard_matches("qwe", PC))  # too short


def test_years():
    assert ("year", "1999") in kinds(year_matches("bob1999", PC))
    assert not list(year_matches("1850", PC))


def test_every_match_saves_bits_or_is_filtered():
    for m in find_matches("Summer2024qwerty", PC):
        assert 0 <= m.start < m.end <= 16
        assert m.token == "Summer2024qwerty"[m.start:m.end]
