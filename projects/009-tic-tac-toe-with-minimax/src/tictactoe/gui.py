"""pygame front end.

Controls
--------
mouse click   place your mark
1 / 2 / 3     difficulty: easy / medium / hard
U             undo your last move
S             swap sides (and start a new round)
R / Space     new round
H             toggle hint (shows the minimax value of each empty cell)
Esc / Q       quit
"""

from __future__ import annotations

from typing import Optional

from .ai import DIFFICULTIES, AIPlayer, move_scores
from .board import EMPTY, X
from .game import Game

# Layout
CELL = 140
GRID = CELL * 3
MARGIN = 30
HEADER = 70
FOOTER = 60
WIDTH = GRID + 2 * MARGIN
HEIGHT = HEADER + GRID + FOOTER + MARGIN

# Palette
BG = (24, 26, 33)
GRID_COLOR = (70, 75, 90)
X_COLOR = (238, 99, 82)
O_COLOR = (89, 172, 236)
TEXT = (230, 230, 235)
MUTED = (140, 145, 160)
HIGHLIGHT = (250, 210, 90)

AI_DELAY_MS = 350  # small pause so the AI's reply is visible, not instantaneous


def cell_at(pos: tuple[int, int]) -> Optional[int]:
    """Map a pixel position to a cell index, or None if outside the grid."""
    x, y = pos[0] - MARGIN, pos[1] - HEADER
    if not (0 <= x < GRID and 0 <= y < GRID):
        return None
    return (y // CELL) * 3 + (x // CELL)


def cell_center(i: int) -> tuple[int, int]:
    r, c = divmod(i, 3)
    return MARGIN + c * CELL + CELL // 2, HEADER + r * CELL + CELL // 2


class App:
    def __init__(self, game: Optional[Game] = None) -> None:
        import pygame  # imported lazily so the rest of the package works without it

        self.pg = pygame
        pygame.init()
        pygame.display.set_caption("Tic-Tac-Toe · Minimax")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.font = pygame.font.SysFont(None, 34)
        self.small = pygame.font.SysFont(None, 24)
        self.clock = pygame.time.Clock()
        self.game = game or Game()
        self.show_hints = False
        self.ai_due_at: Optional[int] = None
        self.running = True

    # ------------------------------------------------------------------ #
    # Event handling
    # ------------------------------------------------------------------ #
    def handle_event(self, event) -> None:
        pg = self.pg
        if event.type == pg.QUIT:
            self.running = False
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            i = cell_at(event.pos)
            if i is not None and self.game.is_human_turn() and self.game.board.cells[i] == EMPTY:
                self.game.human_move(i)
        elif event.type == pg.KEYDOWN:
            key = event.key
            if key in (pg.K_ESCAPE, pg.K_q):
                self.running = False
            elif key in (pg.K_r, pg.K_SPACE):
                self.game.new_round()
            elif key == pg.K_s:
                self.game.new_round(swap_sides=True)
            elif key == pg.K_u:
                self.game.undo()
            elif key == pg.K_h:
                self.show_hints = not self.show_hints
            elif key in (pg.K_1, pg.K_2, pg.K_3):
                level = DIFFICULTIES[key - pg.K_1]
                self.game.ai = AIPlayer(level, self.game.ai.rng)

    def update(self) -> None:
        """Schedule and play the AI's move after a short delay."""
        now = self.pg.time.get_ticks()
        if self.game.is_ai_turn():
            if self.ai_due_at is None:
                self.ai_due_at = now + AI_DELAY_MS
            elif now >= self.ai_due_at:
                self.game.ai_move()
                self.ai_due_at = None
        else:
            self.ai_due_at = None

    # ------------------------------------------------------------------ #
    # Drawing
    # ------------------------------------------------------------------ #
    def draw(self) -> None:
        pg, s, g = self.pg, self.screen, self.game
        s.fill(BG)

        # Header: score and difficulty
        sc = g.score
        header = f"You ({g.human}) {sc.human}   AI ({g.ai_mark}) {sc.ai}   Draws {sc.draws}"
        s.blit(self.font.render(header, True, TEXT), (MARGIN, 18))
        s.blit(self.small.render(f"AI: {g.ai.difficulty}", True, MUTED), (MARGIN, 48))

        # Grid lines
        for k in (1, 2):
            pg.draw.line(s, GRID_COLOR, (MARGIN + k * CELL, HEADER + 10),
                         (MARGIN + k * CELL, HEADER + GRID - 10), 4)
            pg.draw.line(s, GRID_COLOR, (MARGIN + 10, HEADER + k * CELL),
                         (MARGIN + GRID - 10, HEADER + k * CELL), 4)

        # Marks
        pad = CELL // 4
        for i, mark in enumerate(g.board.cells):
            cx, cy = cell_center(i)
            if mark == X:
                d = CELL // 2 - pad
                pg.draw.line(s, X_COLOR, (cx - d, cy - d), (cx + d, cy + d), 10)
                pg.draw.line(s, X_COLOR, (cx - d, cy + d), (cx + d, cy - d), 10)
            elif mark != EMPTY:
                pg.draw.circle(s, O_COLOR, (cx, cy), CELL // 2 - pad, 9)

        # Hints: each empty cell's minimax value for the human
        if self.show_hints and g.is_human_turn():
            for m, v in move_scores(g.board).items():
                label = "win" if v > 0 else "draw" if v == 0 else "lose"
                color = (120, 220, 140) if v > 0 else MUTED if v == 0 else X_COLOR
                img = self.small.render(label, True, color)
                cx, cy = cell_center(m)
                s.blit(img, img.get_rect(center=(cx, cy)))

        # Winning line
        line = g.board.winning_line()
        if line:
            pg.draw.line(s, HIGHLIGHT, cell_center(line[0]), cell_center(line[2]), 8)

        # Footer: status and help
        status = g.result_text() or ("Your move" if g.is_human_turn() else "AI is thinking…")
        s.blit(self.font.render(status, True, HIGHLIGHT if g.over else TEXT),
               (MARGIN, HEADER + GRID + 10))
        help_text = "R new · U undo · S swap · H hints · 1/2/3 level"
        s.blit(self.small.render(help_text, True, MUTED), (MARGIN, HEADER + GRID + 44))

        pg.display.flip()

    def step(self) -> None:
        """Process one frame: events, AI, rendering."""
        for event in self.pg.event.get():
            self.handle_event(event)
        self.update()
        self.draw()

    def run(self) -> None:
        while self.running:
            self.step()
            self.clock.tick(60)
        self.pg.quit()


def main(difficulty: str = "hard", human: str = X) -> int:
    try:
        App(Game(human=human, ai=AIPlayer(difficulty))).run()
    except ImportError:
        print("pygame is not installed: run `pip install pygame`, or use `--cli`.")
        return 1
    except Exception as exc:  # pygame.error when no display is available
        if type(exc).__name__ != "error":
            raise
        print(f"Could not open a window ({exc}); try `--cli` for the terminal version.")
        return 1
    return 0
