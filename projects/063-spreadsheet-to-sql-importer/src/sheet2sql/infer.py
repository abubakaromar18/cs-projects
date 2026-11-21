"""Column type inference.

Each raw cell (a string from CSV, or a native Python value from XLSX) is
classified into the *narrowest* SQL type that can represent it. A column's
type is then the least upper bound ("join") of all its cell types in a small
type lattice:

        TEXT
       /  |  \\
    REAL  |  DATETIME
     |    |    |
  INTEGER |   DATE
     |    |
  BOOLEAN-+

    NULL is the bottom element: it joins with anything to give that thing.

Joining two types walks up until a common ancestor is found, so a column of
``1, 2, 3.5`` becomes REAL, ``2024-01-01, 2024-01-01T10:00`` becomes DATETIME,
and anything incompatible (``1, hello``) widens to TEXT.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


class SqlType(str, Enum):
    NULL = "NULL"
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    REAL = "REAL"
    DATE = "DATE"
    DATETIME = "DATETIME"
    TEXT = "TEXT"


# Parent of each node in the lattice (TEXT is the top).
_PARENT: dict[SqlType, SqlType | None] = {
    SqlType.BOOLEAN: SqlType.INTEGER,
    SqlType.INTEGER: SqlType.REAL,
    SqlType.REAL: SqlType.TEXT,
    SqlType.DATE: SqlType.DATETIME,
    SqlType.DATETIME: SqlType.TEXT,
    SqlType.TEXT: None,
}


def _ancestors(t: SqlType) -> list[SqlType]:
    chain: list[SqlType] = []
    cur: SqlType | None = t
    while cur is not None:
        chain.append(cur)
        cur = _PARENT[cur]
    return chain


def join(a: SqlType, b: SqlType) -> SqlType:
    """Least upper bound of two types in the lattice."""
    if a is SqlType.NULL:
        return b
    if b is SqlType.NULL:
        return a
    b_chain = set(_ancestors(b))
    for t in _ancestors(a):
        if t in b_chain:
            return t
    return SqlType.TEXT  # unreachable: TEXT is a common ancestor of everything


# --- Cell classification ---------------------------------------------------

NULL_TOKENS = frozenset({"", "null", "none", "na", "n/a", "nan", "-"})
TRUE_TOKENS = frozenset({"true", "yes", "y", "t"})
FALSE_TOKENS = frozenset({"false", "no", "n", "f"})

# Integers: optional sign, digits, optional thousands separators.
# Leading zeros (e.g. ZIP codes "02134") are deliberately NOT integers,
# because converting them would silently destroy data.
_INT_RE = re.compile(r"^[+-]?(0|[1-9]\d{0,2}(,\d{3})+|[1-9]\d*)$")
_REAL_RE = re.compile(
    r"^[+-]?((\d{1,3}(,\d{3})+|\d+)(\.\d*)?|\.\d+)([eE][+-]?\d+)?$"
)
_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y")
_DATETIME_FORMATS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
)


def is_null(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and value != value:  # NaN
        return True
    return isinstance(value, str) and value.strip().lower() in NULL_TOKENS


def _parse_date(s: str) -> _dt.date | None:
    for fmt in _DATE_FORMATS:
        try:
            return _dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _parse_datetime(s: str) -> _dt.datetime | None:
    for fmt in _DATETIME_FORMATS:
        try:
            return _dt.datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def classify(value: Any) -> SqlType:
    """Return the narrowest type that can represent one cell."""
    if is_null(value):
        return SqlType.NULL
    # Native values (from XLSX) carry their own types.
    if isinstance(value, bool):
        return SqlType.BOOLEAN
    if isinstance(value, int):
        return SqlType.INTEGER
    if isinstance(value, float):
        return SqlType.INTEGER if value.is_integer() else SqlType.REAL
    if isinstance(value, _dt.datetime):
        if value.time() == _dt.time(0, 0):
            return SqlType.DATE
        return SqlType.DATETIME
    if isinstance(value, _dt.date):
        return SqlType.DATE

    s = str(value).strip()
    low = s.lower()
    if low in TRUE_TOKENS or low in FALSE_TOKENS:
        return SqlType.BOOLEAN
    if _INT_RE.match(s):
        return SqlType.INTEGER
    if _REAL_RE.match(s) and not re.match(r"^[+-]?0\d", s):
        return SqlType.REAL
    if _parse_date(s) is not None:
        return SqlType.DATE
    if _parse_datetime(s) is not None:
        return SqlType.DATETIME
    return SqlType.TEXT


# --- Conversion -------------------------------------------------------------


def convert(value: Any, target: SqlType) -> Any:
    """Convert a cell to the Python value stored for ``target``.

    Dates are stored as ISO-8601 text, which sorts correctly and is what
    SQLite's date/time functions expect.
    """
    if is_null(value):
        return None
    if target is SqlType.TEXT:
        if isinstance(value, (_dt.date, _dt.datetime)):
            return value.isoformat(sep=" ") if isinstance(value, _dt.datetime) else value.isoformat()
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).strip() if isinstance(value, str) else str(value)

    if target is SqlType.BOOLEAN:
        if isinstance(value, (bool, int, float)):
            return int(bool(value))
        return 1 if str(value).strip().lower() in TRUE_TOKENS else 0

    if target is SqlType.INTEGER:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        s = str(value).strip().lower()
        if s in TRUE_TOKENS:
            return 1
        if s in FALSE_TOKENS:
            return 0
        return int(s.replace(",", ""))

    if target is SqlType.REAL:
        if isinstance(value, (bool, int, float)):
            return float(value)
        s = str(value).strip().lower()
        if s in TRUE_TOKENS:
            return 1.0
        if s in FALSE_TOKENS:
            return 0.0
        return float(s.replace(",", ""))

    if target is SqlType.DATE:
        if isinstance(value, _dt.datetime):
            return value.date().isoformat()
        if isinstance(value, _dt.date):
            return value.isoformat()
        d = _parse_date(str(value).strip())
        assert d is not None, f"not a date: {value!r}"
        return d.isoformat()

    if target is SqlType.DATETIME:
        if isinstance(value, _dt.datetime):
            return value.isoformat(sep=" ")
        if isinstance(value, _dt.date):
            return _dt.datetime.combine(value, _dt.time()).isoformat(sep=" ")
        s = str(value).strip()
        dt = _parse_datetime(s)
        if dt is None:
            d = _parse_date(s)
            assert d is not None, f"not a datetime: {value!r}"
            dt = _dt.datetime.combine(d, _dt.time())
        return dt.isoformat(sep=" ")

    raise ValueError(f"cannot convert to {target}")  # pragma: no cover


# --- Column profiling ------------------------------------------------------


@dataclass
class ColumnProfile:
    """Statistics gathered while scanning one column."""

    name: str
    type: SqlType = SqlType.NULL
    non_null: int = 0
    nulls: int = 0
    max_len: int = 0
    _seen: set = field(default_factory=set, repr=False)
    unique: bool = True

    def observe(self, value: Any) -> None:
        t = classify(value)
        self.type = join(self.type, t)
        if t is SqlType.NULL:
            self.nulls += 1
            return
        self.non_null += 1
        key = str(value).strip() if isinstance(value, str) else value
        self.max_len = max(self.max_len, len(str(key)))
        if self.unique:
            if key in self._seen:
                self.unique = False
                self._seen.clear()  # free memory; no longer needed
            else:
                self._seen.add(key)

    @property
    def final_type(self) -> SqlType:
        # An all-null column has no evidence; TEXT is the safe choice.
        return SqlType.TEXT if self.type is SqlType.NULL else self.type

    @property
    def nullable(self) -> bool:
        return self.nulls > 0 or self.non_null == 0


def profile_columns(
    header: list[str], rows: Iterable[list[Any]], sample: int | None = None
) -> list[ColumnProfile]:
    """Scan up to ``sample`` rows (all if None) and profile each column."""
    profiles = [ColumnProfile(name) for name in header]
    for i, row in enumerate(rows):
        if sample is not None and i >= sample:
            break
        for j, prof in enumerate(profiles):
            prof.observe(row[j] if j < len(row) else None)
    return profiles
