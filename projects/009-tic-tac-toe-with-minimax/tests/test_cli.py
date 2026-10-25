import io

from tictactoe.cli import analyze, main, play_terminal, stats
from tictactoe.game import Game


def scripted(*lines):
    it = iter(lines)

    def read(_prompt):
        try:
            return next(it)
        except StopIteration:
            raise EOFError
    return read


def test_analyze_output():
    out = io.StringIO()
    assert analyze("XX.OO....", out) == 0
    assert "cell 3: +5" in out.getvalue()


def test_analyze_bad_board(capsys):
    assert main(["--analyze", "XXX"]) == 2
    assert "error" in capsys.readouterr().err


def test_stats():
    out = io.StringIO()
    stats(out)
    assert "549,946" in out.getvalue() and "pruned" in out.getvalue()


def test_terminal_game_runs_to_completion():
    out = io.StringIO()
    # Corner opening, then blindly try every cell; invalid ones are rejected.
    moves = ["1", "abc", "1"] + [str(i) for i in range(2, 10)] * 2 + ["n"]
    game = Game()
    assert play_terminal(game, scripted(*moves), out) == 0
    text = out.getvalue()
    assert "AI plays" in text
    assert "enter a number 1-9" in text and "already taken" in text
    assert game.score.human == 0  # the hard AI can't be beaten
    assert ("Draw!" in text) or ("AI wins!" in text)


def test_terminal_quit_and_undo():
    out = io.StringIO()
    g = Game()
    assert play_terminal(g, scripted("5", "u", "q"), out) == 0
    assert g.history == []
