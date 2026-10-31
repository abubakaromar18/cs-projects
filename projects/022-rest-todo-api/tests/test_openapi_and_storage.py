"""OpenAPI document, SQLite persistence and the default repository choice."""

from fastapi.testclient import TestClient

from todo_api.main import create_app, default_repository
from todo_api.repository import InMemoryTodoRepository, SqliteTodoRepository
from todo_api.schemas import TodoCreate


def test_openapi_schema_documents_all_routes(client):
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "REST Todo API"
    paths = spec["paths"]
    assert set(paths["/todos"]) == {"get", "post"}
    assert set(paths["/todos/{todo_id}"]) == {"get", "put", "patch", "delete"}
    assert "404" in paths["/todos/{todo_id}"]["get"]["responses"]
    assert "422" in paths["/todos"]["post"]["responses"]
    schemas = spec["components"]["schemas"]
    assert {"Todo", "TodoCreate", "TodoUpdate", "TodoPage", "Stats", "Priority"} <= set(schemas)
    # The create model must not let clients set server-owned fields.
    assert "id" not in schemas["TodoCreate"]["properties"]
    assert schemas["TodoCreate"]["required"] == ["title"]


def test_swagger_ui_served(client):
    r = client.get("/docs")
    assert r.status_code == 200
    assert "swagger" in r.text.lower()


def test_sqlite_persists_across_instances(tmp_path):
    db = str(tmp_path / "todos.db")
    first = SqliteTodoRepository(db)
    created = first.create(TodoCreate(title="survive restart", tags=["a"]))

    second = SqliteTodoRepository(db)
    assert second.get(created.id) == created

    app = create_app(repository=second)
    with TestClient(app) as c:
        assert c.get("/todos").json()["total"] == 1


def test_default_repository_respects_env(monkeypatch, tmp_path):
    monkeypatch.delenv("TODO_DB_PATH", raising=False)
    assert isinstance(default_repository(), InMemoryTodoRepository)
    monkeypatch.setenv("TODO_DB_PATH", str(tmp_path / "x.db"))
    assert isinstance(default_repository(), SqliteTodoRepository)


def test_apps_do_not_share_state():
    a, b = TestClient(create_app(InMemoryTodoRepository())), TestClient(create_app(InMemoryTodoRepository()))
    a.post("/todos", json={"title": "only in a"})
    assert b.get("/todos").json()["total"] == 0
