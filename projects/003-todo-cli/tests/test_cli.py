"""End-to-end tests that drive main() exactly like the shell would."""

import io
import json
from datetime import date

import pytest

from todo_cli.cli import main

TODAY = date(2026, 10, 22)


@pytest.fixture
def todo(tmp_path):
    path = tmp_path / "todo.json"

    def run(*argv):
        out = io.StringIO()
        code = main(["--file", str(path), "--no-color", *argv], out=out, today=TODAY)
        return code, out.getvalue()

    run.path = path
    return run


def test_empty_list(todo):
    code, out = todo()
    assert code == 0 and "Nothing to do" in out
    assert not todo.path.exists()  # read-only commands don't create the file


def test_add_and_list(todo):
    todo("add", "Write", "report", "-p", "high", "-d", "tomorrow", "-t", "work")
    todo("add", "Buy milk", "-d", "2026-10-20")
    code, out = todo("list")
    lines = out.splitlines()
    assert code == 0
    assert "Buy milk" in lines[0] and "2d overdue" in lines[0]       # overdue first
    assert "Write report" in lines[1] and "#work" in lines[1] and "tomorrow" in lines[1]
    assert "2 open, 0 done, 1 overdue" in out


def test_done_hides_task_unless_all(todo):
    todo("add", "a")
    todo("add", "b")
    todo("done", "1")
    assert "a" not in todo("ls")[1].split("\n")[0]
    _, out = todo("ls", "--all")
    assert "[x]" in out and "1 open, 1 done" in out


def test_unknown_id_returns_error(todo, capsys):
    todo("add", "a")
    code, _ = todo("done", "1", "99")
    assert code == 1
    assert "no task with id 99" in capsys.readouterr().err
    assert json.loads(todo.path.read_text())["tasks"][0]["done"] is True  # valid id still applied


def test_filters(todo):
    todo("add", "alpha", "-p", "low", "-t", "home")
    todo("add", "beta", "-p", "high")
    todo("add", "gamma", "-d", "+0d")
    assert "beta" in todo("ls", "-p", "high")[1] and "alpha" not in todo("ls", "-p", "high")[1]
    assert "alpha" in todo("ls", "-t", "home")[1] and "beta" not in todo("ls", "-t", "home")[1]
    assert "gamma" in todo("ls", "-s", "GAM")[1]
    assert "No matching tasks" in todo("ls", "--overdue")[1]


def test_edit(todo):
    todo("add", "old", "-d", "today", "-t", "x")
    code, out = todo("edit", "1", "new", "title", "-p", "high", "-d", "none", "-u", "x", "-t", "y")
    assert code == 0
    task = json.loads(todo.path.read_text())["tasks"][0]
    assert task["title"] == "new title" and task["priority"] == "high"
    assert task["due"] is None and task["tags"] == ["y"]


def test_edit_with_no_changes(todo):
    todo("add", "a")
    assert todo("edit", "1")[0] == 1


def test_undo_remove_clear(todo):
    for t in "abc":
        todo("add", t)
    todo("done", "1", "2")
    todo("undo", "2")
    todo("rm", "3")
    _, out = todo("clear")
    assert "Cleared 1" in out
    titles = [t["title"] for t in json.loads(todo.path.read_text())["tasks"]]
    assert titles == ["b"]


def test_bad_due_date_is_a_usage_error(todo):
    with pytest.raises(SystemExit) as exc:
        todo("add", "x", "-d", "someday")
    assert exc.value.code == 2


def test_corrupt_file_reports_error(todo, capsys):
    todo.path.write_text("{oops")
    assert todo("ls")[0] == 2
    assert "not valid JSON" in capsys.readouterr().err


def test_env_var_selects_file(tmp_path, monkeypatch):
    path = tmp_path / "env.json"
    monkeypatch.setenv("TODO_FILE", str(path))
    main(["add", "from env"], out=io.StringIO(), today=TODAY)
    assert "from env" in path.read_text()
