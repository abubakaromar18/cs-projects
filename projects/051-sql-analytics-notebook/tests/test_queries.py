"""Each analysis query returns results that match known facts about the dataset."""

import pytest

from analytics import list_queries, load_query, run_query

from conftest import as_dicts


def test_ten_queries_discovered():
    assert len(list_queries()) == 10
    assert list_queries()[0].startswith("01_")


def test_load_query_by_number_and_unknown():
    assert "ROW_NUMBER" in load_query("04")
    with pytest.raises(KeyError):
        load_query("99")


@pytest.mark.parametrize("name", list_queries())
def test_every_query_runs_and_returns_rows(conn, name):
    cols, rows = run_query(conn, name)
    assert cols and rows


def test_data_quality(conn):
    (row,) = as_dicts(run_query(conn, "01"))
    assert row["total_rows"] == 344
    assert row["missing_body_mass"] == 2
    assert row["missing_sex"] == 11


def test_species_by_island(conn):
    rows = {(r["species"], r["island"]): r for r in as_dicts(run_query(conn, "02"))}
    assert rows[("Gentoo", "Biscoe")]["n"] == 124
    assert rows[("Chinstrap", "Dream")]["pct_of_species"] == 100.0
    adelie_pct = sum(r["pct_of_species"] for k, r in rows.items() if k[0] == "Adelie")
    assert adelie_pct == pytest.approx(100.0, abs=0.2)


def test_summary_males_heavier(conn):
    rows = as_dicts(run_query(conn, "03"))
    assert len(rows) == 6  # 3 species × 2 sexes, NULL sex excluded
    by = {(r["species"], r["sex"]): r["avg_body_mass_g"] for r in rows}
    for sp in ("Adelie", "Chinstrap", "Gentoo"):
        assert by[(sp, "male")] > by[(sp, "female")]


def test_heaviest_is_ranked(conn):
    rows = as_dicts(run_query(conn, "04"))
    assert len(rows) == 9
    gentoo = [r for r in rows if r["species"] == "Gentoo"]
    assert [r["rank_in_species"] for r in gentoo] == [1, 2, 3]
    assert gentoo[0]["body_mass_g"] == 6300
    masses = [r["body_mass_g"] for r in gentoo]
    assert masses == sorted(masses, reverse=True)


def test_outliers_match_python_zscore(conn):
    # Recompute z-scores in Python and confirm the SQL flags the same penguins.
    import statistics

    data = conn.execute(
        "SELECT id, species, body_mass_g FROM penguins WHERE body_mass_g IS NOT NULL"
    ).fetchall()
    expected = set()
    for sp in {d[1] for d in data}:
        vals = [d[2] for d in data if d[1] == sp]
        mu, sd = statistics.fmean(vals), statistics.pstdev(vals)
        expected |= {d[0] for d in data if d[1] == sp and abs(d[2] - mu) / sd > 2.5}
    got = {r["id"] for r in as_dicts(run_query(conn, "05"))}
    assert got == expected


def test_yearly_trend_lag(conn):
    rows = as_dicts(run_query(conn, "06"))
    assert len(rows) == 9
    for r in rows:
        if r["year"] == 2007:
            assert r["change_from_prev_year_g"] is None
    adelie = [r for r in rows if r["species"] == "Adelie"]
    assert adelie[1]["change_from_prev_year_g"] == adelie[1]["avg_mass_g"] - adelie[0]["avg_mass_g"]


def test_join_has_no_orphans(conn):
    rows = as_dicts(run_query(conn, "07"))
    assert all(r["scientific_name"] for r in rows)
    adelie = next(r for r in rows if r["species"] == "Adelie")
    assert set(adelie["islands"].split(",")) == {"Biscoe", "Dream", "Torgersen"}


def test_median_matches_python(conn):
    import statistics

    for r in as_dicts(run_query(conn, "08")):
        vals = [
            v for (v,) in conn.execute(
                "SELECT flipper_length_mm FROM penguins WHERE species = ? AND flipper_length_mm IS NOT NULL",
                (r["species"],),
            )
        ]
        assert r["median_flipper_length_mm"] == statistics.median(vals)


def test_histogram_totals(conn):
    rows = as_dicts(run_query(conn, "09"))
    assert sum(r["total"] for r in rows) == 342
    for r in rows:
        assert r["adelie"] + r["chinstrap"] + r["gentoo"] == r["total"]
        assert r["bucket_end_g"] - r["bucket_start_g"] == 499


def test_classifier_accuracy(conn):
    rows = as_dicts(run_query(conn, "10"))
    correct = sum(r["n"] for r in rows if r["actual"] == r["predicted"])
    total = sum(r["n"] for r in rows)
    assert total == 342
    assert correct / total > 0.9
