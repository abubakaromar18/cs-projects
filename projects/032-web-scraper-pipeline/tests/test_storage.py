from dataclasses import replace

from scrapepipe.cleaner import Book
from scrapepipe.storage import Store


def book(sku="B1", **kw):
    b = Book(sku=sku, title="T", url="u", price_cents=1000, currency="GBP", rating=3,
             in_stock=True, stock_count=4, category="Poetry")
    return replace(b, **kw)


def test_upsert_insert_update_unchanged_and_history():
    s = Store()
    assert s.upsert([book(), book("B2")], now="t1") == {"inserted": 2, "updated": 0, "unchanged": 0}
    assert s.upsert([book(), book("B2")], now="t2") == {"inserted": 0, "updated": 0, "unchanged": 2}
    assert s.upsert([book(price_cents=900), book("B2", rating=5)], now="t3") == \
        {"inserted": 0, "updated": 2, "unchanged": 0}
    assert [(h["price_cents"], h["observed_at"]) for h in s.history("b1")] == [(1000, "t1"), (900, "t3")]
    assert len(s.history("B2")) == 1  # rating change doesn't add price history
    row = s.conn.execute("SELECT first_seen, last_seen FROM books WHERE sku='B1'").fetchone()
    assert tuple(row) == ("t1", "t3")


def test_queries_and_summary():
    s = Store()
    s.upsert([book("A", price_cents=500, rating=5, category="Mystery"),
              book("B", price_cents=3000, rating=2),
              book("C", price_cents=1500, rating=4)])
    assert [r["sku"] for r in s.books()] == ["A", "C", "B"]
    assert [r["sku"] for r in s.books(max_price_cents=2000, min_rating=4)] == ["A", "C"]
    assert [r["sku"] for r in s.books(category="poetry")] == ["C", "B"]
    summary = {r["category"]: r["n"] for r in s.category_summary()}
    assert summary == {"Poetry": 2, "Mystery": 1}


def test_transaction_rolls_back_on_error():
    s = Store()
    s.upsert([book("A")])
    bad = book("B", rating=9)  # violates CHECK constraint
    try:
        s.upsert([book("C"), bad])
    except Exception:
        pass
    assert s.count() == 1  # C was rolled back along with B


def test_runs_and_export(tmp_path):
    s = Store(str(tmp_path / "db.sqlite3"))
    rid = s.start_run()
    s.finish_run(rid, pages=2, inserted=1)
    assert s.runs()[0]["pages"] == 2
    s.upsert([book("A"), book("B")])
    assert s.export(str(tmp_path / "out.csv")) == 2
    assert (tmp_path / "out.csv").read_text().splitlines()[0].startswith("sku,")
    assert s.export(str(tmp_path / "out.jsonl")) == 2
    assert '"sku": "A"' in (tmp_path / "out.jsonl").read_text()
