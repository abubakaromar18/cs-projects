"""Run the API with ``python -m todo_api`` (host/port via HOST and PORT env vars)."""

import os

import uvicorn


def main() -> None:
    uvicorn.run("todo_api.main:app", host=os.environ.get("HOST", "127.0.0.1"),
                port=int(os.environ.get("PORT", "8000")), reload=False)


if __name__ == "__main__":
    main()
