from sudoku import board as B
from sudoku import generate, has_unique_solution, solve
from sudoku.cli import main


def test_generated_puzzle_is_unique_and_consistent():
    puzzle, solution = generate(seed=1, min_givens=28)
    assert B.is_solved(solution)
    assert B.agrees_with(solution, puzzle)
    assert has_unique_solution(puzzle)
    assert solve(puzzle).solution == solution
    assert sum(1 for v in puzzle if v) >= 28


def test_generator_is_deterministic_and_symmetric():
    a, _ = generate(seed=42)
    b, _ = generate(seed=42)
    assert a == b
    assert all((a[i] == 0) == (a[80 - i] == 0) for i in range(81))


def test_cli_solve_line(load, capsys, tmp_path):
    f = tmp_path / "p.txt"
    f.write_text(B.to_line(load("easy.txt")))
    assert main(["solve", str(f), "--line", "--stats"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("534678912")
    assert out[1].startswith("nodes=")


def test_cli_check(capsys, tmp_path):
    f = tmp_path / "bad.txt"
    f.write_text("11" + "." * 79)
    assert main(["check", str(f)]) == 2
    assert "conflict: r1c1 and r1c2 both 1" in capsys.readouterr().out
    f.write_text("." * 81)
    assert main(["check", str(f)]) == 1
    assert "multiple" in capsys.readouterr().out


def test_cli_parse_error(capsys, tmp_path):
    f = tmp_path / "short.txt"
    f.write_text("123")
    assert main(["solve", str(f)]) == 2
    assert "expected 81 cells" in capsys.readouterr().err


def test_cli_hint_and_generate(load, capsys, tmp_path):
    f = tmp_path / "p.txt"
    f.write_text(B.to_line(load("hard.txt")))
    assert main(["hint", str(f)]) == 0
    assert len(capsys.readouterr().out.splitlines()) == 9
    assert main(["generate", "--seed", "3"]) == 0
    assert "givens" in capsys.readouterr().out
