import json

import pytest

from todo_cli.models import Priority
from todo_cli.storage import StorageError, TaskStore


def test_missing_file_gives_empty_store(tmp_path):
    store = TaskStore.load(tmp_path / "none.json")
    assert store.tasks == [] and store.next_id == 1


def test_save_and_reload(tmp_path):
    path = tmp_path / "todo.json"
    store = TaskStore.load(path)
    store.add("one", priority=Priority.HIGH, tags=["x"])
    store.add("two")
    store.save()

    again = TaskStore.load(path)
    assert [t.title for t in again.tasks] == ["one", "two"]
    assert again.tasks[0].priority is Priority.HIGH
    assert again.next_id == 3
    assert json.loads(path.read_text())["version"] == 1


def test_ids_are_never_reused(tmp_path):
    store = TaskStore(tmp_path / "t.json")
    store.add("a")
    b = store.add("b")
    store.remove(b.id)
    assert store.add("c").id == 3


def test_save_leaves_no_temp_files(tmp_path):
    store = TaskStore(tmp_path / "t.json")
    store.add("a")
    store.save()
    assert [p.name for p in tmp_path.iterdir()] == ["t.json"]


def test_empty_title_rejected(tmp_path):
    with pytest.raises(ValueError):
        TaskStore(tmp_path / "t.json").add("   ")


def test_get_unknown_id(tmp_path):
    with pytest.raises(KeyError):
        TaskStore(tmp_path / "t.json").get(42)


def test_clear_done(tmp_path):
    store = TaskStore(tmp_path / "t.json")
    store.add("a")
    store.add("b").mark_done()
    removed = store.clear_done()
    assert [t.title for t in removed] == ["b"]
    assert [t.title for t in store.tasks] == ["a"]


@pytest.mark.parametrize("content", ["{not json", "[]", '{"version": 99, "tasks": []}',
                                     '{"tasks": [{"id": 1}]}'])
def test_corrupt_files_raise_storage_error(tmp_path, content):
    path = tmp_path / "bad.json"
    path.write_text(content)
    with pytest.raises(StorageError):
        TaskStore.load(path)


def test_next_id_recovers_if_file_was_hand_edited(tmp_path):
    path = tmp_path / "t.json"
    path.write_text(json.dumps({"version": 1, "next_id": 1, "tasks": [
        {"id": 5, "title": "x", "created": "2026-10-01T00:00:00"}]}))
    assert TaskStore.load(path).add("y").id == 6
