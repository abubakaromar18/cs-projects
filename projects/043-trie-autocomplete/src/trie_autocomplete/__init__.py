"""Trie-based autocomplete with frequency ranking."""

from .corpus import tokenize, train
from .storage import load, save
from .trie import Trie

__all__ = ["Trie", "tokenize", "train", "load", "save"]
__version__ = "1.0.0"
