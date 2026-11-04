import pytest

from cipherbreak import caesar_decrypt, caesar_encrypt, vigenere_decrypt, vigenere_encrypt
from cipherbreak.ciphers import key_to_shifts, shifts_to_key


def test_caesar_known_vector():
    assert caesar_encrypt("Hello, World!", 3) == "Khoor, Zruog!"


def test_caesar_wraps_and_preserves_case():
    assert caesar_encrypt("xyz XYZ", 3) == "abc ABC"
    assert caesar_encrypt("abc", -1) == "zab"
    assert caesar_encrypt("abc", 29) == caesar_encrypt("abc", 3)


@pytest.mark.parametrize("shift", range(-30, 31, 7))
def test_caesar_roundtrip(sample, shift):
    assert caesar_decrypt(caesar_encrypt(sample, shift), shift) == sample


def test_rot13_is_involution():
    assert caesar_encrypt(caesar_encrypt("Why did the chicken?", 13), 13) == "Why did the chicken?"


def test_vigenere_textbook_vector():
    # Classic example: ATTACKATDAWN + LEMON
    assert vigenere_encrypt("ATTACKATDAWN", "LEMON") == "LXFOPVEFRNHR"
    assert vigenere_decrypt("LXFOPVEFRNHR", "lemon") == "ATTACKATDAWN"


def test_vigenere_key_skips_non_letters():
    # Spaces and punctuation do not consume key characters.
    assert vigenere_encrypt("attack at dawn!", "LEMON") == "lxfopv ef rnhr!"


def test_vigenere_non_ascii_untouched():
    assert vigenere_encrypt("café", "B") == "dbgé"


@pytest.mark.parametrize("key", ["A", "KEY", "Secret Key", "CRYPTOGRAPHY"])
def test_vigenere_roundtrip(sample, key):
    assert vigenere_decrypt(vigenere_encrypt(sample, key), key) == sample


def test_vigenere_with_key_a_is_identity(sample):
    assert vigenere_encrypt(sample, "AAAA") == sample


def test_bad_key_rejected():
    with pytest.raises(ValueError):
        vigenere_encrypt("text", "123")


def test_key_shift_conversion():
    assert key_to_shifts("Lemon") == [11, 4, 12, 14, 13]
    assert shifts_to_key([11, 4, 12, 14, 13, 26]) == "LEMONA"
