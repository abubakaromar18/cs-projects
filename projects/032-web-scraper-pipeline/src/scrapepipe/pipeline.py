"""Orchestration: fetch -> parse -> clean -> store (classic ETL).

The crawl follows "next" links breadth-first from a start URL, with a
visited set to guarantee termination on cyclic pagination and a page cap
to bound work. Crawling is restricted to the start URL's host.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from .cleaner import clean_all
from .fetcher import FetchError, Fetcher
from .parser import parse_listing
from .storage import Store

log = logging.getLogger("scrapepipe")


@dataclass
class RunResult:
    run_id: int
    pages: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    rejected: int = 0
    errors: list[str] = field(default_factory=list)
    reject_reasons: dict[str, int] = field(default_factory=dict)

    def summary(self) -> str:
        s = (f"run #{self.run_id}: {self.pages} pages, {self.inserted} new, "
             f"{self.updated} updated, {self.unchanged} unchanged, {self.rejected} rejected")
        if self.errors:
            s += f", {len(self.errors)} errors"
        return s


class Pipeline:
    def __init__(self, store: Store, fetcher: Fetcher | None = None, max_pages: int = 50):
        self.store = store
        self.fetcher = fetcher or Fetcher()
        self.max_pages = max_pages

    def crawl(self, start_url: str):
        """Yield ``(url, ParsedPage)`` for each listing page reachable via next links."""
        host = urlsplit(start_url).netloc
        queue, seen = deque([start_url]), {start_url}
        pages = 0
        while queue and pages < self.max_pages:
            url = queue.popleft()
            resp = self.fetcher.get(url)  # may raise FetchError
            pages += 1
            page = parse_listing(resp.text, resp.url)
            yield url, page
            nxt = page.next_url
            if nxt and nxt not in seen and urlsplit(nxt).netloc == host:
                seen.add(nxt)
                queue.append(nxt)

    def run(self, start_url: str) -> RunResult:
        run_id = self.store.start_run()
        result = RunResult(run_id)
        raws = []
        try:
            for url, page in self.crawl(start_url):
                result.pages += 1
                raws.extend(page.records)
                log.info("parsed %s: %d records", url, len(page.records))
        except FetchError as e:
            # Partial crawl: keep what we have, but record the failure.
            result.errors.append(str(e))
            log.warning("%s", e)

        books, rejects = clean_all(raws)
        result.rejected = len(rejects)
        for _, reason in rejects:
            key = reason.split(" '")[0]
            result.reject_reasons[key] = result.reject_reasons.get(key, 0) + 1

        stats = self.store.upsert(books)
        result.inserted, result.updated, result.unchanged = (
            stats["inserted"], stats["updated"], stats["unchanged"])
        self.store.finish_run(
            run_id, pages=result.pages, inserted=result.inserted, updated=result.updated,
            unchanged=result.unchanged, rejected=result.rejected,
            error="; ".join(result.errors) or None,
        )
        return result
