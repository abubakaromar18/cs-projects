from pathlib import Path

import pytest

from cipherbreak.cli import main

EXAMPLES = Path(__file__).parent.parent / "examples"


def run(capsys, *argv):
    assert main(list(argv)) == 0
    return capsys.readouterr().out


def test_encrypt_decrypt(capsys):
    assert run(capsys, "encrypt", "caesar", "-k", "3", "Hello") == "Khoor\n"
    assert run(capsys, "decrypt", "vigenere", "-k", "LEMON", "LXFOPVEFRNHR") == "ATTACKATDAWN\n"


def test_bad_caesar_key(capsys):
    with pytest.raises(SystemExit):
        main(["encrypt", "caesar", "-k", "abc", "x"])


def test_stdin(capsys, monkeypatch):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO("abc"))
    assert run(capsys, "encrypt", "caesar", "-k", "1") == "bcd"


def test_crack_caesar_example(capsys):
    out = run(capsys, "crack-caesar", "-f", str(EXAMPLES / "caesar.txt"))
    assert out.startswith("The history of secret writing")


def test_crack_caesar_top(capsys):
    out = run(capsys, "crack-caesar", "-f", str(EXAMPLES / "caesar.txt"), "--top", "3")
    assert out.count("--- shift") == 3 and "--- shift 17" in out.splitlines()[0]


def test_crack_vigenere_example(capsys):
    out = run(capsys, "crack-vigenere", "-f", str(EXAMPLES / "vigenere.txt"), "--explain")
    assert "key: FREQUENCY" in out
    assert "The history of secret writing" in out
    assert "<-" in out


def test_analyze(capsys):
    out = run(capsys, "analyze", "-f", str(EXAMPLES / "caesar.txt"))
    assert "index of coincidence" in out and " E " in out
