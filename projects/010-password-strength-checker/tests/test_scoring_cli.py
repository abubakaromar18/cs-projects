import io
import json

import pytest

from password_checker import cli
from password_checker.scoring import bits_to_score, check, human_time


@pytest.mark.parametrize("bits,score", [(0, 0), (27.9, 0), (28, 1), (40, 2), (70, 3), (80, 4), (200, 4)])
def test_bits_to_score(bits, score):
    assert bits_to_score(bits) == score


def test_human_time():
    assert human_time(0.5) == "instant"
    assert human_time(1) == "1 second"
    assert human_time(7200) == "2 hours"
    assert human_time(86_400 * 3) == "3 days"
    assert human_time(1e12) == "centuries"


def test_breached_password_scores_zero():
    r = check("password")
    assert r.breached and r.score == 0 and r.label == "very weak"
    assert any("breach" in tip for tip in r.feedback)


def test_hibp_count_marks_breached():
    r = check("xK9#mQ2$vLp7!zR4", pwned=5)
    assert r.breached and r.score == 0


def test_strong_random_password():
    r = check("xK9#mQ2$vLp7!zR4")
    assert r.score == 4 and not r.breached and r.feedback == []


def test_to_dict_is_json_serialisable():
    d = check("Summer1999!").to_dict()
    json.dumps(d)
    assert {p["kind"] for p in d["patterns"]} == {"dictionary", "year"}


def test_cli_stdin_json(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("password\nxK9#mQ2$vLp7!zR4\n"))
    code = cli.main(["--stdin", "--json"])
    lines = [json.loads(l) for l in capsys.readouterr().out.splitlines()]
    assert [l["score"] for l in lines] == [0, 4]
    assert code == 1  # at least one weak password


def test_cli_prompt_human_output(monkeypatch, capsys):
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: "xK9#mQ2$vLp7!zR4")
    assert cli.main([]) == 0
    out = capsys.readouterr().out
    assert "4/4 (very strong)" in out
    assert "xK9#" not in out  # the password itself is never echoed


def test_cli_online_failure_is_warning(monkeypatch, capsys):
    def boom(pw):
        raise OSError("no network")

    monkeypatch.setattr(cli, "pwned_count", boom)
    monkeypatch.setattr("sys.stdin", io.StringIO("xK9#mQ2$vLp7!zR4\n"))
    assert cli.main(["--stdin", "--online"]) == 0
    assert "HIBP lookup failed" in capsys.readouterr().err
