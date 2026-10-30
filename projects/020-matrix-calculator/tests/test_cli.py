import io

from matcalc.cli import main


def run(capsys, *argv):
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def test_det_with_steps_and_check(capsys):
    code, out, _ = run(capsys, "det", "2 1 -1; -3 -1 2; -2 1 2", "--steps", "--check")
    assert code == 0
    assert "Step 1: Start" in out
    assert "agrees" in out
    assert out.strip().endswith("det = -1")


def test_inv_check(capsys):
    code, out, _ = run(capsys, "inv", "[[4,7],[2,6]]", "--check")
    assert code == 0 and "-7/10" in out and "yes" in out


def test_inv_singular_exit_code(capsys):
    code, _, err = run(capsys, "inv", "1 2; 2 4")
    assert code == 2 and "singular" in err


def test_rref_and_rank(capsys):
    _, out, _ = run(capsys, "rref", "1 2 3; 4 5 6; 7 8 9")
    assert "rank = 2" in out and "pivot columns = [1, 2]" in out
    _, out, _ = run(capsys, "rank", "1 2; 2 4")
    assert out.strip() == "1"


def test_solve_accepts_row_vector_for_b(capsys):
    _, out, _ = run(capsys, "solve", "1 1; 1 -1", "3 1")
    assert "x1 = 2" in out and "x2 = 1" in out


def test_mul_transpose_pow(capsys):
    _, out, _ = run(capsys, "mul", "1 2", "3; 4")
    assert "11" in out
    _, out, _ = run(capsys, "transpose", "1 2 3")
    assert len(out.strip().splitlines()) == 3
    _, out, _ = run(capsys, "pow", "1 1; 1 0", "10")
    assert "89" in out and "55" in out


def test_reads_file_and_stdin(capsys, tmp_path, monkeypatch):
    f = tmp_path / "m.txt"
    f.write_text("1 2\n3 4\n")
    _, out, _ = run(capsys, "det", f"@{f}")
    assert "det = -2" in out
    monkeypatch.setattr("sys.stdin", io.StringIO("[[2,0],[0,3]]"))
    _, out, _ = run(capsys, "det", "-")
    assert "det = 6" in out


def test_parse_error_exit_code(capsys):
    code, _, err = run(capsys, "det", "1 2; 3")
    assert code == 1 and "error" in err
