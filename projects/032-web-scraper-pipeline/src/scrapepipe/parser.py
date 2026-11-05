"""Extraction stage: turn listing-page HTML into raw records.

Uses ``html.parser.HTMLParser``, an event-driven (SAX-style) tokenizer. We
keep a tiny state machine: when we enter an ``<article class="product">`` we
start collecting fields, and close the record when that article ends. This is
far more robust than regexes over HTML because the tokenizer handles quoting,
entities, attribute order and whitespace for us.

Expected markup (the bundled demo site produces exactly this)::

    <article class="product" data-sku="B001">
      <h3><a href="/book/b001.html" title="Full Title">Short…</a></h3>
      <p class="price">£51.77</p>
      <p class="rating" data-stars="Three"></p>
      <p class="availability">  In stock (22 available) </p>
      <span class="category">Poetry</span>
    </article>
    ...
    <li class="next"><a href="page-2.html">next</a></li>
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin


@dataclass
class RawRecord:
    """Exactly what was on the page, as strings. Cleaning happens later."""

    sku: str = ""
    title: str = ""
    url: str = ""
    price: str = ""
    rating: str = ""
    availability: str = ""
    category: str = ""


@dataclass
class ParsedPage:
    records: list[RawRecord] = field(default_factory=list)
    next_url: str | None = None


class _ListingParser(HTMLParser):
    # Map a CSS class on a <p>/<span> to the RawRecord field it fills.
    TEXT_FIELDS = {"price": "price", "availability": "availability", "category": "category"}

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.page = ParsedPage()
        self._current: RawRecord | None = None
        self._article_depth = 0  # nesting depth of tags inside the article
        self._capture: str | None = None  # field currently receiving text
        self._in_next = False

    @staticmethod
    def _classes(attrs: dict[str, str | None]) -> set[str]:
        return set((attrs.get("class") or "").split())

    def handle_starttag(self, tag, attrs_list):
        attrs = dict(attrs_list)
        classes = self._classes(attrs)

        if tag == "li" and "next" in classes:
            self._in_next = True
        elif tag == "a" and self._in_next and attrs.get("href"):
            self.page.next_url = urljoin(self.base_url, attrs["href"])

        if self._current is None:
            if tag == "article" and "product" in classes:
                self._current = RawRecord(sku=attrs.get("data-sku") or "")
                self._article_depth = 1
            return

        self._article_depth += 1
        if tag == "a" and attrs.get("href") and not self._current.url:
            self._current.url = urljoin(self.base_url, attrs["href"])
            # Titles are often truncated in link text; prefer the title attr.
            if attrs.get("title"):
                self._current.title = attrs["title"]
            else:
                self._capture = "title"
        elif "rating" in classes:
            self._current.rating = attrs.get("data-stars") or ""
        else:
            for cls, fname in self.TEXT_FIELDS.items():
                if cls in classes:
                    self._capture = fname

    def handle_endtag(self, tag):
        if tag == "li":
            self._in_next = False
        if self._current is None:
            return
        self._capture = None
        self._article_depth -= 1
        if self._article_depth == 0:  # closed the <article>
            self.page.records.append(self._current)
            self._current = None

    def handle_startendtag(self, tag, attrs):
        # Void elements like <img/> don't change depth.
        self.handle_starttag(tag, attrs)
        if self._current is not None:
            self._article_depth -= 1

    def handle_data(self, data):
        if self._current is not None and self._capture:
            old = getattr(self._current, self._capture)
            setattr(self._current, self._capture, old + data)


def parse_listing(html: str, base_url: str) -> ParsedPage:
    """Parse one listing page into raw records plus the next-page URL."""
    p = _ListingParser(base_url)
    p.feed(html)
    p.close()
    return p.page
