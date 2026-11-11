import io
from pathlib import Path

from trie_autocomplete.cli import main
from trie_autocomplete import load

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample.txt"


def run(*argv, stdin=""):
    out = io.StringIO()
    code = main(list(argv), stdin=io.StringIO(stdin), stdout=out)
    return code, out.getvalue()


def test_train_suggest_remove(tmp_path):
    db = str(tmp_path / "w.json")
    corpus = tmp_path / "c.txt"
    corpus.write_text("the the the then this a")
    code, out = run("--db", db, "train", str(corpus))
    assert code == 0 and "3 new words" in out
    code, out = run("--db", db, "suggest", "th", "-k", "2")
    assert code == 0
    lines = out.strip().splitlines()
    assert lines[0].split()[1:] == ["the", "3"] and len(lines) == 2
    assert run("--db", db, "remove", "the")[0] == 0
    assert "the" not in load(db)
    assert run("--db", db, "remove", "the")[0] == 1


def test_add_and_list(tmp_path):
    db = str(tmp_path / "w.json")
    run("--db", db, "add", "Zeta", "--freq", "4")
    run("--db", db, "add", "zebra")
    code, out = run("--db", db, "list", "ze")
    assert out.splitlines() == ["zebra\t1", "zeta\t4"]


def test_corpus_mode_is_read_only(tmp_path):
    code, out = run("--corpus", str(SAMPLE), "suggest", "th", "-k", "1")
    assert code == 0 and "the" in out
    assert run("--corpus", str(SAMPLE), "add", "x")[0] == 2


def test_stats(tmp_path):
    code, out = run("--corpus", str(SAMPLE), "stats")
    assert code == 0 and "words:" in out and "prefix sharing" in out


def test_repl_records_picks_and_saves(tmp_path):
    db = str(tmp_path / "w.json")
    run("--db", db, "add", "transform")
    run("--db", db, "add", "transport")
    code, out = run("--db", db, "repl", stdin="tr\n+transport\n+transport\ntr\n-nothing\n:q\n")
    assert code == 0
    assert "[tab → trans]" in out
    assert "recorded 'transport' (now 3)" in out
    assert "not found:" in out
    assert load(db).frequency("transport") == 3


def test_suggest_no_match(tmp_path):
    code, out = run("--db", str(tmp_path / "w.json"), "suggest", "qq")
    assert code == 0 and "no words start" in out
