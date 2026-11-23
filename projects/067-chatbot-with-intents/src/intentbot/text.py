"""Text normalisation: tokenising, light stemming and n-gram features.

The classifier never sees raw strings. Every utterance is turned into a
bag of features here, so training and prediction always agree on what a
"word" is.
"""

from __future__ import annotations

import re
import unicodedata

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")

# Short list on purpose: words like "what", "how" and "not" carry intent
# ("how are you" vs "who are you"), so they are kept.
STOPWORDS = frozenset(
    "a an the is am are was were be been to of and or in on at for it its "
    "this that i me my you your please can could would will just so".split()
)

# Contractions are expanded before tokenising so "what's" == "what is".
_CONTRACTIONS = {
    "what's": "what is",
    "who's": "who is",
    "it's": "it is",
    "i'm": "i am",
    "you're": "you are",
    "can't": "can not",
    "won't": "will not",
    "don't": "do not",
    "isn't": "is not",
    "how's": "how is",
    "that's": "that is",
    "let's": "let us",
    "whats": "what is",
    "hows": "how is",
}
_CONTRACTION_RE = re.compile(r"\b(?:" + "|".join(re.escape(k) for k in _CONTRACTIONS) + r")(?![a-z'])")


def normalize(text: str) -> str:
    """Lowercase, strip accents and expand common contractions."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("’", "'")
    # Whole-word replacement, so "shows" is never read as "s" + "hows".
    return _CONTRACTION_RE.sub(lambda m: _CONTRACTIONS[m.group(0)], text)


def stem(word: str) -> str:
    """A tiny suffix-stripping stemmer (a cut-down Porter step 1).

    It only needs to be consistent, not linguistically perfect:
    "jokes", "joking" and "joke" should land on the same feature.
    """
    if len(word) <= 3:
        return word
    for suffix, repl in (("ies", "y"), ("ing", ""), ("ed", ""), ("ly", ""), ("es", ""), ("s", "")):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: len(word) - len(suffix)] + repl
            break
    # "joking" -> "jok", "joke" -> "jok": drop a trailing silent e too.
    if word.endswith("e") and len(word) > 3:
        word = word[:-1]
    return word


def tokenize(text: str, *, drop_stopwords: bool = True) -> list[str]:
    """Split into stemmed word tokens."""
    words = _TOKEN_RE.findall(normalize(text))
    words = [w.replace("'", "") for w in words]
    if drop_stopwords:
        words = [w for w in words if w not in STOPWORDS]
    return [stem(w) for w in words]


def features(text: str) -> list[str]:
    """Unigrams plus bigrams.

    Bigrams let the model tell "thank you" from "you" alone, and
    "how are" from "who are", which unigrams after stop-word removal
    cannot always do. Bigrams are built from the stop-word-kept stream.
    """
    unigrams = tokenize(text)
    full = tokenize(text, drop_stopwords=False)
    bigrams = [f"{a}_{b}" for a, b in zip(full, full[1:])]
    return unigrams + bigrams
