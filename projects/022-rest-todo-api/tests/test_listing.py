"""Filtering, searching, sorting and pagination on GET /todos."""

import pytest


def ids(client, query=""):
    return [t["id"] for t in client.get(f"/todos{query}").json()["items"]]


@pytest.fixture
def seeded(make):
    """Five todos with varied fields. Ids are 1..5 in creation order."""
    make(title="Pay rent", priority="high", due_date="2026-11-03", tags=["home", "money"])
    make(title="buy groceries", priority="medium", tags=["home"], notes="Milk, eggs")
    make(title="Write report", priority="high", due_date="2026-11-10", tags=["work"],
         completed=True)
    make(title="Call Alex", priority="low", due_date="2026-11-02")
    make(title="Archive emails", priority="low", tags=["work"], notes="old 50% promo mail")


def test_empty_list(client):
    assert client.get("/todos").json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_default_order_is_creation(client, seeded):
    assert ids(client) == [1, 2, 3, 4, 5]
    assert ids(client, "?order=desc") == [5, 4, 3, 2, 1]


@pytest.mark.parametrize(
    "query, expected",
    [
        ("?completed=true", [3]),
        ("?completed=false", [1, 2, 4, 5]),
        ("?priority=high", [1, 3]),
        ("?tag=home", [1, 2]),
        ("?tag=WORK", [3, 5]),
        ("?tag=nope", []),
        ("?q=REPORT", [3]),
        ("?q=eggs", [2]),            # matches notes
        ("?q=50%25", [5]),           # "%" is literal, not a wildcard
        ("?q=_", []),                # _ is literal too
        ("?due_before=2026-11-03", [1, 4]),  # inclusive; undated todos excluded
        ("?priority=high&completed=false", [1]),
        ("?tag=work&q=archive", [5]),
    ],
)
def test_filters(client, seeded, query, expected):
    assert ids(client, query) == expected


@pytest.mark.parametrize(
    "query, expected",
    [
        ("?sort=title", [5, 2, 4, 1, 3]),            # case-insensitive
        ("?sort=title&order=desc", [3, 1, 4, 2, 5]),
        ("?sort=priority", [4, 5, 2, 1, 3]),         # low < medium < high, ties by id
        ("?sort=priority&order=desc", [3, 1, 2, 5, 4]),
        ("?sort=due_date", [4, 1, 3, 2, 5]),         # undated last
        ("?sort=due_date&order=desc", [5, 2, 3, 1, 4]),  # undated first
    ],
)
def test_sorting(client, seeded, query, expected):
    assert ids(client, query) == expected


def test_pagination(client, seeded):
    page = client.get("/todos?limit=2&offset=0").json()
    assert [t["id"] for t in page["items"]] == [1, 2]
    assert page["total"] == 5
    assert ids(client, "?limit=2&offset=2") == [3, 4]
    assert ids(client, "?limit=2&offset=4") == [5]
    assert ids(client, "?limit=2&offset=10") == []


def test_total_counts_all_matches_not_page(client, seeded):
    page = client.get("/todos?completed=false&limit=1").json()
    assert page["total"] == 4
    assert len(page["items"]) == 1
