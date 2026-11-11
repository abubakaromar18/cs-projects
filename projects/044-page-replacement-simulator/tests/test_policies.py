"""Known answers plus cross-checks against tiny independent reference models."""

import itertools
import random
from collections import OrderedDict

import pytest

from page_replacement import POLICIES, make_policy, simulate
from page_replacement.refstrings import BELADY, TEXTBOOK, loop


# --- textbook answers -------------------------------------------------------

@pytest.mark.parametrize(
    "algo, frames, expected",
    [
        ("fifo", 3, 15), ("lru", 3, 12), ("opt", 3, 9),   # Silberschatz
        ("fifo", 4, 10), ("lru", 4, 8), ("opt", 4, 8),
        ("clock", 3, 14),
    ],
)
def test_textbook_string(algo, frames, expected):
    assert simulate(TEXTBOOK, frames, algo).faults == expected


def test_belady_string_fifo():
    assert simulate(BELADY, 3, "fifo").faults == 9
    assert simulate(BELADY, 4, "fifo").faults == 10


# --- independent reference implementations ---------------------------------
# Deliberately written in a different style (sets, OrderedDict, brute-force
# future scan) so a shared bug is unlikely.

def ref_fifo(refs, k):
    mem, order, faults = set(), [], 0
    for p in refs:
        if p not in mem:
            faults += 1
            if len(mem) == k:
                mem.discard(order.pop(0))
            mem.add(p)
            order.append(p)
    return faults


def ref_lru(refs, k):
    mem, faults = OrderedDict(), 0
    for p in refs:
        if p in mem:
            mem.move_to_end(p)
        else:
            faults += 1
            if len(mem) == k:
                mem.popitem(last=False)
            mem[p] = True
    return faults


def ref_opt(refs, k):
    mem, faults = set(), 0
    for t, p in enumerate(refs):
        if p in mem:
            continue
        faults += 1
        if len(mem) == k:
            def next_use(q):
                for j in range(t + 1, len(refs)):
                    if refs[j] == q:
                        return j
                return float("inf")
            mem.discard(max(mem, key=next_use))
        mem.add(p)
    return faults


def ref_clock(refs, k):
    pages, bits, hand, faults = [None] * k, [0] * k, 0, 0
    for p in refs:
        if p in pages:
            bits[pages.index(p)] = 1
            continue
        faults += 1
        while pages[hand] is not None and bits[hand]:
            bits[hand] = 0
            hand = (hand + 1) % k
        pages[hand], bits[hand] = p, 1
        hand = (hand + 1) % k
    return faults


REFERENCE = {"fifo": ref_fifo, "lru": ref_lru, "opt": ref_opt, "clock": ref_clock}


@pytest.mark.parametrize("algo", list(REFERENCE))
def test_matches_reference_on_random_strings(algo):
    rng = random.Random(1234)
    for _ in range(300):
        refs = [rng.randrange(rng.randint(1, 9)) for _ in range(rng.randint(0, 40))]
        k = rng.randint(1, 6)
        assert simulate(refs, k, algo).faults == REFERENCE[algo](refs, k), (refs, k)


# --- properties --------------------------------------------------------------

def test_opt_is_optimal_and_never_worse():
    rng = random.Random(99)
    for _ in range(200):
        refs = [rng.randrange(7) for _ in range(30)]
        for k in range(1, 6):
            opt = simulate(refs, k, "opt").faults
            for algo in ("fifo", "lru", "clock"):
                assert opt <= simulate(refs, k, algo).faults


def test_opt_matches_exhaustive_search_on_tiny_inputs():
    # Try every possible eviction choice; OPT must equal the true minimum.
    def best(refs, k, t=0, mem=frozenset()):
        if t == len(refs):
            return 0
        p = refs[t]
        if p in mem:
            return best(refs, k, t + 1, mem)
        if len(mem) < k:
            return 1 + best(refs, k, t + 1, mem | {p})
        return 1 + min(best(refs, k, t + 1, (mem - {v}) | {p}) for v in mem)

    for refs in itertools.product(range(4), repeat=7):
        for k in (1, 2, 3):
            assert simulate(refs, k, "opt").faults == best(refs, k)


@pytest.mark.parametrize("algo", list(POLICIES))
def test_compulsory_faults_lower_bound(algo):
    refs = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]
    for k in range(1, 10):
        assert simulate(refs, k, algo).faults >= len(set(refs))
    # Enough frames for everything: only compulsory faults.
    assert simulate(refs, len(set(refs)), algo).faults == len(set(refs))


@pytest.mark.parametrize("algo", list(POLICIES))
def test_one_frame_faults_on_every_change(algo):
    refs = [1, 1, 2, 2, 2, 3, 1, 1]
    assert simulate(refs, 1, algo).faults == 4


def test_loop_is_worst_case_for_lru():
    refs = loop(50, 5)
    assert simulate(refs, 4, "lru").faults == 50
    assert simulate(refs, 4, "opt").faults < 50


def test_make_policy_rejects_unknown():
    with pytest.raises(ValueError, match="unknown algorithm"):
        make_policy("mru")
    assert make_policy("LRU").name == "lru"
