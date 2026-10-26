import pandas as pd

from covid_dash.analyze import add_metrics, summarize
from covid_dash.clean import clean
from covid_dash.cli import main
from covid_dash.dashboard import build_dashboard
from covid_dash.load import load_csv
from covid_dash.sample import generate


def test_sample_generator_is_deterministic():
    pd.testing.assert_frame_equal(generate(seed=3), generate(seed=3))


def test_bundled_sample_matches_generator(tmp_path, sample_path):
    fresh = tmp_path / "s.csv"
    generate().to_csv(fresh, index=False)
    assert fresh.read_bytes() == sample_path.read_bytes()


def test_dashboard_figure(sample_path):
    df, _ = clean(load_csv(sample_path))
    data = add_metrics(df)
    fig = build_dashboard(data, summarize(data))
    # 4 traces per location + 1 summary table
    assert len(fig.data) == 4 * 4 + 1
    assert fig.data[-1].type == "table"
    assert sum(t.showlegend is not False for t in fig.data if t.type == "scatter") == 4


def test_cli_end_to_end(tmp_path, sample_path, capsys):
    out = tmp_path / "dash.html"
    csv = tmp_path / "clean.csv"
    rc = main(["-i", str(sample_path), "-o", str(out), "--summary",
               "--countries", "Avalonia,caldera", "--start", "2021-03-01",
               "--export-clean", str(csv)])
    assert rc == 0
    html = out.read_text()
    assert "plotly" in html.lower() and "Avalonia" in html
    captured = capsys.readouterr()
    assert "Caldera" in captured.out and "Borealis" not in captured.out
    assert "Cleaning report" in captured.err
    exported = pd.read_csv(csv, parse_dates=["date"])
    assert set(exported.location) == {"Avalonia", "Caldera"}
    assert exported.date.min() == pd.Timestamp("2021-03-01")


def test_cli_top_n(tmp_path, sample_path, capsys):
    assert main(["-i", str(sample_path), "--top", "2", "--summary", "--no-html"]) == 0
    out = capsys.readouterr().out
    assert "Avalonia" in out and "Dunmore" in out and "Caldera" not in out


def test_cli_errors(tmp_path, sample_path, capsys):
    assert main(["-i", str(tmp_path / "missing.csv"), "--no-html"]) == 1
    assert main(["-i", str(sample_path), "--countries", "Atlantis", "--no-html"]) == 1
    assert "no rows" in capsys.readouterr().err
