import pandas as pd
import pytest

from covid_dash.clean import clean, normalize_column


def test_normalize_column():
    assert normalize_column("  New Cases ") == "new_cases"
    assert normalize_column("ISO-Code") == "iso_code"


def test_clean_tiny_exact(tiny_raw):
    df, rep = clean(tiny_raw)
    assert rep.rows_in == 8
    assert rep.dropped_missing_keys == 1          # location None
    assert rep.dropped_aggregates == 1            # World
    assert rep.dropped_duplicates == 1            # A 2021-01-02 twice
    assert rep.bad_numbers == 1                   # "oops"
    assert rep.negative_values_fixed == 1         # -3
    assert rep.gap_days_filled == 1               # A 2021-01-03
    assert rep.locations == ["A", "B"]

    a = df[df.location == "A"].set_index("date")["new_cases"]
    assert list(a.index.strftime("%m-%d")) == ["01-01", "01-02", "01-03", "01-04"]
    assert list(a) == [10, 7, 0, 0]               # last duplicate kept; gap & negative -> 0
    b = df[df.location == "B"].set_index("date")["new_cases"]
    assert list(b) == [1000, 0]                   # "1,000" parsed, "oops" -> 0
    assert df["population"].notna().all()


def test_clean_does_not_mutate_input(tiny_raw):
    before = tiny_raw.copy()
    clean(tiny_raw)
    pd.testing.assert_frame_equal(tiny_raw, before)


def test_keep_aggregates(tiny_raw):
    _, rep = clean(tiny_raw, keep_aggregates=True)
    assert rep.dropped_aggregates == 0
    assert "World" in rep.locations


def test_missing_required_column():
    with pytest.raises(ValueError, match="new_cases"):
        clean(pd.DataFrame({"location": ["A"], "date": ["2021-01-01"]}))


def test_clean_sample_is_daily_panel(sample_path):
    from covid_dash.load import load_csv
    df, rep = clean(load_csv(sample_path))
    assert rep.locations == ["Avalonia", "Borealis", "Caldera", "Dunmore"]
    assert not df.duplicated(["location", "date"]).any()
    assert (df[["new_cases", "new_deaths"]] >= 0).all().all()
    for _, g in df.groupby("location"):
        assert (g["date"].diff().dropna() == pd.Timedelta(days=1)).all()
    assert rep.rows_out == len(df) == 4 * 200
