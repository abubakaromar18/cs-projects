"""Turn column profiles into a safe SQL schema.

Spreadsheet headers are messy: spaces, punctuation, duplicates, blanks,
reserved words. We normalise them into snake_case identifiers and always
quote them in generated SQL, so no header can break (or inject into) a
statement.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .infer import ColumnProfile, SqlType

# A small set of words that commonly appear as headers and are SQL keywords.
# Quoting already makes them legal; we suffix them anyway so the resulting
# schema is pleasant to query by hand.
RESERVED = frozenset(
    """select from where group order by table index key primary references
    default check unique limit offset join on as and or not null insert
    update delete create drop alter values into case when then else end
    user date time""".split()
)


def to_identifier(raw: str, fallback: str) -> str:
    """Normalise a header into a lowercase snake_case identifier."""
    s = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode()
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)  # camelCase -> camel_Case
    s = re.sub(r"[^0-9a-zA-Z]+", "_", s).strip("_").lower()
    if not s:
        s = fallback
    if s[0].isdigit():
        s = "c_" + s
    if s in RESERVED:
        s += "_"
    return s


def unique_identifiers(headers: list[str]) -> list[str]:
    """Normalise every header and de-duplicate with numeric suffixes."""
    out: list[str] = []
    used: set[str] = set()
    for i, h in enumerate(headers, start=1):
        base = to_identifier(h or "", f"column_{i}")
        name, n = base, 2
        while name in used:
            name = f"{base}_{n}"
            n += 1
        used.add(name)
        out.append(name)
    return out


def quote(ident: str) -> str:
    """Quote an identifier for SQLite (double any embedded quotes)."""
    return '"' + ident.replace('"', '""') + '"'


# SQLite type affinities for each inferred type. BOOLEAN is stored as an
# INTEGER 0/1 with a CHECK constraint; dates are ISO-8601 TEXT.
_DECL = {
    SqlType.BOOLEAN: "INTEGER",
    SqlType.INTEGER: "INTEGER",
    SqlType.REAL: "REAL",
    SqlType.DATE: "TEXT",
    SqlType.DATETIME: "TEXT",
    SqlType.TEXT: "TEXT",
}


@dataclass
class Column:
    name: str
    source: str
    type: SqlType
    nullable: bool
    unique: bool

    def ddl(self, primary_key: bool = False) -> str:
        parts = [quote(self.name), _DECL[self.type]]
        if primary_key:
            parts.append("PRIMARY KEY")
        elif not self.nullable:
            parts.append("NOT NULL")
        if self.type is SqlType.BOOLEAN:
            parts.append(f"CHECK ({quote(self.name)} IN (0, 1))")
        return " ".join(parts)


@dataclass
class Schema:
    table: str
    columns: list[Column]
    primary_key: str | None = None

    def create_sql(self, if_not_exists: bool = False) -> str:
        cols = ",\n  ".join(c.ddl(c.name == self.primary_key) for c in self.columns)
        ine = "IF NOT EXISTS " if if_not_exists else ""
        return f"CREATE TABLE {ine}{quote(self.table)} (\n  {cols}\n);"

    def insert_sql(self) -> str:
        names = ", ".join(quote(c.name) for c in self.columns)
        marks = ", ".join("?" for _ in self.columns)
        return f"INSERT INTO {quote(self.table)} ({names}) VALUES ({marks})"


def _guess_primary_key(columns: list[Column]) -> str | None:
    """Pick an ``id``-like INTEGER column that is unique and never null."""
    candidates = [
        c for c in columns
        if c.type is SqlType.INTEGER and c.unique and not c.nullable
    ]
    for c in candidates:
        if c.name == "id" or (c.name.endswith("_id") and c is columns[0]):
            return c.name
    return None


def build_schema(table: str, profiles: list[ColumnProfile], detect_pk: bool = True) -> Schema:
    names = unique_identifiers([p.name for p in profiles])
    cols = [
        Column(n, p.name, p.final_type, p.nullable, p.unique and p.non_null > 0)
        for n, p in zip(names, profiles)
    ]
    pk = _guess_primary_key(cols) if detect_pk else None
    return Schema(to_identifier(table, "imported"), cols, pk)
