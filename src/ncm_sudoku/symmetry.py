"""Sudoku symmetry group and exact canonical form (E3 preparation, D59).

Group: transposition x band permutation x row-within-band permutations x stack
permutation x column-within-stack permutations x digit relabelling
(2 * 1296 * 1296 * 9! elements). Grids are length-81 row-major arrays, digits
1..9, 0 = blank (blanks stay blank under every element).
"""

from dataclasses import dataclass
from itertools import permutations, product

import numpy as np

from ncm_sudoku.generate import GeneratedPuzzle

_ID9 = tuple(range(9))
_ID10 = tuple(range(10))
_PERMS3 = list(permutations(range(3)))


@dataclass(frozen=True)
class Symmetry:
    """out = digit_perm[ (grid.T if transpose else grid)[row_perm][:, col_perm] ]."""

    transpose: bool
    row_perm: tuple[int, ...]
    col_perm: tuple[int, ...]
    digit_perm: tuple[int, ...]


def _line_perm(rng: np.random.Generator) -> tuple[int, ...]:
    blocks = rng.permutation(3)
    return tuple(3 * int(b) + int(k) for b in blocks for k in rng.permutation(3))


def random_symmetry(rng: np.random.Generator, kind: str = "all") -> Symmetry:
    if kind not in ("all", "digit", "geometric"):
        raise ValueError(f"unknown kind {kind!r}")
    transpose, rows, cols, digits = False, _ID9, _ID9, _ID10
    if kind != "digit":
        transpose = bool(rng.integers(2))
        rows, cols = _line_perm(rng), _line_perm(rng)
    if kind != "geometric":
        digits = (0, *(int(d) for d in rng.permutation(9) + 1))
    return Symmetry(transpose, rows, cols, digits)


def _move_cells(a: np.ndarray, s: Symmetry) -> np.ndarray:
    """Move the leading 81-cell axis of `a` as `s` moves cells."""
    g = a.reshape(9, 9, *a.shape[1:])
    if s.transpose:
        g = g.swapaxes(0, 1)
    return g[list(s.row_perm)][:, list(s.col_perm)].reshape(a.shape)


def apply_symmetry(grid: np.ndarray, s: Symmetry) -> np.ndarray:
    grid = np.asarray(grid)
    return np.asarray(s.digit_perm, dtype=grid.dtype)[_move_cells(grid, s)]


def inverse(s: Symmetry) -> Symmetry:
    # With h = T(g)[R][:, C], T(h) = g[C][:, R], so the transposed inverse swaps the roles of R and C.
    r, c = np.argsort(s.row_perm), np.argsort(s.col_perm)
    rows, cols = (c, r) if s.transpose else (r, c)
    return Symmetry(
        s.transpose,
        tuple(int(x) for x in rows),
        tuple(int(x) for x in cols),
        tuple(int(x) for x in np.argsort(s.digit_perm)),
    )


def transform_predictions(pred: np.ndarray, s: Symmetry) -> np.ndarray:
    """pred[cell, d-1] -> out[new cell, digit_perm[d]-1], as `apply_symmetry` moves cells and digits."""
    moved = _move_cells(np.asarray(pred), s)
    out = np.empty_like(moved)
    out[:, np.asarray(s.digit_perm[1:]) - 1] = moved
    return out


_COL_PERMS = np.array(
    [[3 * st[i] + w[i][k] for i in range(3) for k in range(3)] for st in _PERMS3 for w in product(_PERMS3, repeat=3)]
)  # all 1296 stack / column-within-stack permutations
_POW10 = 10 ** np.arange(8, -1, -1, dtype=np.int64)
_N = len(_COL_PERMS)


def canonical_form(solution: np.ndarray) -> bytes:
    """Exact minlex canonical form: the lexicographically minimal 81-digit ASCII string over the whole group.

    Idea: the "minlex" form of Sudoku grid enumeration (e.g. Russell & Jarvis 2006,
    "Mathematics of Sudoku II"; the minlex convention of gsf's sudoku tool). Any
    minimal string starts with 123456789, so the digit relabelling is fixed once the
    top row is chosen. We enumerate transposition (2) x top row (9) x all 1296 column
    permutations; for each, the remaining row order is forced: the other two rows of
    the top band ascending, then the two other bands ordered by their smallest row,
    each band's rows ascending (rows are distinct, so comparing row keys is exact).
    Rows are compared as 9-digit integers. 2 * 9 * 1296 = 23,328 candidates, vectorised.
    """
    g0 = np.asarray(solution, dtype=np.int64).reshape(9, 9)
    ar = np.arange(_N)
    best = None
    for g in (g0, g0.T):
        cols = g[:, _COL_PERMS].transpose(1, 0, 2)  # (perm, row, col)
        for top in range(9):
            relabel = np.zeros((_N, 10), dtype=np.int64)
            relabel[ar[:, None], cols[:, top]] = np.arange(1, 10)
            keys = relabel[ar[:, None, None], cols] @ _POW10  # (perm, row) as 9-digit ints
            band = top // 3
            rest = np.sort(keys[:, [r for r in range(3 * band, 3 * band + 3) if r != top]], axis=1)
            b1, b2 = (np.sort(keys[:, 3 * b : 3 * b + 3], axis=1) for b in range(3) if b != band)
            swap = (b1[:, 0] > b2[:, 0])[:, None]
            cand = np.concatenate([rest, np.where(swap, b2, b1), np.where(swap, b1, b2)], axis=1)
            c = tuple(int(x) for x in cand[np.lexsort(cand.T[::-1])[0]])
            if best is None or c < best:
                best = c
    return b"123456789" + b"".join(b"%09d" % k for k in best)


def screen_canonical(subsets: dict[str, list[GeneratedPuzzle]], released_solutions: np.ndarray) -> dict:
    """Exact orbit screen: ids sharing a canonical form (classes of size >= 2) and exact duplicate pairs."""
    entries = [(f"released-{i}", s) for i, s in enumerate(released_solutions)]
    for puzzles in subsets.values():
        entries += [(p.puzzle_id, p.solution) for p in puzzles]
    by_bytes: dict[bytes, str] = {}
    by_canon: dict[bytes, list[str]] = {}
    exact = []
    for pid, sol in entries:
        key = np.asarray(sol, dtype=np.int8).tobytes()
        if key in by_bytes:
            exact.append([by_bytes[key], pid])
        else:
            by_bytes[key] = pid
        by_canon.setdefault(canonical_form(sol), []).append(pid)
    classes = [ids for ids in by_canon.values() if len(ids) >= 2]
    return {"n_entries": len(entries), "classes": classes, "exact_duplicates": exact}
