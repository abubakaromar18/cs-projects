import pytest

from cpusched import Process, ascii_gantt, fcfs, mlfq, parse_workload, svg_gantt
from cpusched.cli import main


def test_parse_workload_skips_comments_and_header():
    text = "# comment\npid,arrival,burst\n\nA, 0, 3  # inline\nB,2,1\n"
    assert parse_workload(text) == [Process("A", 0, 3), Process("B", 2, 1)]


@pytest.mark.parametrize("text", ["A,0", "A,x,1", "A,0,0", "A,0,1\nA,1,1"])
def test_parse_workload_errors(text):
    with pytest.raises(ValueError):
        parse_workload(text)


def test_ascii_gantt_layout():
    chart = ascii_gantt(fcfs([Process("P1", 0, 2), Process("P2", 4, 3)]), scale=2)
    assert chart.splitlines() == [
        "+----+------+------+",
        "| P1 | idle |  P2  |",
        "+----+------+------+",
        "0    2      4      7",
    ]


def test_ascii_gantt_lines_align():
    chart = ascii_gantt(mlfq([Process("job", 0, 9), Process("x", 1, 1)]), scale=1, show_levels=True)
    border, middle, *_ = chart.splitlines()
    assert len(border) == len(middle)
    assert "job@0" in middle


def test_svg_gantt_is_well_formed_xml():
    import xml.dom.minidom

    svg = svg_gantt(mlfq([Process("A<&>", 0, 5), Process("B", 1, 2)]))
    xml.dom.minidom.parseString(svg)  # raises if malformed (e.g. unescaped pid)


@pytest.fixture
def workload_file(tmp_path):
    path = tmp_path / "w.csv"
    path.write_text("P1,0,8\nP2,1,4\nP3,2,9\nP4,3,5\n")
    return path


@pytest.mark.parametrize("algo", ["fcfs", "sjf", "srtf", "rr", "mlfq"])
def test_cli_run(workload_file, capsys, algo):
    assert main(["run", str(workload_file), "-a", algo]) == 0
    out = capsys.readouterr().out
    assert "avg" in out and "makespan=26" in out


def test_cli_run_writes_svg(workload_file, tmp_path, capsys):
    svg = tmp_path / "g.svg"
    assert main(["run", str(workload_file), "-a", "rr", "--svg", str(svg)]) == 0
    assert svg.read_text().startswith("<svg")


def test_cli_compare(workload_file, capsys):
    assert main(["compare", str(workload_file), "--gantt"]) == 0
    out = capsys.readouterr().out
    for name in ("FCFS", "SJF", "SRTF", "RR (q=2)", "MLFQ"):
        assert name in out
    assert "6.50" in out  # SRTF average waiting on the textbook workload


def test_cli_missing_file_reports_error(capsys):
    assert main(["run", "does-not-exist.csv"]) == 1
    assert "error" in capsys.readouterr().err


def test_cli_random(capsys):
    assert main(["random", "3", "--seed", "1"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[0] == "pid,arrival,burst" and len(lines) == 4
