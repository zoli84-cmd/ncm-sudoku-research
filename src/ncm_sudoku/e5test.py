"""E5 TEST pair screening, internal collisions and eligibility (protocol §4.1).

Candidate pair solutions are screened against a precomputed index of external
canonical keys (gate, CAL, PROBE-TRAIN, PROBE-VAL, WP2 TEST, released hard set,
the E5 PROBE-TRAIN and PROBE-VAL pairs); a colliding candidate is rejected and
the raw index steps to the next candidate until N pairs are accepted. A
generation error propagates and stops the run; it never silently becomes a step
to the next index. After the accepted set is fixed, internal collisions among
its own solution orbits are only logged, never replaced (D99's internal
replacement does not apply to TEST). Eligibility for claims A and B is decided
from candidate-mask labels alone, before any model output is read.
"""

from typing import Callable

import numpy as np

from ncm_sudoku.e5pairs import Pair
from ncm_sudoku.symmetry import canonical_form


def canonical_key(solution: np.ndarray) -> bytes:
    """Exact canonical form of a solution grid (the key `symmetry.screen_canonical` uses)."""
    return canonical_form(solution)


def external_index(entries: dict[str, list[tuple[str, np.ndarray]]]) -> dict[bytes, str]:
    """Canonical key -> first external id, built once over every named collection."""
    index: dict[bytes, str] = {}
    for items in entries.values():
        for pid, solution in items:
            key = canonical_key(solution)
            if key not in index:
                index[key] = pid
    return index


def screen_pairs(make_pair: Callable[[int], Pair], index: dict[bytes, str], n: int) -> tuple[list[Pair], list[dict]]:
    """Raw index from 0: a pair whose solution's canonical key is in `index` is
    rejected and logged; accepted pairs accumulate until the n-th is reached.
    Any exception `make_pair` raises propagates unchanged."""
    accepted: list[Pair] = []
    log: list[dict] = []
    i = 0
    while len(accepted) < n:
        pair = make_pair(i)
        colliding_id = index.get(canonical_key(pair.solution))
        ok = colliding_id is None
        log.append({"index": i, "pair_id": pair.pair_id, "accepted": ok,
                     "reason": None if ok else "external_collision", "colliding_id": colliding_id})
        if ok:
            accepted.append(pair)
        i += 1
    return accepted, log


def internal_collisions(pairs: list[Pair]) -> list[tuple[str, str]]:
    """Every pair of pair ids whose solutions share a canonical-form orbit."""
    by_key: dict[bytes, list[str]] = {}
    for p in pairs:
        by_key.setdefault(canonical_key(p.solution), []).append(p.pair_id)
    out: list[tuple[str, str]] = []
    for ids in by_key.values():
        if len(ids) >= 2:
            out += [(ids[a], ids[b]) for a in range(len(ids)) for b in range(a + 1, len(ids))]
    return out


def eligibility(mask: np.ndarray, empty: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Members stacked a then b. `elig_a` = at least one cell empty in both
    members with a digit that is a candidate in exactly one of them (a
    discordant bit); `elig_b` = at least one cell empty in both members."""
    ma, mb, ea, eb = mask[:n], mask[n:], empty[:n], empty[n:]
    both = ea & eb
    disc = both[..., None] & (ma != mb)
    return disc.any(axis=(1, 2)), both.any(axis=1)
