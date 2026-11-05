"""A self-contained demo bookstore served on localhost.

The pipeline is meant to be pointed at sites you own or that permit
scraping; this generator gives you one that runs offline. It deliberately
includes messy data (extra whitespace, a missing price, a duplicate SKU,
thousand separators) so the cleaning stage has something to do, and a
``robots.txt`` that disallows ``/private/``.

``price_shift`` lets tests (or you) simulate prices changing between runs.
"""

from __future__ import annotations

import html
import random
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CATEGORIES = ["Poetry", "Mystery", "Science", "History", "Fantasy", "Travel"]
WORDS = ("silent river garden machine shadow empire winter atlas quantum lantern "
         "harbor echo meridian cipher orchard velvet summit compass ember tide").split()
STARS = ["One", "Two", "Three", "Four", "Five"]


def make_catalog(n: int = 45, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    books = []
    for i in range(1, n + 1):
        title = " ".join(rng.sample(WORDS, rng.randint(2, 4))).title()
        stock = rng.choice([0, rng.randint(1, 30)])
        books.append({
            "sku": f"b{i:03d}",
            "title": f"The {title}",
            "price": f"£{rng.uniform(5, 60):.2f}",
            "stars": rng.choice(STARS),
            "availability": f"  In stock ({stock} available) " if stock else "Out of stock",
            "category": rng.choice(CATEGORIES),
        })
    # Inject dirty data the cleaner must handle.
    dirty = {3: ("price", ""),                                  # missing price -> rejected
             10: ("title", "  The   Whitespace\n  Edition  "),     # messy whitespace
             20: ("price", "£1,204.50")}                            # thousands separator
    for i, (key, value) in dirty.items():
        if i < len(books):
            books[i][key] = value
    books.append(dict(books[0]))                 # duplicate SKU -> rejected
    return books


def render_page(books: list[dict], page: int, per_page: int, price_shift: int = 0) -> str:
    total_pages = max(1, -(-len(books) // per_page))
    chunk = books[(page - 1) * per_page: page * per_page]
    items = []
    for b in chunk:
        price = b["price"]
        if price_shift and price:
            num = float(price.lstrip("£").replace(",", "")) + price_shift
            price = f"£{num:,.2f}"
        short = b["title"] if len(b["title"]) < 22 else b["title"][:20] + "…"
        items.append(f"""
  <article class="product" data-sku="{b['sku']}">
    <img src="/img/{b['sku']}.jpg" alt=""/>
    <h3><a href="/book/{b['sku']}.html" title="{html.escape(b['title'])}">{html.escape(short)}</a></h3>
    <p class="price">{price}</p>
    <p class="rating" data-stars="{b['stars']}"></p>
    <p class="availability">{b['availability']}</p>
    <span class="category">{b['category']}</span>
  </article>""")
    nav = ""
    if page < total_pages:
        nav = f'<ul class="pager"><li class="next"><a href="page-{page + 1}.html">next</a></li></ul>'
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>Books p{page}</title></head>"
            f"<body><h1>Demo Books &amp; Co.</h1><section>{''.join(items)}</section>{nav}</body></html>")


ROBOTS = "User-agent: *\nDisallow: /private/\n"


def make_handler(books: list[dict], per_page: int, state: dict):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep test output quiet
            pass

        def _send(self, code: int, body: str, ctype: str = "text/html; charset=utf-8"):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            state["hits"] = state.get("hits", 0) + 1
            path = self.path.split("?")[0]
            if path == "/robots.txt":
                return self._send(200, ROBOTS, "text/plain")
            if state.get("fail_next", 0) > 0:
                state["fail_next"] -= 1
                return self._send(503, "try later")
            if path in ("/", "/index.html"):
                # Redirect (not serve) so relative links resolve against the real URL.
                self.send_response(301)
                self.send_header("Location", "/catalogue/page-1.html")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if path.startswith("/catalogue/page-") and path.endswith(".html"):
                try:
                    n = int(path[len("/catalogue/page-"):-5])
                except ValueError:
                    n = 0
                total = max(1, -(-len(books) // per_page))
                if 1 <= n <= total:
                    return self._send(200, render_page(books, n, per_page, state.get("price_shift", 0)))
            if path.startswith("/private/"):
                return self._send(200, "<p>secret</p>")
            return self._send(404, "not found")

    return Handler


class DemoSite:
    """Run the demo site in a background thread: ``with DemoSite() as site: ...``"""

    def __init__(self, host: str = "127.0.0.1", port: int = 0, n_books: int = 45, per_page: int = 10):
        self.books = make_catalog(n_books)
        self.state: dict = {}
        self.server = ThreadingHTTPServer((host, port), make_handler(self.books, per_page, self.state))
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}"

    @property
    def start_url(self) -> str:
        return self.base_url + "/catalogue/page-1.html"

    def start(self) -> "DemoSite":
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()
