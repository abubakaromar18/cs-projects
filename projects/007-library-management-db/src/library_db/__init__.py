"""Library Management DB: a normalized SQLite schema with a Python service layer and CLI."""

from .db import connect, transaction
from .library import Conflict, Library, LibraryError, NotFound

__all__ = ["connect", "transaction", "Library", "LibraryError", "NotFound", "Conflict"]
__version__ = "1.0.0"
