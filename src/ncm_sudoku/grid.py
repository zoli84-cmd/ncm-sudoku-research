"""Grid conventions and NCM Sudoku token serialization.

A grid is a numpy int8 array of shape (81,), row-major (cell c = 9*row + col),
0 = blank, 1..9 = digits. NCM token ids follow HazyResearch/ncm
tokenization/sudoku_tokenizer.py at the pinned commit: 0 blank, 1..9 digits,
10 row separator, 11 BOS.
"""

import numpy as np

BLANK = 0
SEP = 10
BOS = 11

_rows = [[9 * r + c for c in range(9)] for r in range(9)]
_cols = [[9 * r + c for r in range(9)] for c in range(9)]
_boxes = [
    [9 * (3 * br + r) + 3 * bc + c for r in range(3) for c in range(3)]
    for br in range(3)
    for bc in range(3)
]
UNITS = np.array(_rows + _cols + _boxes, dtype=np.int64)  # rows 0-8, cols 9-17, boxes 18-26
# Cell c -> position in the 89-token output / state sequence (the 91-token puzzle
# prefix adds BOS in front: 1 + CELL_TOKEN_INDICES).
CELL_TOKEN_INDICES = np.array([c + c // 9 for c in range(81)], dtype=np.int64)
PEERS = tuple(
    frozenset(int(p) for u in UNITS if c in u for p in u) - {c} for c in range(81)
)


def _rows_joined(grid) -> list[int]:
    g = np.asarray(grid).tolist()
    tokens: list[int] = []
    for r in range(9):
        if r:
            tokens.append(SEP)
        tokens.extend(g[9 * r : 9 * r + 9])
    return tokens


def encode_puzzle_tokens(grid) -> list[int]:
    """91 tokens: BOS + 9 rows joined by SEP (89) + BOS."""
    return [BOS] + _rows_joined(grid) + [BOS]


def encode_solution_tokens(grid) -> list[int]:
    """89 tokens: 9 rows of 9 digits joined by SEP."""
    return _rows_joined(grid)


def grid_from_string(s: str) -> np.ndarray:
    """81 characters, '.' or '0' for blank."""
    assert len(s) == 81, len(s)
    return np.array([0 if ch == "." else int(ch) for ch in s], dtype=np.int8)
