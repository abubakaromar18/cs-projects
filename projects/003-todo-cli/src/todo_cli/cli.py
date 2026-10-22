"""Command-line interface (argparse sub-commands).

Every command is a small function ``cmd_<name>(store, args, out) -> int`` that
returns a process exit code. ``main()`` wires argparse to those functions, loads
the store, and saves it only if the command changed something. Keeping output
going through an ``out`` stream makes the whole CLI easy to test.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from typing import Callable, TextIO

from . import __version__
from .dates import describe_due, parse_due
from .models import Priority, Task, sort_key
from .storage import StorageError, TaskStore, default_path

# ---- presentation ---------------------------------------------------------

_ANSI = {
    "reset": "\033[0m", "dim": "\033[2m", "bold": "\033[1m",
    "red": "\033[31m", "yellow": "\033[33m", "green": "\033[32m", "cyan": "\033[36m",
}
_PRIORITY_MARK = {Priority.HIGH: "!!!", Priority.MEDIUM: "!! ", Priority.LOW: "!  "}
_PRIORITY_COLOR = {Priority.HIGH: "red", Priority.MEDIUM: "yellow", Priority.LOW: "cyan"}


class Painter:
    """Wraps text in ANSI colours, or is a no-op when colour is disabled."""

    def __init__(self, enabled: bool):
        self.enabled = enabled

    def __call__(self, text: str, *styles: str) -> str:
        if not self.enabled or not styles:
            return text
        return "".join(_ANSI[s] for s in styles) + text + _ANSI["reset"]


def format_task(task: Task, paint: Painter, today: date) -> str:
    """Render one task as a single aligned line."""
    box = paint("[x]", "green") if task.done else "[ ]"
    prio = paint(_PRIORITY_MARK[task.priority], _PRIORITY_COLOR[task.priority])
    title = paint(task.title, "dim") if task.done else task.title
    parts = [f"{task.id:>3}  {box} {prio} {title}"]

    if task.tags:
        parts.append(paint(" ".join(f"#{t}" for t in task.tags), "cyan"))
    if task.due:
        if task.done:
            # Relative wording ("3d overdue") is meaningless for finished work.
            due_txt = f"(due {task.due.isoformat()})"
        else:
            due_txt = f"(due {task.due.isoformat()}, {describe_due(task.due, today)})"
        if task.is_overdue(today):
            due_txt = paint(due_txt, "red", "bold")
        elif not task.done and task.due == today:
            due_txt = paint(due_txt, "yellow")
        else:
            due_txt = paint(due_txt, "dim")
        parts.append(due_txt)
    return "  ".join(parts)


# ---- commands -------------------------------------------------------------

def cmd_add(store: TaskStore, args, out: TextIO) -> int:
    task = store.add(
        " ".join(args.title),
        priority=args.priority,
        due=args.due,
        tags=args.tag or [],
    )
    print(f"Added task {task.id}: {task.title}", file=out)
    return 0


def cmd_list(store: TaskStore, args, out: TextIO) -> int:
    today = args.today
    tasks = list(store.tasks)

    if not args.all:
        tasks = [t for t in tasks if not t.done]
    if args.priority is not None:
        tasks = [t for t in tasks if t.priority == args.priority]
    if args.overdue:
        tasks = [t for t in tasks if t.is_overdue(today)]
    if args.tag:
        tasks = [t for t in tasks if args.tag in t.tags]
    if args.search:
        needle = args.search.lower()
        tasks = [t for t in tasks if needle in t.title.lower()]

    tasks.sort(key=sort_key(args.sort, today))

    if not tasks:
        print("Nothing to do!" if not store.tasks else "No matching tasks.", file=out)
        return 0

    for t in tasks:
        print(format_task(t, args.paint, today), file=out)

    open_count = sum(1 for t in store.tasks if not t.done)
    overdue = sum(1 for t in store.tasks if t.is_overdue(today))
    summary = f"\n{open_count} open, {len(store.tasks) - open_count} done"
    if overdue:
        summary += f", {overdue} overdue"
    print(args.paint(summary, "dim"), file=out)
    return 0


def _with_task(fn: Callable[[Task, argparse.Namespace, TextIO], None]):
    """Decorator: resolve every ``args.ids`` to a Task, reporting unknown IDs."""

    def wrapper(store: TaskStore, args, out: TextIO) -> int:
        status = 0
        for task_id in args.ids:
            try:
                task = store.get(task_id)
            except KeyError as exc:
                print(f"error: {exc.args[0]}", file=sys.stderr)
                status = 1
                continue
            fn(store, task, args, out)
        return status

    return wrapper


@_with_task
def cmd_done(store, task: Task, args, out) -> None:
    if task.done:
        print(f"Task {task.id} was already done.", file=out)
    else:
        task.mark_done()
        print(f"Completed task {task.id}: {task.title}", file=out)


@_with_task
def cmd_undo(store, task: Task, args, out) -> None:
    task.mark_undone()
    print(f"Reopened task {task.id}: {task.title}", file=out)


@_with_task
def cmd_remove(store, task: Task, args, out) -> None:
    store.remove(task.id)
    print(f"Removed task {task.id}: {task.title}", file=out)


def cmd_edit(store: TaskStore, args, out: TextIO) -> int:
    try:
        task = store.get(args.id)
    except KeyError as exc:
        print(f"error: {exc.args[0]}", file=sys.stderr)
        return 1

    changed = []
    if args.title:
        task.title = " ".join(args.title).strip() or task.title
        changed.append("title")
    if args.priority is not None:
        task.priority = args.priority
        changed.append("priority")
    if args.due is not _UNSET:
        task.due = args.due
        changed.append("due")
    if args.tag:
        task.tags = sorted(set(task.tags) | set(args.tag))
        changed.append("tags")
    if args.untag:
        task.tags = [t for t in task.tags if t not in args.untag]
        changed.append("tags")

    if not changed:
        print("Nothing to change (see `todo edit --help`).", file=out)
        return 1
    print(f"Updated task {task.id} ({', '.join(dict.fromkeys(changed))}).", file=out)
    return 0


def cmd_clear(store: TaskStore, args, out: TextIO) -> int:
    removed = store.clear_done()
    print(f"Cleared {len(removed)} completed task(s).", file=out)
    return 0


# Commands that never modify the store (so we skip saving).
_READ_ONLY = {"list"}

# ---- argument parsing -----------------------------------------------------

_UNSET = object()  # sentinel: distinguishes "--due not given" from "--due none"


def _priority(text: str) -> Priority:
    try:
        return Priority.parse(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def _due_parser(today: date):
    def parse(text: str):
        try:
            return parse_due(text, today)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(str(exc)) from None
    return parse


def build_parser(today: date) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="todo",
        description="A small, fast task list for your terminal.",
        epilog="Data lives in $TODO_FILE or ~/.todo.json.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("-f", "--file", help="path to the JSON data file")
    p.add_argument("--no-color", action="store_true", help="disable coloured output")
    sub = p.add_subparsers(dest="command", metavar="COMMAND")

    due_help = "due date: YYYY-MM-DD, today, tomorrow, +3d, +2w, fri, or none"

    a = sub.add_parser("add", help="add a new task")
    a.add_argument("title", nargs="+", help="task description")
    a.add_argument("-p", "--priority", type=_priority, default=Priority.MEDIUM,
                   help="low, medium (default) or high")
    a.add_argument("-d", "--due", type=_due_parser(today), help=due_help)
    a.add_argument("-t", "--tag", action="append", help="add a tag (repeatable)")
    a.set_defaults(func=cmd_add)

    ls = sub.add_parser("list", aliases=["ls"], help="show tasks")
    ls.add_argument("-a", "--all", action="store_true", help="include completed tasks")
    ls.add_argument("-p", "--priority", type=_priority, help="only this priority")
    ls.add_argument("-o", "--overdue", action="store_true", help="only overdue tasks")
    ls.add_argument("-t", "--tag", help="only tasks with this tag")
    ls.add_argument("-s", "--search", help="case-insensitive text search")
    ls.add_argument("--sort", choices=["smart", "priority", "due", "created"], default="smart")
    ls.set_defaults(func=cmd_list, command="list")

    for name, fn, helptext, aliases in [
        ("done", cmd_done, "mark task(s) as done", ["do"]),
        ("undo", cmd_undo, "reopen completed task(s)", []),
        ("remove", cmd_remove, "delete task(s)", ["rm"]),
    ]:
        sp = sub.add_parser(name, aliases=aliases, help=helptext)
        sp.add_argument("ids", nargs="+", type=int, metavar="ID")
        sp.set_defaults(func=fn, command=name)

    e = sub.add_parser("edit", help="change a task")
    e.add_argument("id", type=int)
    e.add_argument("title", nargs="*", help="new title (optional)")
    e.add_argument("-p", "--priority", type=_priority)
    e.add_argument("-d", "--due", type=_due_parser(today), default=_UNSET, help=due_help)
    e.add_argument("-t", "--tag", action="append", help="add a tag")
    e.add_argument("-u", "--untag", action="append", help="remove a tag")
    e.set_defaults(func=cmd_edit)

    c = sub.add_parser("clear", help="delete all completed tasks")
    c.set_defaults(func=cmd_clear)
    return p


def _use_color(args, stream: TextIO) -> bool:
    if args.no_color or os.environ.get("NO_COLOR"):  # https://no-color.org
        return False
    return hasattr(stream, "isatty") and stream.isatty()


def main(argv: list[str] | None = None, out: TextIO | None = None, today: date | None = None) -> int:
    """Entry point. ``out`` and ``today`` are injectable for testing."""
    out = out or sys.stdout
    argv = sys.argv[1:] if argv is None else list(argv)
    today = today or date.today()
    parser = build_parser(today)
    args = parser.parse_args(argv)

    # Bare `todo` behaves like `todo list`.
    if args.command is None:
        args = parser.parse_args([*argv, "list"])

    args.today = today
    args.paint = Painter(_use_color(args, out))

    path = default_path() if args.file is None else os.path.expanduser(args.file)
    try:
        store = TaskStore.load(path)
    except StorageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        code = args.func(store, args, out)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.command not in _READ_ONLY:
        store.save()
    return code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
