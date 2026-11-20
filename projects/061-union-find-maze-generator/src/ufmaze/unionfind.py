"""Disjoint-set (union-find) with path compression and union by rank.

With both optimisations, a sequence of m operations on n elements runs in
O(m * alpha(n)) time, where alpha is the inverse Ackermann function --
effectively constant for any input that fits in the universe.
"""

from __future__ import annotations


class UnionFind:
    """A disjoint-set forest over the integers ``0 .. n-1``."""

    __slots__ = ("_parent", "_rank", "_size", "components")

    def __init__(self, n: int) -> None:
        if n < 0:
            raise ValueError("n must be non-negative")
        self._parent = list(range(n))
        self._rank = [0] * n
        self._size = [1] * n
        #: Number of disjoint sets currently in the structure.
        self.components = n

    def __len__(self) -> int:
        return len(self._parent)

    def find(self, x: int) -> int:
        """Return the representative of ``x``'s set.

        Iterative two-pass path compression: first walk up to the root, then
        point every node on the path directly at it. Iteration avoids Python's
        recursion limit on large, unbalanced inputs.
        """
        root = x
        parent = self._parent
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    def union(self, a: int, b: int) -> bool:
        """Merge the sets containing ``a`` and ``b``.

        Returns ``True`` if a merge happened, ``False`` if they were already
        in the same set (which, for Kruskal, means the edge would form a cycle).
        """
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        # Union by rank: hang the shallower tree under the deeper one so tree
        # height stays O(log n) even before path compression kicks in.
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        self._size[ra] += self._size[rb]
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1
        self.components -= 1
        return True

    def connected(self, a: int, b: int) -> bool:
        return self.find(a) == self.find(b)

    def size_of(self, x: int) -> int:
        """Number of elements in ``x``'s set."""
        return self._size[self.find(x)]
