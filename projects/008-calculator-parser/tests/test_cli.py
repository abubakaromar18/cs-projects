from calc.cli import main, run_line
from calc.evaluator import Evaluator


def test_one_shot(capsys):
    assert main(["2", "*", "(3", "+", "4)"]) == 0
    assert capsys.readouterr().out.strip() == "14"


def test_one_shot_with_ast(capsys):
    assert main(["--ast", "1+2*3"]) == 0
    assert capsys.readouterr().out.splitlines() == ["(+ 1 (* 2 3))", "7"]


def test_error_exit_code_and_caret(capsys):
    assert main(["1 + * 2"]) == 1
    err = capsys.readouterr().err.splitlines()
    assert err[0] == "1 + * 2"
    assert err[1] == "    ^"


def test_repl_commands():
    ev = Evaluator()
    assert run_line(ev, "x = 5") == "5"
    assert run_line(ev, ":vars") == "ans = 5\nx = 5"
    assert run_line(ev, ":ast -x^2") == "(neg (^ x 2))"
    assert run_line(ev, ":tokens 1+x") == "NUMBER(1) PLUS(+) IDENT(x) EOF"
    assert "Functions" in run_line(ev, ":help")


def test_repl_session(monkeypatch, capsys):
    lines = iter(["r = 2", "pi * r ^ 2", "1 / 0", ":quit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(lines))
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "12.5663706144" in out
    assert "division by zero" in out


def test_ast_of_huge_expression_fails_cleanly():
    import pytest

    from calc.errors import EvalError

    with pytest.raises(EvalError):
        run_line(Evaluator(), ":ast " + "+".join(["1"] * 20000))
