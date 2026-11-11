"""Drive a policy over a reference string and record every step."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .policies import Page, Policy, make_policy


@dataclass(frozen=True)
class Step:
    """What happened on one memory reference."""

    t: int
    page: Page
    hit: bool
    slot: int  # slot that holds ``page`` after this step
    evicted: Page | None  # page thrown out, if a full-memory fault
    frames: tuple[Page | None, ...]  # snapshot after the step
    note: str = ""  # policy-specific state, e.g. clock bits


@dataclass
class Result:
    algorithm: str
    frames: int
    refs: tuple[Page, ...]
    steps: list[Step] = field(default_factory=list)

    @property
    def faults(self) -> int:
        return sum(not s.hit for s in self.steps)

    @property
    def hits(self) -> int:
        return len(self.steps) - self.faults

    @property
    def evictions(self) -> int:
        return sum(s.evicted is not None for s in self.steps)

    @property
    def fault_rate(self) -> float:
        return self.faults / len(self.steps) if self.steps else 0.0

    @property
    def hit_ratio(self) -> float:
        return 1.0 - self.fault_rate if self.steps else 0.0


def simulate(
    refs: Sequence[Page], frames: int, policy: Policy | str, *, record: bool = True
) -> Result:
    """Run ``policy`` over ``refs`` with ``frames`` physical frames.

    Memory starts empty (pure demand paging), so the first reference to each
    distinct page is always a *compulsory* fault, whatever the policy.
    Set ``record=False`` to skip per-step snapshots for big sweeps.
    """
    if frames < 1:
        raise ValueError("frames must be >= 1")
    if isinstance(policy, str):
        policy = make_policy(policy)
    refs = tuple(refs)
    policy.reset(frames, refs)

    memory: list[Page | None] = [None] * frames
    where: dict[Page, int] = {}  # page -> slot: O(1) residency check
    used = 0
    result = Result(policy.name, frames, refs)

    for t, page in enumerate(refs):
        evicted = None
        slot = where.get(page)
        hit = slot is not None
        if hit:
            policy.on_hit(page, slot, t)
        else:
            if used < frames:  # free frame available
                slot = used
                used += 1
            else:
                slot = policy.victim(memory, t)
                if not 0 <= slot < frames:
                    raise RuntimeError(f"{policy.name} returned bad slot {slot}")
                evicted = memory[slot]
                del where[evicted]
            memory[slot] = page
            where[page] = slot
            policy.on_load(page, slot, t)

        if record:
            result.steps.append(
                Step(t, page, hit, slot, evicted, tuple(memory), policy.state())
            )
        else:
            # Keep a lightweight record so faults/hits still work.
            result.steps.append(Step(t, page, hit, slot, evicted, ()))

    return result


def compare(
    refs: Sequence[Page], frames: int, algorithms: Iterable[str]
) -> list[Result]:
    """Run several algorithms on the same input."""
    return [simulate(refs, frames, a) for a in algorithms]
