import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from plaintext import SAMPLE  # noqa: E402


@pytest.fixture
def sample() -> str:
    return SAMPLE
