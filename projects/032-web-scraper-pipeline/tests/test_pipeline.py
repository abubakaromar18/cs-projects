"""End-to-end tests against the demo site on 127.0.0.1 (no internet needed)."""

import pytest

from scrapepipe.cli import main
from scrapepipe.demo_site import DemoSite
from scrapepipe.fetcher import FetchError, Fetcher, RobotsDisallowed
from scrapepipe.pipeline import Pipeline
from scrapepipe.storage import Store


@pytest.fixture
def site():
    with DemoSite(n_books=45, per_page=10) as s:
        yield s


def fast_fetcher(**kw):
    return Fetcher(sleep=lambda _: None, timeout=5, **kw)


def test_full_run_is_idempotent_and_tracks_changes(site):
    pipe = Pipeline(Store(), fast_fetcher())
    r1 = pipe.run(site.start_url)
    # 45 books + 1 duplicate = 46 rows over 5 pages; 1 bad price + 1 dup rejected
    assert (r1.pages, r1.inserted, r1.rejected) == (5, 44, 2)
    assert r1.reject_reasons == {"unparseable price": 1, "duplicate sku": 1}

    r2 = pipe.run(site.start_url)
    assert (r2.inserted, r2.updated, r2.unchanged) == (0, 0, 44)

    site.state["price_shift"] = 1
    r3 = pipe.run(site.start_url)
    assert r3.updated == 44
    assert len(pipe.store.history("B001")) == 2
    assert len(pipe.store.runs()) == 3


def test_cleaned_values_in_store(site):
    pipe = Pipeline(Store(), fast_fetcher())
    pipe.run(site.start_url)
    rows = {r["sku"]: r for r in pipe.store.books()}
    assert rows["B011"]["title"] == "The Whitespace Edition"
    assert rows["B021"]["price_cents"] == 120450
    assert "B004" not in rows  # missing price


def test_follows_redirect_from_root(site):
    r = Pipeline(Store(), fast_fetcher()).run(site.base_url + "/")
    assert (r.pages, r.inserted, r.errors) == (5, 44, [])


def test_max_pages_bounds_crawl(site):
    r = Pipeline(Store(), fast_fetcher(), max_pages=2).run(site.start_url)
    assert r.pages == 2 and (r.inserted, r.rejected) == (19, 1)  # B004 has no price


def test_retries_transient_errors(site):
    site.state["fail_next"] = 2  # two 503s, then success
    f = fast_fetcher(retries=3)
    assert f.get(site.start_url).status == 200


def test_gives_up_after_retries_and_records_error(site):
    site.state["fail_next"] = 100
    pipe = Pipeline(Store(), fast_fetcher(retries=1))
    r = pipe.run(site.start_url)
    assert r.pages == 0 and r.errors
    assert pipe.store.runs()[0]["error"]


def test_404_is_not_retried(site):
    f = fast_fetcher(retries=5)
    with pytest.raises(FetchError):
        f.get(site.base_url + "/nope")
    assert f.requests_made == 2  # robots.txt + one attempt


def test_respects_robots_txt(site):
    f = fast_fetcher()
    with pytest.raises(RobotsDisallowed):
        f.get(site.base_url + "/private/data.html")
    assert fast_fetcher(respect_robots=False).get(site.base_url + "/private/x").status == 200


def test_cli_run_query_and_export(site, tmp_path, capsys):
    db = str(tmp_path / "b.db")
    assert main(["--db", db, "run", site.start_url, "--delay", "0"]) == 0
    assert "44 new" in capsys.readouterr().out
    assert main(["--db", db, "query", "--max-price", "20", "--min-rating", "4"]) == 0
    assert "SKU" in capsys.readouterr().out
    assert main(["--db", db, "stats"]) == 0
    assert "44 books" in capsys.readouterr().out
    assert main(["--db", db, "export", str(tmp_path / "o.csv")]) == 0
    assert main(["--db", db, "schedule", site.start_url, "--every", "0.01", "--runs", "2", "--delay", "0"]) == 0
    assert "stopped after 2 runs (0 failures)" in capsys.readouterr().out
