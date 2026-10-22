# Todo CLI

A small, fast task list for your terminal, written in pure Python (standard library only). Tasks have **priorities**, **due dates** (with friendly shortcuts like `tomorrow`, `+3d` or `fri`), and **tags**, and they're stored in a human-readable **JSON** file.

```
$ todo add Write report -p high -d tomorrow -t work
Added task 1: Write report
$ todo add Buy milk -d 2026-10-20
Added task 2: Buy milk
$ todo add Read a book -p low
Added task 3: Read a book
$ todo
  2  [ ] !!  Buy milk  (due 2026-10-20, 2d overdue)
  1  [ ] !!! Write report  #work  (due 2026-10-23, tomorrow)
  3  [ ] !   Read a book

3 open, 0 done, 1 overdue
$ todo done 2
Completed task 2: Buy milk
```

In a real terminal, overdue dates show in red, high priority in red, today's tasks in yellow and finished tasks dimmed. Colour turns off automatically when output is piped, or with `--no-color` or `NO_COLOR=1`.

## Key CS concepts

| Concept | Where |
|---|---|
| **Data modelling** with dataclasses and an `IntEnum` that sorts by value | `models.py` |
| **Serialisation**: a versioned JSON format with validation on load | `models.py`, `storage.py` |
| **Atomic file writes**: write to a temp file, `fsync`, then `os.replace`, so a crash can't corrupt your data | `storage.py` |
| **Composite sort keys**: tuple keys give multi-level ordering (overdue → priority → due → id) | `models.sort_key` |
| **Parsing**: a small hand-written grammar for relative dates, using regex plus modular weekday arithmetic | `dates.py` |
| **Command dispatch** with argparse sub-commands, aliases and custom type converters | `cli.py` |
| **Decorators** to share "look up each ID, report missing ones" logic | `cli._with_task` |
| **Sentinel objects** to tell "flag not given" apart from "flag set to none" | `cli._UNSET` |
| **Dependency injection** for testability: `main()` takes `out` and `today` | `cli.main` |
| **Monotonic IDs**: IDs are never reused, so a stale ID can't hit the wrong task | `storage.TaskStore` |

## Project layout

```
003-todo-cli/
├── pyproject.toml        # packaging + `todo` console script + pytest config
├── Makefile
├── src/todo_cli/
│   ├── __init__.py
│   ├── __main__.py       # python -m todo_cli
│   ├── models.py         # Task, Priority, sort keys
│   ├── dates.py          # due-date parsing / "in 3d" descriptions
│   ├── storage.py        # JSON TaskStore with atomic saves
│   └── cli.py            # argparse commands and output formatting
└── tests/                # 57 pytest tests (unit + end-to-end CLI)
```

## Build, run, test

Requires Python 3.10+.

```bash
# Run straight from source
make run ARGS="add Hello world"
PYTHONPATH=src python3 -m todo_cli list

# Install the `todo` command
pip install .            # or: make install

# Tests
pip install pytest
make test                # or: python3 -m pytest
```

## Commands

| Command | Description |
|---|---|
| `todo add TITLE… [-p low/medium/high] [-d DUE] [-t TAG]…` | Add a task |
| `todo` / `todo list` / `todo ls` | Show open tasks |
| `  -a/--all`, `-p PRIO`, `-o/--overdue`, `-t TAG`, `-s TEXT`, `--sort smart/priority/due/created` | List filters and sort order |
| `todo done ID…` (alias `do`) | Mark task(s) done |
| `todo undo ID…` | Reopen task(s) |
| `todo edit ID [NEW TITLE…] [-p] [-d] [-t TAG] [-u TAG]` | Change a task (`-d none` clears the due date) |
| `todo rm ID…` | Delete task(s) |
| `todo clear` | Delete all completed tasks |

**Due-date formats:** `2026-11-05`, `today`, `tomorrow`, `+3d`, `+2w`, `mon` to `sun` (or full names; always the *next* occurrence), and `none`.

**Data file:** `~/.todo.json` by default. You can override it with `$TODO_FILE` or `--file PATH`, which is handy for keeping a separate list in each project.

```json
{
  "version": 1,
  "next_id": 4,
  "tasks": [
    {"id": 1, "title": "Write report", "priority": "high", "due": "2026-10-23",
     "done": false, "created": "2026-10-22T09:15:00", "completed": null, "tags": ["work"]}
  ]
}
```

**Exit codes:** `0` means success, `1` means an unknown ID or nothing to edit, and `2` means a usage error or an unreadable data file.

## Possible extensions

- Recurring tasks (`--every week`) that spawn the next instance when completed
- Sub-tasks and dependencies, with topological ordering
- An SQLite backend behind the same `TaskStore` interface
- A `todo stats` command (completion streaks, average lateness)
- Export to and import from iCalendar `VTODO` or Markdown checklists
- A file lock so two shells editing the same list concurrently can't race
- Fuzzy search, or a TUI built with `curses`
