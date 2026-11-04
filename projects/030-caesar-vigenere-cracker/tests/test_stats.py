import math

import pytest

from cipherbreak import caesar_encrypt, chi_squared, english_score, index_of_coincidence, letter_counts
from cipherbreak.stats import ENGLISH_IOC, ENGLISH_PROB, RANDOM_IOC, friedman_estimate, letters_only
from cipherbreak import vigenere_encrypt


def test_probabilities_sum_to_one():
    assert sum(ENGLISH_PROB.values()) == pytest.approx(1.0)
    assert 0.064 < ENGLISH_IOC < 0.067


def test_letters_only_and_counts():
    assert letters_only("a-B c!1") == "ABC"
    counts = letter_counts("Hello")
    assert len(counts) == 26 and counts["L"] == 2 and counts["Z"] == 0


def test_ioc_edge_cases():
    assert index_of_coincidence("") == 0.0
    assert index_of_coincidence("A") == 0.0
    assert index_of_coincidence("AAAA") == 1.0
    assert index_of_coincidence("ABCDEFGHIJKLMNOPQRSTUVWXYZ") == 0.0


def test_english_ioc_and_caesar_invariance(sample):
    ioc = index_of_coincidence(sample)
    assert 0.06 < ioc < 0.075
    # A monoalphabetic substitution only relabels letters: IoC is unchanged.
    assert index_of_coincidence(caesar_encrypt(sample, 11)) == pytest.approx(ioc)


def test_vigenere_flattens_ioc(sample):
    ioc = index_of_coincidence(vigenere_encrypt(sample, "CRYPTOGRAPHY"))
    assert ioc < 0.05
    assert abs(ioc - RANDOM_IOC) < abs(ioc - ENGLISH_IOC)


def test_chi_squared_prefers_english(sample):
    assert chi_squared(sample) < 60
    assert chi_squared(caesar_encrypt(sample, 5)) > 5 * chi_squared(sample)
    assert chi_squared("123 !!") == math.inf


def test_english_score(sample):
    assert english_score(sample) > english_score(caesar_encrypt(sample, 9))
    assert english_score("") == -math.inf


def test_friedman_estimate_is_in_the_right_ballpark(sample):
    est = friedman_estimate(vigenere_encrypt(sample, "LEMON"))
    # Friedman is a coarse statistical estimate; it only needs to land near the truth.
    assert 2 <= est <= 12
    assert friedman_estimate(sample) < 1.6
