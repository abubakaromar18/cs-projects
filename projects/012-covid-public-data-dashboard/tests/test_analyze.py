import math

import numpy as np
import pandas as pd
import pytest

from covid_dash.analyze import add_metrics, filter_frame, summarize, top_n, weekly_growth


def panel(cases, deaths=None, pop=100_000, loc="X", start="2021-01-01"):
    n = len(cases)
    return pd.DataFrame({
        "location": loc, "iso_code": loc, "continent": "C",
        "date": pd.date_range(start, periods=n, freq="D"),
        "new_cases": np.asarray(cases, float),
        "new_deaths": np.asarray(deaths if deaths is not None else [0] * n, float),
        "population": float(pop),
    })


def test_cumulative_and_rolling():
    out = add_metrics(panel([7, 0, 0, 0, 0, 0, 0, 14]), window=7)
    assert list(out.total_cases) == [7, 7, 7, 7, 7, 7, 7, 21]
    assert out.cases_avg.iloc[0] == 7                # min_periods=1
    assert out.cases_avg.iloc[6] == pytest.approx(1)  # 7/7
    assert out.cases_avg.iloc[7] == pytest.approx(2)  # (0*6+14)/7


def test_per_capita_and_cfr():
    out = add_metrics(panel([100, 100], deaths=[0, 4], pop=200_000), window=1)
    assert out.cases_avg_per_100k.iloc[0] == pytest.approx(50)
    assert out.total_cases_per_100k.iloc[-1] == pytest.approx(100)
    assert out.cfr_pct.iloc[-1] == pytest.approx(2.0)


def test_cfr_nan_before_first_case_and_zero_population():
    out = add_metrics(panel([0, 5], pop=0))
    assert math.isnan(out.cfr_pct.iloc[0])
    assert out.cases_avg_per_100k.isna().all()


def test_groups_are_independent():
    df = pd.concat([panel([1] * 3, loc="A"), panel([10] * 3, loc="B")])
    out = add_metrics(df)
    assert out[out.location == "A"].total_cases.iloc[-1] == 3
    assert out[out.location == "B"].total_cases.iloc[-1] == 30


def test_bad_window():
    with pytest.raises(ValueError):
        add_metrics(panel([1]), window=0)


def test_weekly_growth():
    rising = add_metrics(panel([10] * 7 + [20] * 7))
    g = weekly_growth(rising)
    assert g["X"] == pytest.approx(100.0)  # avg went 10 -> 20
    assert math.isnan(weekly_growth(add_metrics(panel([1, 2, 3])))["X"])


def test_summary_and_top_n():
    df = pd.concat([
        panel([0, 50, 10, 0], deaths=[0, 1, 0, 0], loc="A"),
        panel([5, 5, 5, 5], loc="B", pop=10_000),
    ])
    s = summarize(add_metrics(df, window=1))
    assert list(s.index) == ["B", "A"]           # sorted by cases_per_100k
    assert s.loc["A", "total_cases"] == 60
    assert str(s.loc["A", "peak_date"]) == "2021-01-02"
    assert s.loc["B", "cases_per_100k"] == pytest.approx(200)
    assert list(top_n(s, "total_cases", 1).index) == ["A"]
    with pytest.raises(KeyError):
        top_n(s, "nope")


def test_filter_frame():
    df = add_metrics(pd.concat([panel([1] * 10, loc="Alpha"), panel([1] * 10, loc="Beta")]))
    f = filter_frame(df, locations=[" alpha "], start="2021-01-03", end="2021-01-05")
    assert set(f.location) == {"Alpha"} and len(f) == 3
    # totals keep pre-window history because metrics were computed first
    assert f.total_cases.iloc[0] == 3
