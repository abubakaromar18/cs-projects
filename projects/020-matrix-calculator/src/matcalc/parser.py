"""Parsing matrices from the text formats people actually type.

Accepted forms (entries may be integers, decimals or fractions like ``-3/4``):

* MATLAB style:   ``1 2 3; 4 5 6``
* Python/JSON:    ``[[1, 2, 3], [4, 5, 6]]``
* One row per line, separated by spaces and/or commas (handy for files)
"""

from __future__ import annotations

import re

from .matrix import Matrix

_TOKEN = re.compile(r"[^\s,]+")


def parse_matrix(text: str) -> Matrix:
    text = text.strip()
    if not text:
        raise ValueError("empty matrix")

    if text.startswith("["):
        rows = _parse_nested(text)
    else:
        raw_rows = re.split(r"[;\n]", text)
        rows = [_TOKEN.findall(r) for r in raw_rows if r.strip() and not r.strip().startswith("#")]

    if not rows:
        raise ValueError("empty matrix")
    widths = {len(r) for r in rows}
    if len(widths) != 1:
        raise ValueError(
            "rows have different lengths: " + ", ".join(str(len(r)) for r in rows)
        )
    return Matrix(rows)


def _parse_nested(text: str) -> list[list[str]]:
    """Parse ``[[a, b], [c, d]]`` (or a single row ``[a, b]``) without eval."""
    inner = text.strip()
    if not (inner.startswith("[") and inner.endswith("]")):
        raise ValueError("unbalanced brackets")
    inner = inner[1:-1].strip()
    if "[" not in inner:  # a single row vector like [1, 2, 3]
        return [_TOKEN.findall(inner)]
    groups = re.findall(r"\[([^\[\]]*)\]", inner)
    leftover = re.sub(r"\[[^\[\]]*\]", "", inner)
    if re.search(r"[^\s,]", leftover):
        raise ValueError("unexpected text outside row brackets")
    return [_TOKEN.findall(g) for g in groups]
