"""HTTP fetching stage: polite, rate-limited, retrying, robots.txt-aware.

Only the standard library is used (``urllib``). The fetcher is the single
place that touches the network, which keeps every other stage pure and easy
to test.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import urljoin, urlsplit

DEFAULT_USER_AGENT = "scrapepipe/1.0 (+educational scraper)"


class FetchError(Exception):
    """Raised when a page cannot be fetched after all retries."""


class RobotsDisallowed(FetchError):
    """Raised when robots.txt forbids fetching a URL."""


@dataclass
class Response:
    url: str
    status: int
    text: str


@dataclass
class RateLimiter:
    """Ensures at least ``min_interval`` seconds pass between requests to the
    same host. ``clock`` and ``sleep`` are injectable so tests never wait."""

    min_interval: float = 1.0
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    _last: dict[str, float] = field(default_factory=dict)

    def wait(self, host: str) -> float:
        """Block until the host may be hit again; return seconds slept."""
        now = self.clock()
        last = self._last.get(host)
        slept = 0.0
        if last is not None:
            remaining = self.min_interval - (now - last)
            if remaining > 0:
                self.sleep(remaining)
                slept = remaining
        self._last[host] = self.clock() if slept == 0 else now + slept
        return slept


class Fetcher:
    """Fetches pages with retries (exponential backoff), a per-host rate limit
    and robots.txt checks."""

    RETRY_STATUSES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 10.0,
        retries: int = 3,
        backoff: float = 0.5,
        rate_limiter: RateLimiter | None = None,
        respect_robots: bool = True,
        sleep: Callable[[float], None] = time.sleep,
        opener: Callable[..., object] | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.rate_limiter = rate_limiter or RateLimiter(min_interval=0.0)
        self.respect_robots = respect_robots
        self.sleep = sleep
        self._open = opener or urllib.request.urlopen
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self.requests_made = 0

    # -- robots.txt ---------------------------------------------------------
    def _robots_for(self, url: str) -> urllib.robotparser.RobotFileParser | None:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                text = self._raw_get(urljoin(origin, "/robots.txt")).text
                rp.parse(text.splitlines())
            except FetchError:
                rp = None  # no robots.txt (or unreachable) => allow everything
            self._robots[origin] = rp
        return self._robots[origin]

    def allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        rp = self._robots_for(url)
        return True if rp is None else rp.can_fetch(self.user_agent, url)

    # -- HTTP ---------------------------------------------------------------
    def _raw_get(self, url: str) -> Response:
        """One GET attempt-loop with retries; no robots check."""
        host = urlsplit(url).netloc
        last_err: Exception | None = None
        for attempt in range(self.retries + 1):
            self.rate_limiter.wait(host)
            self.requests_made += 1
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            try:
                with self._open(req, timeout=self.timeout) as resp:
                    charset = resp.headers.get_content_charset() or "utf-8"
                    body = resp.read().decode(charset, errors="replace")
                    return Response(resp.geturl(), resp.status, body)
            except urllib.error.HTTPError as e:
                last_err = e
                if e.code not in self.RETRY_STATUSES:
                    break  # 404 etc. won't fix themselves
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last_err = e
            if attempt < self.retries:
                self.sleep(self.backoff * (2**attempt))
        raise FetchError(f"GET {url} failed: {last_err}")

    def get(self, url: str) -> Response:
        if not self.allowed(url):
            raise RobotsDisallowed(f"robots.txt disallows {url}")
        return self._raw_get(url)
