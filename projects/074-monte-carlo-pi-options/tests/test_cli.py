from montecarlo.cli import main


def test_pi_command(capsys):
    assert main(["pi", "-n", "20000", "--seed", "1"]) == 0
    out = capsys.readouterr().out
    assert "pi (crude)" in out and "true pi" in out


def test_option_command(capsys):
    assert main(["option", "-n", "20000", "--seed", "1", "--kind", "put"]) == 0
    out = capsys.readouterr().out
    assert "Black-Scholes" in out and "antithetic" in out and "control" in out


def test_convergence_command(capsys):
    assert main(["convergence", "--max-samples", "10000", "--seed", "1"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 4  # header + n=100, 1000, 10000
