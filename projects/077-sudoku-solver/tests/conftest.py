from pathlib import Path

import pytest

from sudoku import parse

PUZZLES = Path(__file__).resolve().parent.parent / "puzzles"


@pytest.fixture
def load():
    return lambda name: parse((PUZZLES / name).read_text())
