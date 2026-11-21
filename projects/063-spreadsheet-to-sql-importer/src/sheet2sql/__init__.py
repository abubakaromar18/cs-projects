"""sheet2sql: infer column types and load CSV/XLSX spreadsheets into SQLite."""

__version__ = "1.0.0"

from .infer import SqlType, classify, join  # noqa: E402
from .loader import ImportFailure, ImportResult, infer_schema, load_table  # noqa: E402
from .readers import read_any, read_csv, read_xlsx  # noqa: E402

__all__ = [
    "SqlType", "classify", "join",
    "ImportFailure", "ImportResult", "infer_schema", "load_table",
    "read_any", "read_csv", "read_xlsx",
]
