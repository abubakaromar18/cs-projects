from spamfilter.cli import main

from conftest import SAMPLE


def test_train_then_predict(tmp_path, capsys):
    out = tmp_path / "model.json"
    assert main(["train", "-d", str(SAMPLE), "-o", str(out)]) == 0
    assert out.exists()
    assert main(["predict", "-m", str(out), "WIN a FREE prize now, text CLAIM to 80086",
                 "meet you at the library"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()[-2:]
    assert lines[0].startswith("spam") and lines[1].startswith("ham")


def test_predict_from_stdin(monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO("free cash prize call now\n\n"))
    assert main(["predict"]) == 0
    assert capsys.readouterr().out.startswith("spam")


def test_eval_and_cv(capsys):
    assert main(["eval"]) == 0
    assert "precision" in capsys.readouterr().out
    assert main(["cv", "-k", "3"]) == 0
    out = capsys.readouterr().out
    assert "fold 3" in out and "pooled over 3 folds" in out


def test_explain_and_top(capsys):
    assert main(["explain", "claim your prize"]) == 0
    assert "P(spam)" in capsys.readouterr().out
    assert main(["top", "-n", "3"]) == 0
    assert "most ham-indicative" in capsys.readouterr().out


def test_missing_file_is_clean_error(capsys):
    assert main(["eval", "-d", "/nonexistent.tsv"]) == 1
    assert "error" in capsys.readouterr().err
