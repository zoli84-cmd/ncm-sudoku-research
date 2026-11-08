"""Independent solution counter: Knuth's Algorithm X over the 324-column exact-cover matrix.

Written independently of solve.py (must not import it); used to cross-check
uniqueness decisions. Columns: ("cell", r, c), ("row", r, d), ("col", c, d),
("box", b, d). Covering uses the dict-of-sets formulation of Algorithm X
instead of pointer-based dancing links; the search is the same.
"""

import numpy as np


def _matrix():
    rows = {}
    for r in range(9):
        for c in range(9):
            b = (r // 3) * 3 + c // 3
            for d in range(1, 10):
                rows[(r, c, d)] = [("cell", r, c), ("row", r, d), ("col", c, d), ("box", b, d)]
    cols = {}
    for key, cs in rows.items():
        for col in cs:
            cols.setdefault(col, set()).add(key)
    return rows, cols


def _select(rows, cols, key):
    removed = []
    for j in rows[key]:
        for i in cols[j]:
            for k in rows[i]:
                if k != j:
                    cols[k].remove(i)
        removed.append(cols.pop(j))
    return removed


def _deselect(rows, cols, key, removed):
    for j in reversed(rows[key]):
        cols[j] = removed.pop()
        for i in cols[j]:
            for k in rows[i]:
                if k != j:
                    cols[k].add(i)


def _count(rows, cols, limit):
    if not cols:
        return 1
    col = min(cols, key=lambda k: len(cols[k]))
    total = 0
    for key in list(cols[col]):
        removed = _select(rows, cols, key)
        total += _count(rows, cols, limit - total)
        _deselect(rows, cols, key, removed)
        if total >= limit:
            break
    return total


def dlx_count_solutions(grid, limit: int = 2) -> int:
    g = np.asarray(grid)
    rows, cols = _matrix()
    for idx in range(81):
        v = int(g[idx])
        if not v:
            continue
        key = (idx // 9, idx % 9, v)
        if any(col not in cols for col in rows[key]):
            return 0  # clue conflicts with an earlier clue
        _select(rows, cols, key)
    return min(_count(rows, cols, limit), limit)
