"""Breach-list checks.

* :func:`in_local_list` checks a bundled (or user-supplied) list of known
  leaked passwords. Lookups compare SHA-1 digests so a user-supplied list may
  be stored either as plaintext or as hex SHA-1 hashes.

* :func:`pwned_count` optionally queries the Have I Been Pwned "Pwned
  Passwords" range API using **k-anonymity**: only the first 5 hex characters
  of the SHA-1 hash leave the machine, and the match is done locally. The
  password itself is never sent. This is opt-in (``--online``) and the HTTP
  fetcher is injectable so tests never touch the network.
"""

from __future__ import annotations

import hashlib
import re
import urllib.request
from pathlib import Path
from typing import Callable, Iterable

from .patterns import load_wordlist

HIBP_RANGE_URL = "https://api.pwnedpasswords.com/range/{prefix}"
_HEX40 = re.compile(r"^[0-9a-fA-F]{40}$")

Fetcher = Callable[[str], str]


def sha1_hex(password: str) -> str:
    return hashlib.sha1(password.encode("utf-8")).hexdigest().upper()


def load_hash_set(lines: Iterable[str]) -> set[str]:
    """Turn lines of plaintext passwords or SHA-1 hex digests into a hash set."""
    out: set[str] = set()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line.upper() if _HEX40.match(line) else sha1_hex(line))
    return out


def _bundled_hashes() -> set[str]:
    return load_hash_set(load_wordlist("common_passwords.txt"))


def in_local_list(password: str, extra_list: Path | None = None) -> bool:
    """True if *password* appears in the bundled list or *extra_list*."""
    digest = sha1_hex(password)
    if digest in _bundled_hashes():
        return True
    if extra_list is not None:
        with extra_list.open(encoding="utf-8", errors="ignore") as fh:
            return digest in load_hash_set(fh)
    return False


def _http_fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": "password-strength-checker (educational)",
        "Add-Padding": "true",  # HIBP pads responses to hide result size
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8")


def pwned_count(password: str, fetch: Fetcher = _http_fetch) -> int:
    """Return how many times *password* appears in HIBP (0 if never seen)."""
    digest = sha1_hex(password)
    prefix, suffix = digest[:5], digest[5:]
    body = fetch(HIBP_RANGE_URL.format(prefix=prefix))
    for line in body.splitlines():
        tail, _, count = line.strip().partition(":")
        if tail.upper() == suffix:
            return int(count or 0)  # padded entries have count 0
    return 0
