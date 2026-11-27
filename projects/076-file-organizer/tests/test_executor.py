import json

from fileorg.executor import apply_plan, undo
from fileorg.planner import JOURNAL_NAME, plan_moves

from conftest import tree


def test_dry_run_changes_nothing(make_files):
    root = make_files({"a.jpg": None, "b.pdf": None})
    result = apply_plan(plan_moves(root), dry_run=True)
    assert result.moved == 0
    assert tree(root) == {"a.jpg", "b.pdf"}
    assert not (root / JOURNAL_NAME).exists()


def test_apply_moves_files_and_preserves_content(make_files):
    root = make_files({"a.jpg": None, "b.pdf": None})
    result = apply_plan(plan_moves(root))
    assert result.moved == 2 and not result.errors
    assert tree(root) == {"Images/a.jpg", "Documents/b.pdf"}
    assert (root / "Images/a.jpg").read_text() == "content of a.jpg"


def test_second_run_is_noop(make_files):
    root = make_files({"a.jpg": None})
    apply_plan(plan_moves(root))
    assert plan_moves(root).moves == []
    assert plan_moves(root, recursive=True).moves == []


def test_undo_restores_original_layout(make_files):
    spec = {"a.jpg": None, "sub/b.pdf": None, "sub/deeper/c.mp3": None}
    root = make_files(spec)
    apply_plan(plan_moves(root, recursive=True))
    assert tree(root) == {"Images/a.jpg", "Documents/b.pdf", "Audio/c.mp3"}
    # Emptied source folders are cleaned up.
    assert not (root / "sub").exists()

    result = undo(root)
    assert result.moved == 3 and not result.errors
    assert tree(root) == set(spec)
    assert not (root / "Images").exists()
    assert not (root / JOURNAL_NAME).exists()


def test_undo_only_reverts_latest_run(make_files):
    root = make_files({"a.jpg": None})
    apply_plan(plan_moves(root))
    (root / "b.pdf").write_text("later")
    apply_plan(plan_moves(root))
    undo(root)
    assert tree(root) == {"Images/a.jpg", "b.pdf"}
    undo(root)
    assert tree(root) == {"a.jpg", "b.pdf"}


def test_undo_with_nothing_recorded(tmp_path):
    result = undo(tmp_path)
    assert result.moved == 0 and not result.errors


def test_never_overwrites_file_created_after_planning(make_files):
    root = make_files({"a.jpg": None})
    plan = plan_moves(root)
    (root / "Images").mkdir()
    (root / "Images/a.jpg").write_text("precious")
    result = apply_plan(plan)
    assert result.moved == 0 and len(result.errors) == 1
    assert (root / "Images/a.jpg").read_text() == "precious"
    assert (root / "a.jpg").exists()


def test_undo_refuses_to_clobber_and_keeps_entry(make_files):
    root = make_files({"a.jpg": None})
    apply_plan(plan_moves(root))
    (root / "a.jpg").write_text("new file in the way")
    result = undo(root)
    assert result.moved == 0 and len(result.errors) == 1
    history = json.loads((root / JOURNAL_NAME).read_text())
    assert history[-1]["moves"] == [{"src": "a.jpg", "dst": "Images/a.jpg"}]
