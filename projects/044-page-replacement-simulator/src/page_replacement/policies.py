"""Page replacement policies.

Each policy only answers one question — *which resident page should be evicted?*
— and keeps whatever bookkeeping it needs to answer it. The simulator owns the
physical frames (a fixed list of slots), so a victim is identified by its slot
index. That keeps traces stable: a page stays in the same slot until evicted,
exactly as drawn in OS textbooks.

Hooks, called by the simulator in this order for every reference at time ``t``:

* hit:   ``on_hit(page, slot, t)``
* fault with a free slot: ``on_load(page, slot, t)``
* fault with all slots full: ``victim(frames, t)`` -> slot, then ``on_load``
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections import deque
from typing import Hashable, Sequence

Page = Hashable


class Policy(ABC):
    """Base class. Subclasses set ``name`` and implement :meth:`victim`."""

    name: str = "base"
    description: str = ""

    def reset(self, capacity: int, refs: Sequence[Page]) -> None:
        """Called once before a run. ``refs`` is the whole reference string,
        which only the offline OPT policy is allowed to look at."""
        self.capacity = capacity

    def on_hit(self, page: Page, slot: int, t: int) -> None:  # noqa: B027
        """A resident page was referenced."""

    def on_load(self, page: Page, slot: int, t: int) -> None:  # noqa: B027
        """``page`` was just placed into ``slot`` (after a fault)."""

    @abstractmethod
    def victim(self, frames: Sequence[Page], t: int) -> int:
        """Return the slot index whose page should be evicted. ``frames`` is
        full (no ``None`` entries) when this is called."""

    def state(self) -> str:
        """Optional extra per-step state for traces (e.g. clock ref bits)."""
        return ""


class FIFO(Policy):
    """Evict the page that has been resident longest, regardless of use.

    A queue of slots in load order: O(1) per fault. Simple, but it suffers
    from Belady's anomaly because it is not a *stack algorithm*.
    """

    name = "fifo"
    description = "First-In First-Out: evict the oldest loaded page"

    def reset(self, capacity, refs):
        super().reset(capacity, refs)
        self._queue: deque[int] = deque()

    def on_load(self, page, slot, t):
        self._queue.append(slot)

    def victim(self, frames, t):
        return self._queue.popleft()


class LRU(Policy):
    """Evict the page whose most recent use is furthest in the past.

    Implemented with a last-use timestamp per slot, so a victim search is
    O(frames). Real kernels approximate this (see :class:`Clock`) because
    updating a timestamp on *every* memory access is too expensive in hardware.
    """

    name = "lru"
    description = "Least Recently Used: evict the page unused for longest"

    def reset(self, capacity, refs):
        super().reset(capacity, refs)
        self._last_use = [-1] * capacity

    def on_hit(self, page, slot, t):
        self._last_use[slot] = t

    def on_load(self, page, slot, t):
        self._last_use[slot] = t

    def victim(self, frames, t):
        return min(range(len(frames)), key=self._last_use.__getitem__)


class Clock(Policy):
    """Second-chance / Clock: an O(1)-amortised approximation of LRU.

    Each frame has a reference bit, set whenever its page is used. On a fault
    the hand sweeps around the frames: a set bit is cleared (the page gets a
    "second chance"), and the first frame found with a clear bit is the victim.
    The hand then rests just past the newly loaded page.
    """

    name = "clock"
    description = "Clock / second chance: LRU approximation with reference bits"

    def reset(self, capacity, refs):
        super().reset(capacity, refs)
        self._ref = [False] * capacity
        self._hand = 0

    def on_hit(self, page, slot, t):
        self._ref[slot] = True

    def on_load(self, page, slot, t):
        self._ref[slot] = True
        # Initial fills happen in slot order; afterwards the hand points at the
        # slot just replaced. Either way, advance past the slot we just filled.
        self._hand = (slot + 1) % self.capacity

    def victim(self, frames, t):
        while self._ref[self._hand]:
            self._ref[self._hand] = False
            self._hand = (self._hand + 1) % self.capacity
        return self._hand

    def state(self):
        bits = "".join("1" if b else "0" for b in self._ref)
        return f"bits={bits} hand={self._hand}"


class OPT(Policy):
    """Belady's optimal (MIN) policy: evict the page whose next use is
    furthest in the future (or never). Not implementable online since it
    needs the future, but it is the lower bound every other policy is
    measured against.

    We precompute ``next_use[i]`` — the index of the next reference to
    ``refs[i]`` — in one right-to-left pass, so each fault costs O(frames).
    """

    name = "opt"
    description = "Optimal (Belady's MIN): evict the page used furthest in future"

    def reset(self, capacity, refs):
        super().reset(capacity, refs)
        self._next_use: list[float] = [math.inf] * len(refs)
        seen: dict[Page, int] = {}
        for i in range(len(refs) - 1, -1, -1):
            self._next_use[i] = seen.get(refs[i], math.inf)
            seen[refs[i]] = i
        # next_for_slot[s] = when the page in slot s will next be needed
        self._next_for_slot: list[float] = [math.inf] * capacity

    def on_hit(self, page, slot, t):
        self._next_for_slot[slot] = self._next_use[t]

    def on_load(self, page, slot, t):
        self._next_for_slot[slot] = self._next_use[t]

    def victim(self, frames, t):
        # max() returns the first maximal slot, so ties (e.g. several pages
        # never used again) break deterministically toward the lowest slot.
        return max(range(len(frames)), key=self._next_for_slot.__getitem__)


POLICIES: dict[str, type[Policy]] = {p.name: p for p in (FIFO, LRU, Clock, OPT)}


def make_policy(name: str) -> Policy:
    """Instantiate a policy by its short name (case-insensitive)."""
    try:
        return POLICIES[name.lower()]()
    except KeyError:
        raise ValueError(
            f"unknown algorithm {name!r}; choose from {', '.join(POLICIES)}"
        ) from None
