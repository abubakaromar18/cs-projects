import io

import pytest

from page_replacement.cli import main


def run(*argv):
    buf = io.StringIO()
    code = main(list(argv), out=buf)
    return code, buf.getvalue()


def test_compare_default_textbook():
    code, out = run("compare", "-f", "3")
    assert code == 0
    lines = {l.split()[0]: l.split() for l in out.splitlines() if l[:1].isalpha()}
    assert lines["opt"][1] == "9" and lines["lru"][1] == "12" and lines["fifo"][1] == "15"
    assert lines["fifo"][-1] == "+6"


def test_trace_grid_and_steps():
    code, out = run("trace", "-a", "fifo", "-f", "3", "-r", "1 2 3 4")
    assert code == 0 and "FIFO: 4 faults" in out and out.count("*") == 4
    code, out = run("trace", "-a", "clock", "--steps", "-r", "1 2 1 3", "-f", "2")
    assert "bits=" in out and "evict 1" in out  # all bits set: full sweep, back to slot 0


def test_sweep_reports_anomaly():
    code, out = run("sweep", "--preset", "belady", "-F", "1-5", "-a", "fifo")
    assert code == 0 and "Belady's anomaly: fifo 3->4" in out
    code, out = run("sweep", "--chart", "--gen", "loop", "-n", "20", "-p", "4", "-F", "3-4")
    assert "#" in out


def test_belady_commands():
    assert run("belady")[0] == 0
    code, out = run("belady", "--search", "-a", "lru", "--tries", "200", "--seed", "1")
    assert code == 1 and "stack algorithms" in out


def test_list_and_errors(capsys):
    code, out = run("list")
    assert code == 0 and "clock" in out
    assert main(["compare", "-r", "1 x"], out=io.StringIO()) == 2
    with pytest.raises(SystemExit):
        main(["compare", "-a", "nope"])
    with pytest.raises(SystemExit):
        main(["sweep", "-F", "5-2"])
