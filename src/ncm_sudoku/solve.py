"""Backtracking Sudoku solver with bitmask candidates and minimum-remaining-values choice."""

from dataclasses import dataclass

import numpy as np

_ROW = [c // 9 for c in range(81)]
_COL = [c % 9 for c in range(81)]
_BOX = [(c // 27) * 3 + (c % 9) // 3 for c in range(81)]
_FULL = 0x3FE  # bits 1..9


@dataclass(frozen=True)
class PuzzleStatus:
    consistent: bool
    n_solutions: int  # capped at 2; 0 if inconsistent


def _init(grid):
    """Return (cells, rows, cols, boxes) bitmask state, or None if clues conflict."""
    cells = [int(v) for v in np.asarray(grid)]
    rows, cols, boxes = [0] * 9, [0] * 9, [0] * 9
    for c, v in enumerate(cells):
        if v:
            bit = 1 << v
            r, k, b = _ROW[c], _COL[c], _BOX[c]
            if (rows[r] | cols[k] | boxes[b]) & bit:
                return None
            rows[r] |= bit
            cols[k] |= bit
            boxes[b] |= bit
    return cells, rows, cols, boxes


def _search(cells, rows, cols, boxes, limit, found):
    best, best_mask, best_n = -1, 0, 10
    for c in range(81):
        if cells[c]:
            continue
        mask = _FULL & ~(rows[_ROW[c]] | cols[_COL[c]] | boxes[_BOX[c]])
        n = mask.bit_count()
        if n < best_n:
            best, best_mask, best_n = c, mask, n
            if n <= 1:
                break
    if best < 0:
        found.append(list(cells))
        return len(found) >= limit
    r, k, b = _ROW[best], _COL[best], _BOX[best]
    mask = best_mask
    while mask:
        bit = mask & -mask
        mask ^= bit
        cells[best] = bit.bit_length() - 1
        rows[r] |= bit
        cols[k] |= bit
        boxes[b] |= bit
        done = _search(cells, rows, cols, boxes, limit, found)
        rows[r] ^= bit
        cols[k] ^= bit
        boxes[b] ^= bit
        cells[best] = 0
        if done:
            return True
    return False


def _solutions(grid, limit):
    state = _init(grid)
    if state is None:
        return []
    found: list[list[int]] = []
    _search(*state, limit, found)
    return found


def count_solutions(grid, limit: int = 2) -> int:
    return len(_solutions(grid, limit))


def solve_one(grid) -> np.ndarray | None:
    sols = _solutions(grid, 1)
    return np.array(sols[0], dtype=np.int8) if sols else None


def check_puzzle(grid) -> PuzzleStatus:
    if _init(grid) is None:
        return PuzzleStatus(consistent=False, n_solutions=0)
    return PuzzleStatus(consistent=True, n_solutions=count_solutions(grid, limit=2))
