"""Headless smoke tests for the pygame UI (SDL dummy video driver)."""

import pytest

pygame = pytest.importorskip("pygame")

from tictactoe.board import EMPTY, X  # noqa: E402
from tictactoe.gui import App, cell_at, cell_center  # noqa: E402


def test_cell_mapping_round_trips():
    for i in range(9):
        assert cell_at(cell_center(i)) == i
    assert cell_at((0, 0)) is None


@pytest.fixture
def app():
    a = App()
    yield a
    pygame.quit()


def click(app, i):
    app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=cell_center(i)))


def key(app, k):
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k))


def test_click_places_mark_and_ai_replies(app, monkeypatch):
    click(app, 0)
    assert app.game.board.cells[0] == X
    # Fast-forward the AI delay.
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 0)
    app.update()
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 10_000)
    app.update()
    assert app.game.is_human_turn()
    assert app.game.board.cells.count(EMPTY) == 7
    app.draw()


def test_keys(app):
    key(app, pygame.K_1)  # 1 -> easy
    assert app.game.ai.difficulty == "easy"
    key(app, pygame.K_h)
    assert app.show_hints
    click(app, 4)
    key(app, pygame.K_u)
    assert app.game.board.cells.count(EMPTY) == 9
    key(app, pygame.K_s)
    assert app.game.human == "O"
    app.step()  # one full frame with hints on
    key(app, pygame.K_ESCAPE)
    assert not app.running
