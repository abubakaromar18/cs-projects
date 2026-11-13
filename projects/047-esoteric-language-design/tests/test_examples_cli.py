from pathlib import Path

import pytest

from pebble import run_source
from pebble.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def run_example(name, stdin=""):
    return run_source((EXAMPLES / name).read_text(), stdin=stdin)


def test_hello():
    assert run_example("hello.pbl") == "Hello, World!\n"


def test_fizzbuzz():
    expected = []
    for i in range(1, 101):
        expected.append("FizzBuzz" if i % 15 == 0 else "Fizz" if i % 3 == 0 else "Buzz" if i % 5 == 0 else str(i))
    assert run_example("fizzbuzz.pbl").splitlines() == expected


def test_factorial():
    import math

    lines = run_example("factorial.pbl").splitlines()
    assert lines == [f"{i}! = {math.factorial(i)}" for i in range(11)]


def test_fibonacci():
    a, b, fibs = 0, 1, []
    for _ in range(20):
        fibs.append(a)
        a, b = b, a + b
    assert run_example("fibonacci.pbl").split() == [str(x) for x in fibs]


def test_primes():
    assert run_example("primes.pbl").split() == [
        str(p) for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
    ]


def test_cat_and_sum_use_input():
    assert run_example("cat.pbl", stdin="echo me\n") == "echo me\n"
    assert run_example("sum.pbl", stdin="10 20\n30") == "60\n"


def test_cli_eval_and_stack(capsys):
    assert main(["-e", "1 2 + : .", "--stack"]) == 0
    assert capsys.readouterr().out == "3\nstack: [3]\n"


def test_cli_runs_file(capsys):
    assert main([str(EXAMPLES / "hello.pbl")]) == 0
    assert capsys.readouterr().out == "Hello, World!\n"


def test_cli_tokens_and_ast(capsys):
    assert main(["-e", "1 [ , ]", "--tokens"]) == 0
    assert "LBRACKET" in capsys.readouterr().out
    assert main(["-e", "(F 1) F", "--ast"]) == 0
    out = capsys.readouterr().out
    assert "Call F" in out and "Define F" in out


def test_cli_reports_errors_with_exit_code(capsys):
    assert main(["-e", "1 +"]) == 1
    assert "runtime error at 1:3" in capsys.readouterr().err
    assert main(["-e", "["]) == 1
    assert "syntax error" in capsys.readouterr().err


def test_cli_missing_file(capsys):
    assert main(["no/such/file.pbl"]) == 2
    assert "cannot read" in capsys.readouterr().err
