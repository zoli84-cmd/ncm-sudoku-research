"""Logical labels: direct-rule candidate mask and synchronous single waves (plan §5).

Labels are computed from the puzzle only; the reference solution is never read.
"""

from dataclasses import dataclass

import numpy as np

from ncm_sudoku.grid import PEERS, UNITS
from ncm_sudoku.solve import check_puzzle

STUCK = -1
CENSORED = -2


class ConflictError(ValueError):
    """Inconsistent input or conflicting derivations within one wave."""


@dataclass(frozen=True)
class WaveResult:
    depth: np.ndarray  # (81,) int16: 0 given, k >= 1 first wave, STUCK, or CENSORED
    rules: tuple[frozenset[str], ...]  # per cell, subset of {"naked", "hidden"}
    n_waves: int
    values: np.ndarray  # (81,) int8 grid after the last wave (0 where not determined)


def candidate_mask(grid) -> np.ndarray:
    """(81, 9) bool; bit d-1 is set iff d is absent among the filled peers of a blank cell."""
    g = np.asarray(grid)
    mask = np.zeros((81, 9), dtype=bool)
    for c in range(81):
        if g[c] == 0:
            seen = {int(g[p]) for p in PEERS[c]}
            mask[c] = [d not in seen for d in range(1, 10)]
    return mask


def _naked(mask) -> dict[int, int]:
    return {c: int(np.flatnonzero(mask[c])[0]) + 1 for c in range(81) if mask[c].sum() == 1}


def _hidden(grid, mask) -> list[tuple[int, int, int]]:
    out = []
    for u, cells in enumerate(UNITS):
        present = set(np.asarray(grid)[cells].tolist())
        for d in range(1, 10):
            if d in present:
                continue
            where = [int(c) for c in cells if mask[c, d - 1]]
            if len(where) == 1:
                out.append((u, d, where[0]))
    return out


def naked_singles(grid) -> dict[int, int]:
    return _naked(candidate_mask(grid))


def hidden_singles(grid) -> list[tuple[int, int, int]]:
    return _hidden(grid, candidate_mask(grid))


def inference_waves(grid, max_waves: int = 81) -> WaveResult:
    g = np.asarray(grid).astype(np.int8).copy()
    status = check_puzzle(g)
    if not status.consistent:
        raise ConflictError("inconsistent clues")
    if status.n_solutions == 0:
        raise ConflictError("clues admit no solution")
    depth = np.where(g != 0, 0, STUCK).astype(np.int16)
    rules: list[set[str]] = [set() for _ in range(81)]
    n_waves = 0
    while True:
        mask = candidate_mask(g)
        derived: dict[int, tuple[int, set[str]]] = {}

        def add(c, d, rule):
            if c in derived and derived[c][0] != d:
                raise ConflictError(f"cell {c}: digits {derived[c][0]} and {d}")
            derived.setdefault(c, (d, set()))[1].add(rule)

        for c, d in _naked(mask).items():
            add(c, d, "naked")
        for _, d, c in _hidden(g, mask):
            add(c, d, "hidden")
        if not derived:
            break
        if n_waves == max_waves:
            depth[(g == 0)] = CENSORED
            break
        n_waves += 1
        nxt = g.copy()
        for c, (d, rs) in derived.items():
            nxt[c] = d
            depth[c] = n_waves
            rules[c] |= rs
        for cells in UNITS:  # joint constraint check on the simultaneous write
            vals = nxt[cells][nxt[cells] != 0]
            if len(vals) != len(set(vals.tolist())):
                raise ConflictError("simultaneous fills violate a unit")
        g = nxt
    return WaveResult(
        depth=depth,
        rules=tuple(frozenset(r) for r in rules),
        n_waves=n_waves,
        values=g,
    )
