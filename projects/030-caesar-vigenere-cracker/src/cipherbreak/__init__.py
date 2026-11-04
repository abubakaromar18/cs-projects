"""cipherbreak: classical ciphers and the frequency analysis that breaks them.

Educational toolkit: encrypt/decrypt with Caesar and Vigenere, then recover
keys from ciphertext alone using letter statistics.
"""

from .ciphers import caesar_decrypt, caesar_encrypt, vigenere_decrypt, vigenere_encrypt
from .crack import CaesarCandidate, VigenereResult, crack_caesar, crack_vigenere
from .stats import chi_squared, english_score, index_of_coincidence, letter_counts

__all__ = [
    "caesar_encrypt", "caesar_decrypt", "vigenere_encrypt", "vigenere_decrypt",
    "crack_caesar", "crack_vigenere", "CaesarCandidate", "VigenereResult",
    "chi_squared", "english_score", "index_of_coincidence", "letter_counts",
]
__version__ = "1.0.0"
