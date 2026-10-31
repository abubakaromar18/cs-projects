"""Create / read / update / delete behaviour and status codes."""


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_create_returns_201_with_location_and_defaults(client):
    r = client.post("/todos", json={"title": "  Buy milk  "})
    assert r.status_code == 201
    body = r.json()
    assert r.headers["location"] == f"/todos/{body['id']}"
    assert body["title"] == "Buy milk"  # whitespace trimmed
    assert body["priority"] == "medium"
    assert body["completed"] is False
    assert body["tags"] == []
    assert body["notes"] == ""
    assert body["due_date"] is None
    assert body["created_at"] == body["updated_at"]


def test_ids_increase(make):
    assert [make()["id"] for _ in range(3)] == [1, 2, 3]


def test_get_one(client, make):
    todo = make(title="Read", priority="high", due_date="2026-12-01", tags=["Home", "home", "x"])
    r = client.get(f"/todos/{todo['id']}")
    assert r.status_code == 200
    assert r.json() == todo
    assert todo["tags"] == ["home", "x"]  # lower-cased and de-duplicated


def test_get_missing_is_404(client):
    r = client.get("/todos/999")
    assert r.status_code == 404
    assert r.json() == {"detail": "Todo 999 not found"}


def test_patch_changes_only_sent_fields(client, make):
    todo = make(title="Old", notes="keep me", priority="low")
    r = client.patch(f"/todos/{todo['id']}", json={"completed": True})
    assert r.status_code == 200
    body = r.json()
    assert body["completed"] is True
    assert body["title"] == "Old"
    assert body["notes"] == "keep me"
    assert body["priority"] == "low"
    assert body["updated_at"] > todo["updated_at"]
    assert body["created_at"] == todo["created_at"]


def test_patch_null_due_date_clears_it(client, make):
    todo = make(due_date="2026-12-24")
    r = client.patch(f"/todos/{todo['id']}", json={"due_date": None})
    assert r.json()["due_date"] is None


def test_patch_null_title_rejected(client, make):
    todo = make()
    assert client.patch(f"/todos/{todo['id']}", json={"title": None}).status_code == 422


def test_empty_patch_is_noop(client, make):
    todo = make()
    r = client.patch(f"/todos/{todo['id']}", json={})
    assert r.status_code == 200
    assert r.json() == todo


def test_patch_missing_is_404(client):
    assert client.patch("/todos/5", json={"completed": True}).status_code == 404
    assert client.patch("/todos/5", json={}).status_code == 404


def test_put_replaces_everything(client, make):
    todo = make(title="A", notes="n", tags=["t"], priority="high", due_date="2026-12-01")
    r = client.put(f"/todos/{todo['id']}", json={"title": "B"})
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "B"
    assert body["notes"] == ""          # reset to default
    assert body["tags"] == []
    assert body["priority"] == "medium"
    assert body["due_date"] is None


def test_put_missing_is_404(client):
    assert client.put("/todos/1", json={"title": "x"}).status_code == 404


def test_delete(client, make):
    todo = make()
    r = client.delete(f"/todos/{todo['id']}")
    assert r.status_code == 204
    assert r.content == b""
    assert client.get(f"/todos/{todo['id']}").status_code == 404
    assert client.delete(f"/todos/{todo['id']}").status_code == 404


def test_ids_not_reused_after_delete(client, make):
    first = make()
    client.delete(f"/todos/{first['id']}")
    assert make()["id"] == first["id"] + 1


def test_clear_completed(client, make):
    make(title="a", completed=True)
    keep = make(title="b")
    make(title="c", completed=True)
    r = client.post("/todos/clear-completed")
    assert r.json() == {"deleted": 2}
    items = client.get("/todos").json()["items"]
    assert [t["id"] for t in items] == [keep["id"]]


def test_stats(client, make):
    make(priority="high", due_date="2026-10-01")                  # overdue
    make(priority="high", due_date="2026-10-01", completed=True)  # done, not overdue
    make(priority="low", due_date="2026-11-01")                   # due today, not overdue
    make()
    r = client.get("/todos/stats")
    assert r.json() == {
        "total": 4, "completed": 1, "open": 3, "overdue": 1,
        "by_priority": {"low": 1, "medium": 1, "high": 2},
    }
