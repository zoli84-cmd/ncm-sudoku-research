"""Safe loading of the released NCM Sudoku evaluation set.

File structure (inspected with pickletools, no unpickling): protocol-4 pickles
holding a plain list of int lists, no globals. puzzles.pickle: 91-token
sequences [BOS] + 9 rows joined by SEP + [BOS]; solutions.pickle: 89-token
sequences of 9 rows joined by SEP. Token ids follow ncm_sudoku.grid.
"""

import pickle
from pathlib import Path

import numpy as np

from ncm_sudoku.grid import BOS, SEP

ALLOWED_GLOBALS: frozenset[tuple[str, str]] = frozenset()


class UnsafePickleError(ValueError):
    pass


class _SafeUnpickler(pickle.Unpickler):
    # Untrusted data: refuse every global, so no callable can be resolved or run.
    # The released files contain only builtin lists and ints (no globals).
    def find_class(self, module, name):
        if (module, name) not in ALLOWED_GLOBALS:
            raise UnsafePickleError(f"global {module}.{name} is not allowed")
        return super().find_class(module, name)


def safe_load_pickle(path: Path) -> object:
    with Path(path).open("rb") as f:
        return _SafeUnpickler(f).load()


def _rows_to_grid(tokens: list[int]) -> np.ndarray:
    if len(tokens) != 89 or any(tokens[i] != SEP for i in range(9, 89, 10)):
        raise ValueError(f"unexpected row serialization of length {len(tokens)}")
    cells = [t for i, t in enumerate(tokens) if i % 10 != 9]
    if any(not 0 <= t <= 9 for t in cells):
        raise ValueError("cell token outside 0..9")
    return np.array(cells, dtype=np.int8)


def load_released(split_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    split_dir = Path(split_dir)
    raw_p = safe_load_pickle(split_dir / "puzzles.pickle")
    raw_s = safe_load_pickle(split_dir / "solutions.pickle")
    if len(raw_p) != len(raw_s):
        raise ValueError("puzzle and solution counts differ")
    puzzles = []
    for seq in raw_p:
        if len(seq) != 91 or seq[0] != BOS or seq[-1] != BOS:
            raise ValueError("puzzle sequence is not [BOS] + 89 + [BOS]")
        puzzles.append(_rows_to_grid(seq[1:-1]))
    return np.stack(puzzles), np.stack([_rows_to_grid(seq) for seq in raw_s])
