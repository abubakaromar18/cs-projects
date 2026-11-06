"""Core slug functions."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(text: str, separator: str = "-", max_length: int | None = None) -> str:
    """Convert ``text`` into a lowercase ASCII slug.

    Accents are stripped via Unicode NFKD decomposition, every run of
    non-alphanumeric characters collapses into a single ``separator``, and the
    result is optionally truncated at a separator boundary so words are not cut
    in half.

    >>> slugify("Héllo, Wörld!")
    'hello-world'
    """
    if not separator or _NON_ALNUM.fullmatch(separator) is None:
        raise ValueError("separator must be a non-empty string of non-alphanumeric characters")
    if max_length is not None and max_length < 1:
        raise ValueError("max_length must be positive")

    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = _NON_ALNUM.sub(separator, ascii_text.lower()).strip(separator)

    if max_length is not None and len(slug) > max_length:
        cut = slug[:max_length]
        # Back up to the last separator if we chopped a word in half.
        if slug[max_length : max_length + len(separator)] != separator and separator in cut:
            cut = cut[: cut.rindex(separator)]
        slug = cut.strip(separator)
    return slug


def unique_slug(text: str, existing: Iterable[str], separator: str = "-") -> str:
    """Return a slug for ``text`` that does not collide with ``existing``.

    Collisions get a numeric suffix: ``post``, ``post-2``, ``post-3`` ...
    """
    taken = set(existing)
    base = slugify(text, separator) or "item"
    if base not in taken:
        return base
    n = 2
    while f"{base}{separator}{n}" in taken:
        n += 1
    return f"{base}{separator}{n}"
