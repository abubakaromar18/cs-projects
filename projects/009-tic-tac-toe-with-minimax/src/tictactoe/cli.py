"""Command-line entry point: launches the pygame UI, or a terminal game with --cli."""

from __future__ import annotations

import argparse
import sys
from typing import Callable, Optional, TextIO

from .ai import DIFFICULTIES, AIPlayer, SearchStats, alphabeta, count_minimax_nodes, move_scores
from .board import O, X, Board, IllegalMove
from .game import Game


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tictactoe", description="Tic-tac-toe with an unbeatable minimax AI.")
    p.add_argument("--cli", action="store_true", help="play in the terminal instead of a pygame window")
    p.add_argument("--difficulty", "-d", choices=DIFFICULTIES, default="hard")
    p.add_argument("--play-as", choices=(X, O), default=X, help="X moves first (default: X)")
    p.add_argument("--analyze", metavar="BOARD",
                   help="print move values for a 9-char board like 'X...O....' and exit")
    p.add_argument("--stats", action="store_true",
                   help="compare node counts: full minimax tree vs. alpha-beta, then exit")
    return p


def analyze(board_str: str, out: TextIO) -> int:
    board = Board.from_string(board_str)
    print(board, file=out)
    if board.is_terminal():
        print("Game over:", board.winner() or "draw", file=out)
        return 0
    print(f"\n{board.to_move} to move. Move values (+ win, 0 draw, - loss):", file=out)
    for move, value in sorted(move_scores(board).items(), key=lambda kv: -kv[1]):
        print(f"  cell {move + 1}: {value:+d}", file=out)
    return 0


def stats(out: TextIO) -> int:
    empty = Board()
    s = SearchStats()
    value = alphabeta(empty, stats=s)
    full = count_minimax_nodes(empty)
    print(f"Value of the empty board: {value} (a draw with perfect play)", file=out)
    print(f"Plain minimax visits  {full:>7,} nodes", file=out)
    print(f"Alpha-beta visits     {s.nodes:>7,} nodes ({s.cutoffs:,} cutoffs, "
          f"{100 * (1 - s.nodes / full):.1f}% pruned)", file=out)
    return 0


def play_terminal(game: Game, read: Callable[[str], str] = input, out: TextIO = sys.stdout) -> int:
    """Interactive loop. ``read`` is injectable so tests can script input."""
    print(f"You are {game.human}. Enter 1-9 to move, 'u' to undo, 'q' to quit.\n", file=out)
    while True:
        while not game.over:
            if game.is_ai_turn():
                move = game.ai_move()
                print(f"AI plays {move + 1}", file=out)
                continue
            print(game.board, "\n", file=out)
            try:
                raw = read("Your move: ").strip().lower()
            except EOFError:
                return 0
            if raw in ("q", "quit"):
                return 0
            if raw == "u":
                game.undo()
                continue
            try:
                game.human_move(int(raw) - 1)
            except (ValueError, IllegalMove) as exc:
                print(f"  ✗ {exc if isinstance(exc, IllegalMove) else 'enter a number 1-9'}", file=out)
        print(game.board, "\n", file=out)
        print(game.result_text(), file=out)
        sc = game.score
        print(f"Score — you {sc.human}, AI {sc.ai}, draws {sc.draws}", file=out)
        try:
            again = read("Play again? [y/N] ").strip().lower()
        except EOFError:
            return 0
        if again not in ("y", "yes"):
            return 0
        game.new_round(swap_sides=True)
        print(f"\nSwapping sides: you are now {game.human}.\n", file=out)


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.stats:
        return stats(sys.stdout)
    if args.analyze:
        try:
            return analyze(args.analyze, sys.stdout)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    game = Game(human=args.play_as, ai=AIPlayer(args.difficulty))
    if args.cli:
        return play_terminal(game)
    from .gui import main as gui_main
    return gui_main(args.difficulty, args.play_as)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
