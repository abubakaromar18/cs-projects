"""Caesar and Vigenere ciphers.

Both ciphers shift letters within the 26-letter Latin alphabet and leave every
other character (spaces, digits, punctuation) untouched. Case is preserved, so
"Hello, World!" stays readable in shape after encryption -- which is exactly
the kind of leak frequency analysis exploits.
"""

from __future__ import annotations

from collections.abc import Iterable

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _shift_char(ch: str, shift: int) -> str:
    """Shift one ASCII letter by `shift` positions (mod 26); pass others through."""
    if "a" <= ch <= "z":
        base = ord("a")
    elif "A" <= ch <= "Z":
        base = ord("A")
    else:
        return ch
    return chr(base + (ord(ch) - base + shift) % 26)


def caesar_encrypt(text: str, shift: int) -> str:
    """Rotate every letter forward by `shift` (any integer; reduced mod 26)."""
    return "".join(_shift_char(c, shift) for c in text)


def caesar_decrypt(text: str, shift: int) -> str:
    """Inverse of :func:`caesar_encrypt`."""
    return caesar_encrypt(text, -shift)


def key_to_shifts(key: str) -> list[int]:
    """Convert a key like "Lemon" to shifts [11, 4, 12, 14, 13]. Non-letters are ignored."""
    shifts = [ord(c) - ord("A") for c in key.upper() if c in ALPHABET]
    if not shifts:
        raise ValueError("Vigenere key must contain at least one letter")
    return shifts


def shifts_to_key(shifts: Iterable[int]) -> str:
    """Inverse of :func:`key_to_shifts`."""
    return "".join(ALPHABET[s % 26] for s in shifts)


def _vigenere(text: str, key: str, sign: int) -> str:
    shifts = key_to_shifts(key)
    out: list[str] = []
    i = 0  # the key only advances on letters, the classical convention
    for ch in text:
        if ch.isascii() and ch.isalpha():
            out.append(_shift_char(ch, sign * shifts[i % len(shifts)]))
            i += 1
        else:
            out.append(ch)
    return "".join(out)


def vigenere_encrypt(text: str, key: str) -> str:
    """Polyalphabetic encryption: letter i is Caesar-shifted by key[i mod len(key)]."""
    return _vigenere(text, key, +1)


def vigenere_decrypt(text: str, key: str) -> str:
    """Inverse of :func:`vigenere_encrypt`."""
    return _vigenere(text, key, -1)
