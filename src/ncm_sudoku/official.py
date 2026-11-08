"""Mirror of the official upstream Sudoku metric (third_party/ncm scripts/eval_merge.py `exact`).

Kept for the G0 reproduction only; the scientific analysis uses ncm_sudoku.validate.
Known upstream properties reproduced on purpose: solved is string equality, and the
cell metric averages over zip(hyp, ref), so a truncated hypothesis shrinks the
denominator (plan §6). Deviation: an empty hypothesis contributes 0.0 instead of NaN.
All *_pct values are on the 0..100 scale, as eval_merge prints them.
"""

from collections.abc import Sequence

import numpy as np

_CHARS = ["_"] + list("123456789") + ["|", "<BOS>"]
_BOS = 11


def decode_string(tokens: Sequence[int]) -> str:
    """SudokuTokenizer.decode(ids, skip_special_tokens=True)."""
    return "".join(_CHARS[int(t)] for t in tokens if int(t) != _BOS)


def _cells(t: str) -> str:
    return t.replace("|", "")


def _valid(t: str) -> bool:
    g = _cells(t)
    if len(g) != 81 or not g.isdigit() or "0" in g:
        return False
    rows = [g[i * 9 : (i + 1) * 9] for i in range(9)]
    cols = ["".join(r[j] for r in rows) for j in range(9)]
    boxes = [
        "".join(rows[r][c] for r in range(br, br + 3) for c in range(bc, bc + 3))
        for br in (0, 3, 6)
        for bc in (0, 3, 6)
    ]
    return all(sorted(x) == list("123456789") for x in rows + cols + boxes)


def _cell_value(h: str, r: str) -> float:
    pairs = list(zip(_cells(h), _cells(r)))
    return float(np.mean([a == b for a, b in pairs])) if pairs else 0.0


def official_exact(hyps: list[str], refs: list[str]) -> dict:
    n = len(hyps)
    solved_n = sum(h == r for h, r in zip(hyps, refs))
    return {
        "n": n,
        "solved_n": solved_n,
        "solved_pct": 100.0 * solved_n / n,
        "cell_pct": 100.0 * float(np.mean([_cell_value(h, r) for h, r in zip(hyps, refs)])),
        "valid_pct": 100.0 * sum(_valid(h) for h in hyps) / n,
    }
