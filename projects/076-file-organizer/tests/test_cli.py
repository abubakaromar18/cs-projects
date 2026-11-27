from fileorg.cli import main

from conftest import tree


def test_cli_dry_run(make_files, capsys):
    root = make_files({"a.jpg": None, "b.zip": None})
    assert main(["organize", str(root), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "a.jpg  ->  Images/a.jpg" in out
    assert "Dry run: would move 2 file(s) (Archives: 1, Images: 1)." in out
    assert tree(root) == {"a.jpg", "b.zip"}


def test_cli_organize_and_undo(make_files, capsys):
    root = make_files({"a.jpg": (2023, 7)})
    assert main(["organize", str(root), "--by", "type-date", "-q"]) == 0
    assert tree(root) == {"Images/2023/07/a.jpg"}
    assert "Moved 1 file(s)" in capsys.readouterr().out
    assert main(["undo", str(root)]) == 0
    assert tree(root) == {"a.jpg"}
    assert "Restored 1 file(s)." in capsys.readouterr().out


def test_cli_nothing_to_do(tmp_path, capsys):
    assert main(["organize", str(tmp_path)]) == 0
    assert "Nothing to organize." in capsys.readouterr().out
    assert main(["undo", str(tmp_path)]) == 0
    assert "Nothing to undo." in capsys.readouterr().out


def test_cli_missing_directory(tmp_path, capsys):
    assert main(["organize", str(tmp_path / "nope")]) == 2
    assert "fileorg:" in capsys.readouterr().err


def test_cli_custom_rules(make_files, tmp_path_factory, capsys):
    root = make_files({"a.jpg": None})
    rules = tmp_path_factory.mktemp("cfg") / "rules.json"
    rules.write_text('{"Pictures": ["jpg"]}')
    assert main(["organize", str(root), "--rules", str(rules)]) == 0
    assert tree(root) == {"Pictures/a.jpg"}
