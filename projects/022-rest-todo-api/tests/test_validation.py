"""Request validation: bad input must be a 422 with a useful location, never a 500."""

import pytest


def _error_locs(response):
    return [tuple(e["loc"]) for e in response.json()["detail"]]


@pytest.mark.parametrize(
    "payload, field",
    [
        ({}, "title"),
        ({"title": ""}, "title"),
        ({"title": "    "}, "title"),
        ({"title": "x" * 201}, "title"),
        ({"title": "ok", "priority": "urgent"}, "priority"),
        ({"title": "ok", "due_date": "next tuesday"}, "due_date"),
        ({"title": "ok", "due_date": "2026-02-30"}, "due_date"),
        ({"title": "ok", "completed": "maybe"}, "completed"),
        ({"title": "ok", "notes": "n" * 2001}, "notes"),
        ({"title": "ok", "tags": "work"}, "tags"),
        ({"title": "ok", "tags": ["has space"]}, "tags"),
        ({"title": "ok", "tags": [f"t{i}" for i in range(11)]}, "tags"),
        ({"title": "ok", "id": 7}, "id"),  # server-owned / unknown fields are rejected
    ],
)
def test_create_rejects_invalid(client, payload, field):
    r = client.post("/todos", json=payload)
    assert r.status_code == 422
    assert any(loc[:2] == ("body", field) for loc in _error_locs(r)), r.json()


def test_title_at_max_length_accepted(client):
    assert client.post("/todos", json={"title": "x" * 200}).status_code == 201


def test_non_json_body_rejected(client):
    r = client.post("/todos", content="title=x", headers={"content-type": "text/plain"})
    assert r.status_code == 422


def test_patch_rejects_unknown_fields(client, make):
    todo = make()
    r = client.patch(f"/todos/{todo['id']}", json={"created_at": "2020-01-01T00:00:00Z"})
    assert r.status_code == 422


def test_non_integer_id_is_422(client):
    assert client.get("/todos/abc").status_code == 422


@pytest.mark.parametrize(
    "query",
    ["limit=0", "limit=101", "offset=-1", "sort=color", "order=sideways",
     "priority=urgent", "due_before=soon", "completed=perhaps", "q="],
)
def test_list_rejects_bad_query_params(client, query):
    assert client.get(f"/todos?{query}").status_code == 422
