from scrapepipe.demo_site import make_catalog, render_page
from scrapepipe.parser import parse_listing

HTML = """
<html><body>
<article class="product featured" data-sku="X1">
  <img src="a.jpg"/>
  <h3><a href="/book/x1.html" title="A &amp; B: The Full Title">A &amp; B…</a></h3>
  <div><p class="price">£3.50</p></div>
  <p class="rating" data-stars="Four"></p>
  <p class="availability">In stock</p>
  <span class="category">Poetry</span>
</article>
<article class="product" data-sku="X2">
  <h3><a href="x2.html">No title attr</a></h3>
  <p class="price">£9.99</p>
</article>
<article class="ad"><p class="price">£0.00</p></article>
<ul><li class="previous"><a href="page-0.html">prev</a></li>
    <li class="next"><a href="page-3.html">next</a></li></ul>
</body></html>
"""


def test_extracts_records_and_fields():
    page = parse_listing(HTML, "http://localhost/catalogue/page-2.html")
    assert [r.sku for r in page.records] == ["X1", "X2"]  # non-product article ignored
    r = page.records[0]
    assert r.title == "A & B: The Full Title"  # title attr wins, entities decoded
    assert r.url == "http://localhost/book/x1.html"
    assert r.price == "£3.50" and r.rating == "Four"
    assert r.availability == "In stock" and r.category == "Poetry"


def test_falls_back_to_link_text_and_resolves_relative_urls():
    r = parse_listing(HTML, "http://localhost/catalogue/page-2.html").records[1]
    assert r.title == "No title attr"
    assert r.url == "http://localhost/catalogue/x2.html"


def test_next_link_only_from_li_next():
    page = parse_listing(HTML, "http://localhost/catalogue/page-2.html")
    assert page.next_url == "http://localhost/catalogue/page-3.html"


def test_last_page_has_no_next():
    books = make_catalog(12)
    html = render_page(books, page=2, per_page=10)
    page = parse_listing(html, "http://h/catalogue/page-2.html")
    assert page.next_url is None
    assert len(page.records) == 3  # 12 books + 1 injected duplicate


def test_roundtrip_demo_page():
    books = make_catalog(30)
    page = parse_listing(render_page(books, 1, 10), "http://h/catalogue/page-1.html")
    assert len(page.records) == 10
    assert page.records[0].title == books[0]["title"]
