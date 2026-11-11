"""A frequency-aware prefix tree (trie) for autocomplete.

Each node maps one character to a child node. A node that ends a stored word
carries that word's frequency (> 0). Lookups walk one edge per character, so
finding a prefix costs O(m) for a prefix of length m regardless of how many
words are stored.

Ranking: ``suggest(prefix, k)`` returns the k most frequent words that start
with ``prefix``, ties broken alphabetically. To keep this fast on large
vocabularies, every node caches ``best`` — the highest frequency of any word
in its subtree. A best-first search over a heap keyed by ``best`` visits the
most promising branches first and stops as soon as k words are produced,
instead of enumerating the whole subtree.
"""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field
from typing import Iterable, Iterator


@dataclass
class _Node:
    children: dict[str, "_Node"] = field(default_factory=dict)
    freq: int = 0  # > 0 iff a word ends here
    best: int = 0  # max freq of any word in this subtree (including self)

    def recompute_best(self) -> None:
        self.best = max([self.freq, *(c.best for c in self.children.values())])


class Trie:
    """Prefix tree storing words with integer frequencies."""

    def __init__(self, words: Iterable[str] | None = None, *, case_sensitive: bool = False):
        self._root = _Node()
        self._size = 0
        self.case_sensitive = case_sensitive
        if words is not None:
            for w in words:
                self.insert(w)

    # ----------------------------------------------------------------- helpers
    def _norm(self, s: str) -> str:
        return s if self.case_sensitive else s.lower()

    def _find(self, prefix: str) -> _Node | None:
        node = self._root
        for ch in prefix:
            node = node.children.get(ch)
            if node is None:
                return None
        return node

    # ---------------------------------------------------------------- mutation
    def insert(self, word: str, freq: int = 1) -> int:
        """Add ``freq`` to ``word``'s count (creating it). Returns the new count."""
        if not isinstance(word, str) or not word:
            raise ValueError("word must be a non-empty string")
        if freq <= 0:
            raise ValueError("freq must be positive")
        word = self._norm(word)
        path = [self._root]
        for ch in word:
            path.append(path[-1].children.setdefault(ch, _Node()))
        end = path[-1]
        if end.freq == 0:
            self._size += 1
        end.freq += freq
        # Only increases happen here, so updating `best` up the path is cheap.
        for node in path:
            node.best = max(node.best, end.freq)
        return end.freq

    def remove(self, word: str) -> bool:
        """Delete ``word`` entirely. Returns False if it was not present.

        Empty branches are pruned and the cached ``best`` values along the path
        are recomputed bottom-up, since removing the maximum can lower them.
        """
        word = self._norm(word)
        path = [self._root]
        for ch in word:
            nxt = path[-1].children.get(ch)
            if nxt is None:
                return False
            path.append(nxt)
        if path[-1].freq == 0:
            return False
        path[-1].freq = 0
        self._size -= 1
        for i in range(len(word), 0, -1):
            node, parent = path[i], path[i - 1]
            if node.freq == 0 and not node.children:
                del parent.children[word[i - 1]]
            else:
                node.recompute_best()
        self._root.recompute_best()
        return True

    # ------------------------------------------------------------------ queries
    def frequency(self, word: str) -> int:
        node = self._find(self._norm(word))
        return node.freq if node else 0

    def __contains__(self, word: object) -> bool:
        return isinstance(word, str) and self.frequency(word) > 0

    def __len__(self) -> int:
        return self._size

    def has_prefix(self, prefix: str) -> bool:
        node = self._find(self._norm(prefix))
        return node is not None and node.best > 0

    def words_with_prefix(self, prefix: str = "") -> Iterator[tuple[str, int]]:
        """Yield every (word, freq) under ``prefix`` in lexicographic order."""
        prefix = self._norm(prefix)
        start = self._find(prefix)
        if start is None:
            return
        # Iterative DFS; children pushed in reverse so pops come out sorted.
        stack: list[tuple[str, _Node]] = [(prefix, start)]
        while stack:
            text, node = stack.pop()
            if node.freq:
                yield text, node.freq
            for ch in sorted(node.children, reverse=True):
                stack.append((text + ch, node.children[ch]))

    def __iter__(self) -> Iterator[str]:
        return (w for w, _ in self.words_with_prefix(""))

    def suggest(self, prefix: str, k: int = 5) -> list[tuple[str, int]]:
        """Top-``k`` completions of ``prefix`` by frequency (desc), then alphabetically.

        Best-first search: the heap holds both *subtrees* (priority = cached
        ``best``) and *words* (priority = their own freq). A word popped from the
        heap is guaranteed to beat everything still in it, because every
        remaining subtree's words are bounded above by its ``best``.
        """
        if k <= 0:
            return []
        prefix = self._norm(prefix)
        start = self._find(prefix)
        if start is None or start.best == 0:
            return []
        # Entries: (-priority, text, kind, tiebreak, node). kind 0 = word, 1 = subtree,
        # so at equal priority a finished word sorts before an unexplored subtree.
        # Note a subtree's text is a prefix of all its words, so it sorts no later
        # than any of them — alphabetical tie-breaking stays correct.
        counter = itertools.count()
        heap: list = [(-start.best, prefix, 1, next(counter), start)]
        out: list[tuple[str, int]] = []
        while heap and len(out) < k:
            neg, text, kind, _, node = heapq.heappop(heap)
            if kind == 0:
                out.append((text, -neg))
                continue
            if node.freq:
                heapq.heappush(heap, (-node.freq, text, 0, next(counter), None))
            for ch, child in node.children.items():
                heapq.heappush(heap, (-child.best, text + ch, 1, next(counter), child))
        return out

    def longest_common_prefix(self, prefix: str = "") -> str:
        """Extend ``prefix`` while the trie has exactly one way forward (tab-completion)."""
        prefix = self._norm(prefix)
        node = self._find(prefix)
        if node is None:
            return prefix
        while node.freq == 0 and len(node.children) == 1:
            (ch, node), = node.children.items()
            prefix += ch
        return prefix

    def node_count(self) -> int:
        """Total nodes including the root — a measure of prefix sharing."""
        count, stack = 0, [self._root]
        while stack:
            n = stack.pop()
            count += 1
            stack.extend(n.children.values())
        return count

    # ---------------------------------------------------------- serialization
    def to_dict(self) -> dict:
        return {
            "case_sensitive": self.case_sensitive,
            "words": dict(self.words_with_prefix("")),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Trie":
        t = cls(case_sensitive=bool(data.get("case_sensitive", False)))
        for word, freq in data.get("words", {}).items():
            t.insert(word, int(freq))
        return t
