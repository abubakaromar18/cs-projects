"""Shared fixtures.

Every API test is parametrised over both repository implementations, so the
in-memory and SQLite backends are held to exactly the same contract.
"""

from datetime import date, datetime, timedelta, timezone
from itertools import count

import pytest
from fastapi.testclient import TestClient

from todo_api.main import create_app
from todo_api.repository import InMemoryTodoRepository, SqliteTodoRepository

TODAY = date(2026, 11, 1)


class FakeClock:
    """Deterministic clock: each call is one second after the previous one."""

    def __init__(self) -> None:
        self._ticks = count()
        self._start = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self._start + timedelta(seconds=next(self._ticks))


@pytest.fixture(params=["memory", "sqlite"])
def repo(request):
    clock = FakeClock()
    if request.param == "memory":
        return InMemoryTodoRepository(clock=clock)
    return SqliteTodoRepository(":memory:", clock=clock)


@pytest.fixture
def client(repo):
    app = create_app(repository=repo, today=lambda: TODAY)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def make(client):
    """Create a todo via the API and return its JSON."""

    def _make(**fields):
        fields.setdefault("title", "task")
        r = client.post("/todos", json=fields)
        assert r.status_code == 201, r.text
        return r.json()

    return _make
