# 022 · REST Todo API

A small but complete **REST API for todos** built with **FastAPI** and **Pydantic v2**.
It covers full CRUD with proper HTTP semantics, strict input validation, filtering,
search, sorting, pagination, summary stats, and auto-generated **OpenAPI** docs.

Storage sits behind a repository interface with two interchangeable backends:
an in-memory store (default) and **SQLite** (set `TODO_DB_PATH`). The whole test
suite runs against both.

## Endpoints

| Method | Path | Purpose | Success |
| --- | --- | --- | --- |
| `GET` | `/health` | Liveness check | 200 |
| `GET` | `/todos` | List with filters, search, sort, pagination | 200 |
| `POST` | `/todos` | Create (returns `Location` header) | 201 |
| `GET` | `/todos/{id}` | Fetch one | 200 / 404 |
| `PUT` | `/todos/{id}` | Replace the whole todo | 200 / 404 |
| `PATCH` | `/todos/{id}` | Change only the fields sent | 200 / 404 |
| `DELETE` | `/todos/{id}` | Delete | 204 / 404 |
| `GET` | `/todos/stats` | Totals, open/completed, overdue, by priority | 200 |
| `POST` | `/todos/clear-completed` | Delete every completed todo | 200 |

Invalid input always gets a **422** with the failing field's location. It never
causes a 500.

**List query parameters:** `completed`, `priority` (`low|medium|high`), `tag`,
`q` (case-insensitive search in title and notes), `due_before` (inclusive date),
`sort` (`created_at|due_date|priority|title`), `order` (`asc|desc`),
`limit` (1–100, default 20), `offset`.

**Todo fields:** `title` (1–200 chars, trimmed), `notes` (≤ 2000), `priority`
(default `medium`), `due_date` (ISO date or `null`), `tags` (≤ 10, lower-cased,
de-duplicated, `[a-z0-9_-]`), `completed`. The server owns `id`, `created_at` and
`updated_at`. Unknown fields are rejected, so a typo like `"complted"` fails
instead of being silently ignored.

## CS concepts demonstrated

- **REST resource design.** Collection vs. item URLs, the right verb for each
  operation, and the right status codes (201 + `Location`, 204 with an empty body, 404, 422).
- **PUT vs. PATCH semantics.** PUT replaces the resource, so omitted fields reset to
  defaults. PATCH uses `model_dump(exclude_unset=True)` to tell "field not sent" apart
  from "field sent as `null`". That lets `{"due_date": null}` clear a date while
  `{"title": null}` is rejected.
- **Validation at the boundary.** Separate input and output models (`TodoCreate`,
  `TodoUpdate`, `Todo`) mean clients can't set server-owned fields, and the
  OpenAPI schema documents each direction exactly.
- **Repository pattern and dependency injection.** Routes depend on an abstract
  `TodoRepository` through `Depends`. The app factory `create_app(repository, today)`
  lets tests inject a fresh store and a fixed clock.
- **SQL injection safety.** Every value is a bound parameter. `ORDER BY` columns
  can't be bound, so they come from a whitelist dict. Search uses `instr()` rather
  than `LIKE`, so `%` and `_` in user input are literal.
- **Stable sorting and pagination.** `id` breaks ties so pages never overlap or skip
  items. `total` counts all matches, not just the current page. Undated todos sort last
  (first when descending) in both backends.
- **Concurrency.** FastAPI runs sync endpoints in a thread pool, so both repositories
  guard shared state with a lock.
- **Contract testing.** Every API test is parametrised over both backends, which
  forces them to behave the same.

## Project layout

```
022-rest-todo-api/
├── src/todo_api/
│   ├── __init__.py      # version
│   ├── __main__.py      # `python -m todo_api` → uvicorn
│   ├── main.py          # app factory, routes, status codes
│   ├── schemas.py       # Pydantic request/response models and validation rules
│   └── repository.py    # TodoRepository ABC + in-memory and SQLite implementations
├── tests/               # 137 pytest cases (each API test runs on both backends)
├── pyproject.toml
└── Makefile
```

## Build, run and test

Requires Python 3.10+.

```bash
make install          # creates .venv and installs the package with dev extras
make test             # runs pytest
make run              # serves on http://127.0.0.1:8000
make openapi          # writes openapi.json
```

Without make:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m todo_api                         # in-memory storage
TODO_DB_PATH=todos.db python -m todo_api   # persistent SQLite storage
```

Open **http://127.0.0.1:8000/docs** for Swagger UI or `/redoc` for ReDoc. You can
try every endpoint from the browser.

## Example session

```console
$ curl -s -X POST localhost:8000/todos -H 'content-type: application/json' \
    -d '{"title":"Write report","priority":"high","due_date":"2026-11-15","tags":["work"]}'
{"id":1,"title":"Write report","notes":"","priority":"high","due_date":"2026-11-15",
 "tags":["work"],"completed":false,"created_at":"2026-10-31T13:45:03.630015Z",
 "updated_at":"2026-10-31T13:45:03.630015Z"}

$ curl -s 'localhost:8000/todos?priority=high&sort=due_date'
{"items":[{"id":1,"title":"Write report", ...}],"total":1,"limit":20,"offset":0}

$ curl -s -X PATCH localhost:8000/todos/1 -H 'content-type: application/json' -d '{"completed":true}'
{"id":1, ..., "completed":true, ...}

$ curl -s localhost:8000/todos/stats
{"total":1,"completed":1,"open":0,"overdue":0,"by_priority":{"low":0,"medium":0,"high":1}}

$ curl -s -X POST localhost:8000/todos -H 'content-type: application/json' -d '{"title":"   "}'
{"detail":[{"type":"string_too_short","loc":["body","title"],
  "msg":"String should have at least 1 character","input":"   ","ctx":{"min_length":1}}]}
```

## Possible extensions

- Users and authentication (OAuth2 password flow with JWTs), with each todo owned by a user.
- Swap the SQLite repository for SQLAlchemy/SQLModel and add Alembic migrations.
- Optimistic concurrency with `ETag` / `If-Match` so two clients can't overwrite each other.
- Cursor-based pagination for large datasets.
- Subtasks or projects as nested resources (`/projects/{id}/todos`).
- A Dockerfile and a GitHub Actions workflow that runs the tests.
- A small front end (for example project 021's React setup) that uses this API.
