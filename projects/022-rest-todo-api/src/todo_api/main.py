"""HTTP layer: routes, status codes and dependency wiring.

``create_app`` is an application factory: tests build a fresh app with a fresh
repository (and a fixed clock) for every test, so no state leaks between them.
"""

import os
from datetime import date
from typing import Annotated, Callable

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status

from . import __version__
from .repository import (
    InMemoryTodoRepository,
    SqliteTodoRepository,
    TodoQuery,
    TodoRepository,
)
from .schemas import Priority, SortField, Stats, Todo, TodoCreate, TodoPage, TodoUpdate

NOT_FOUND = {404: {"description": "Todo not found",
                   "content": {"application/json": {"example": {"detail": "Todo 42 not found"}}}}}


def default_repository() -> TodoRepository:
    """Use SQLite if ``TODO_DB_PATH`` is set, otherwise keep everything in memory."""
    path = os.environ.get("TODO_DB_PATH")
    return SqliteTodoRepository(path) if path else InMemoryTodoRepository()


def create_app(
    repository: TodoRepository | None = None,
    today: Callable[[], date] = date.today,
) -> FastAPI:
    app = FastAPI(
        title="REST Todo API",
        version=__version__,
        description="A small CRUD API with validation, filtering, pagination and stats. "
                    "Interactive docs live at `/docs` (Swagger UI) and `/redoc`.",
        openapi_tags=[
            {"name": "todos", "description": "Create, read, update and delete todos."},
            {"name": "meta", "description": "Health and service information."},
        ],
    )
    app.state.repo = repository or default_repository()

    # Dependency: routes ask for a repository instead of reaching for a global.
    def get_repo(request: Request) -> TodoRepository:
        return request.app.state.repo

    Repo = Annotated[TodoRepository, Depends(get_repo)]

    def get_or_404(repo: TodoRepository, todo_id: int) -> Todo:
        todo = repo.get(todo_id)
        if todo is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Todo {todo_id} not found")
        return todo

    # ------------------------------------------------------------------ meta

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    # ------------------------------------------------------------------ collection

    @app.get("/todos", response_model=TodoPage, tags=["todos"], summary="List todos")
    def list_todos(
        repo: Repo,
        completed: bool | None = None,
        priority: Priority | None = None,
        tag: Annotated[str | None, Query(max_length=30)] = None,
        q: Annotated[str | None, Query(min_length=1, max_length=100,
                                       description="Search title and notes")] = None,
        due_before: Annotated[date | None, Query(description="Due on or before (inclusive)")] = None,
        sort: SortField = SortField.created_at,
        order: Annotated[str, Query(pattern="^(asc|desc)$")] = "asc",
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> TodoPage:
        query = TodoQuery(completed=completed, priority=priority, tag=tag, search=q,
                          due_before=due_before, sort=sort, descending=order == "desc",
                          limit=limit, offset=offset)
        items, total = repo.list(query)
        return TodoPage(items=items, total=total, limit=limit, offset=offset)

    @app.post("/todos", response_model=Todo, status_code=status.HTTP_201_CREATED,
              tags=["todos"], summary="Create a todo")
    def create_todo(body: TodoCreate, repo: Repo, response: Response) -> Todo:
        todo = repo.create(body)
        response.headers["Location"] = f"/todos/{todo.id}"
        return todo

    @app.get("/todos/stats", response_model=Stats, tags=["todos"], summary="Summary counts")
    def todo_stats(repo: Repo) -> Stats:
        return repo.stats(today())

    @app.post("/todos/clear-completed", tags=["todos"], summary="Delete all completed todos")
    def clear_completed(repo: Repo) -> dict[str, int]:
        done = [t.id for t in repo.all() if t.completed]
        for todo_id in done:
            repo.delete(todo_id)
        return {"deleted": len(done)}

    # ------------------------------------------------------------------ item

    @app.get("/todos/{todo_id}", response_model=Todo, responses=NOT_FOUND,
             tags=["todos"], summary="Get one todo")
    def read_todo(todo_id: int, repo: Repo) -> Todo:
        return get_or_404(repo, todo_id)

    @app.put("/todos/{todo_id}", response_model=Todo, responses=NOT_FOUND,
             tags=["todos"], summary="Replace a todo")
    def replace_todo(todo_id: int, body: TodoCreate, repo: Repo) -> Todo:
        get_or_404(repo, todo_id)
        # PUT sends the whole resource, so every field is overwritten.
        return repo.update(todo_id, body.model_dump())  # type: ignore[return-value]

    @app.patch("/todos/{todo_id}", response_model=Todo, responses=NOT_FOUND,
               tags=["todos"], summary="Partially update a todo")
    def patch_todo(todo_id: int, body: TodoUpdate, repo: Repo) -> Todo:
        changes = body.model_dump(exclude_unset=True)
        if not changes:
            return get_or_404(repo, todo_id)
        updated = repo.update(todo_id, changes)
        if updated is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Todo {todo_id} not found")
        return updated

    @app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT,
                responses=NOT_FOUND, tags=["todos"], summary="Delete a todo")
    def delete_todo(todo_id: int, repo: Repo) -> Response:
        if not repo.delete(todo_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Todo {todo_id} not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


# Module-level app for ``uvicorn todo_api.main:app``.
app = create_app()
