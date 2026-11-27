from fileorg.planner import Mode, plan_moves, unique_name


def rel(plan):
    return {m.relative(plan.root) for m in plan.moves}


def test_plan_by_type_does_not_touch_disk(make_files):
    root = make_files({"a.jpg": None, "b.pdf": None, "c.xyz": None})
    before = sorted(p.name for p in root.iterdir())
    plan = plan_moves(root)
    assert rel(plan) == {
        ("a.jpg", "Images/a.jpg"),
        ("b.pdf", "Documents/b.pdf"),
        ("c.xyz", "Other/c.xyz"),
    }
    assert sorted(p.name for p in root.iterdir()) == before
    assert plan.summary() == {"Documents": 1, "Images": 1, "Other": 1}


def test_plan_by_date(make_files):
    root = make_files({"a.jpg": (2024, 3), "b.pdf": (2025, 11)})
    assert rel(plan_moves(root, mode=Mode.DATE)) == {
        ("a.jpg", "2024/03/a.jpg"),
        ("b.pdf", "2025/11/b.pdf"),
    }


def test_plan_by_type_date(make_files):
    root = make_files({"a.jpg": (2024, 3)})
    assert rel(plan_moves(root, mode="type-date")) == {("a.jpg", "Images/2024/03/a.jpg")}


def test_hidden_files_skipped_by_default(make_files):
    root = make_files({".env": None, "a.txt": None})
    assert rel(plan_moves(root)) == {("a.txt", "Documents/a.txt")}
    assert (".env", "Other/.env") in rel(plan_moves(root, include_hidden=True))


def test_non_recursive_ignores_subdirs(make_files):
    root = make_files({"sub/a.jpg": None, "b.jpg": None})
    assert rel(plan_moves(root)) == {("b.jpg", "Images/b.jpg")}


def test_recursive_flattens_but_skips_category_folders(make_files):
    root = make_files({"sub/deep/a.jpg": None, "Images/old.jpg": None})
    assert rel(plan_moves(root, recursive=True)) == {("sub/deep/a.jpg", "Images/a.jpg")}


def test_collisions_get_numbered_suffix(make_files):
    root = make_files({"Images/pic.JPG": None, "pic.JPG": None,
                       "x/pic.JPG": None, "y/pic.JPG": None})
    moves = rel(plan_moves(root, recursive=True))
    assert moves == {
        ("pic.JPG", "Images/pic (1).JPG"),
        ("x/pic.JPG", "Images/pic (2).JPG"),
        ("y/pic.JPG", "Images/pic (3).JPG"),
    }


def test_compound_extension_suffix(tmp_path):
    (tmp_path / "b.tar.gz").write_text("x")
    assert unique_name(tmp_path, "b.tar.gz", set()).name == "b (1).tar.gz"
    assert unique_name(tmp_path, "c.tar.gz", set()).name == "c.tar.gz"


def test_plan_is_deterministic(make_files):
    root = make_files({f"d{i}/f.txt": None for i in range(5)})
    assert plan_moves(root, recursive=True).moves == plan_moves(root, recursive=True).moves


def test_symlinks_skipped(make_files):
    root = make_files({"real.txt": None})
    (root / "link.txt").symlink_to(root / "real.txt")
    plan = plan_moves(root)
    assert rel(plan) == {("real.txt", "Documents/real.txt")}
    assert [p.name for p, _ in plan.skipped] == ["link.txt"]
