from pathlib import Path

import pandas as pd
import pytest

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample_covid.csv"


@pytest.fixture
def sample_path() -> Path:
    return SAMPLE


@pytest.fixture
def tiny_raw() -> pd.DataFrame:
    """A hand-written frame whose cleaned result can be checked exactly."""
    return pd.DataFrame({
        " Location ": ["A", "A", "A", "A", "B", "B", "World", None],
        "Date": ["2021-01-01", "2021-01-02", "2021-01-02", "2021-01-04",
                 "2021-01-01", "2021-01-02", "2021-01-01", "2021-01-01"],
        "New Cases": ["10", "5", "7", "-3", "1,000", "oops", "2000", "9"],
        "new_deaths": ["1", "", "0", "0", "2", "1", "5", "0"],
        "population": ["100000", "100000", "100000", "100000", "200000", "200000", "300000", "1"],
        "iso_code": ["AAA", "AAA", "AAA", "AAA", "BBB", "BBB", "OWID_WRL", "ZZZ"],
    }, dtype=str)
