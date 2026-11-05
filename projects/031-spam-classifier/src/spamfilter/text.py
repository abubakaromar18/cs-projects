"""Text normalisation and tokenisation.

Spam is full of signals that a naive ``str.split`` throws away: phone numbers,
URLs, currency symbols and SHOUTING. Rather than keep every distinct phone
number as its own (never-seen-again) token, we map such patterns to shared
placeholder tokens so the classifier can learn "messages with a premium-rate
number are spammy" from a handful of examples.
"""

from __future__ import annotations

import re

# Order matters: e-mails, then URLs, are replaced before we strip punctuation.
_URL = re.compile(r"(https?://\S+|www\.\S+|\b\S+\.(com|net|org|example|co\.uk)\b\S*)", re.I)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
_MONEY = re.compile(r"[£$€]\s?\d[\d,]*(\.\d+)?|\b\d+(\.\d+)?\s?(p|pence|gbp|usd)\b", re.I)
_PHONE = re.compile(r"\b\d[\d\s-]{6,}\d\b")
_NUMBER = re.compile(r"\b\d+\b")
_WORD = re.compile(r"[a-z]+(?:'[a-z]+)?|__[a-z]+__")

# A small stop-word list. Removing these slightly reduces noise; the classifier
# still works fine without it (try ``tokenize(..., stopwords=frozenset())``).
STOPWORDS = frozenset(
    """a an and are as at be but by for from has have i if in is it its me my
    of on or so that the this to was we were will with you your""".split()
)


def tokenize(text: str, *, stopwords: frozenset[str] = STOPWORDS,
             bigrams: bool = False) -> list[str]:
    """Turn a raw message into a list of tokens.

    Placeholders produced: ``__url__``, ``__email__``, ``__money__``,
    ``__phone__``, ``__num__`` and ``__caps__`` (one per ALL-CAPS word of
    three or more letters).
    """
    caps = sum(1 for w in re.findall(r"\b[A-Z]{3,}\b", text))

    t = _EMAIL.sub(" __email__ ", text)   # before URLs: "a@b.com" contains "b.com"
    t = _URL.sub(" __url__ ", t)
    t = _MONEY.sub(" __money__ ", t)
    t = _PHONE.sub(" __phone__ ", t)
    t = _NUMBER.sub(" __num__ ", t)
    t = t.lower()

    tokens = [w for w in _WORD.findall(t) if w not in stopwords]
    tokens.extend(["__caps__"] * caps)

    if bigrams:
        words = [w for w in tokens if w != "__caps__"]
        tokens.extend(f"{a}_{b}" for a, b in zip(words, words[1:]))
    return tokens
