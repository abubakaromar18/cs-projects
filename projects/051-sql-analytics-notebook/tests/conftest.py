import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics import build_database  # noqa: E402


@pytest.fixture(scope="session")
def conn():
    c = build_database()
    yield c
    c.close()


def as_dicts(result):
    """Turn (columns, rows) into a list of dicts for readable assertions."""
    cols, rows = result
    return [dict(zip(cols, r)) for r in rows]
