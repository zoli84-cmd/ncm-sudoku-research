"""Output parser and validator metrics (research plan §2.2 item 8, §6, §10).

The parser never repairs model output: no solver-based fixing, no clue
write-back. Format errors stay in every denominator.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ncm_sudoku.grid import SEP, UNITS

OUTPUT_LEN = 89
_DIGITS = np.arange(1, 10)


@dataclass(frozen=True)
class ParsedOutput:
    cells: np.ndarray  # (81,) int8; -1 where a slot is missing or invalid
    positions_identified: bool
    format_error: bool


@dataclass(frozen=True)
class Metrics:
    well_formed: bool
    solve: bool
    valid_grid: bool
    all_clues_preserved: bool
    clue_preservation: float
    cell_acc_all: float
    cell_acc_empty: float
    constraint_violations: int | None
    reference_match: bool


def parse_output_tokens(tokens: Sequence[int]) -> ParsedOutput:
    """Positions are identified iff the output has exactly 89 tokens.

    Slot i is a separator slot iff i % 10 == 9, else a digit slot.
    """
    cells = np.full(81, -1, dtype=np.int8)
    tokens = list(tokens)
    if len(tokens) != OUTPUT_LEN:
        return ParsedOutput(cells, positions_identified=False, format_error=True)
    format_error = False
    c = 0
    for i, t in enumerate(tokens):
        if i % 10 == 9:
            if t != SEP:
                format_error = True
            continue
        if 1 <= t <= 9:
            cells[c] = t
        else:
            format_error = True
        c += 1
    return ParsedOutput(cells, positions_identified=True, format_error=format_error)


def count_violations(grid: np.ndarray) -> int:
    """Number of the 27 units that are not a permutation of 1..9."""
    return int(sum(not np.array_equal(np.sort(grid[u]), _DIGITS) for u in UNITS))


def evaluate(puzzle: np.ndarray, out: ParsedOutput, reference: np.ndarray) -> Metrics:
    well_formed = not out.format_error
    clues = puzzle != 0
    blanks = ~clues
    kept = out.cells[clues] == puzzle[clues]
    clue_preservation = float(kept.mean()) if clues.any() else 1.0
    all_clues_preserved = bool(kept.all())
    violations = count_violations(out.cells) if well_formed else None
    valid_grid = well_formed and violations == 0
    if out.positions_identified:
        correct = out.cells == reference
        cell_acc_all = float(correct.mean())
        cell_acc_empty = float(correct[blanks].mean()) if blanks.any() else 1.0
    else:
        cell_acc_all = cell_acc_empty = 0.0
    return Metrics(
        well_formed=well_formed,
        solve=valid_grid and all_clues_preserved,
        valid_grid=valid_grid,
        all_clues_preserved=all_clues_preserved,
        clue_preservation=clue_preservation,
        cell_acc_all=cell_acc_all,
        cell_acc_empty=cell_acc_empty,
        constraint_violations=violations,
        reference_match=well_formed and bool(np.array_equal(out.cells, reference)),
    )


def cell_hamming(a: np.ndarray, b: np.ndarray, cells: np.ndarray | None = None) -> float:
    """Fraction of differing cells over `cells` (default: all 81)."""
    idx = np.arange(81) if cells is None else np.asarray(cells)
    return float((np.asarray(a)[idx] != np.asarray(b)[idx]).mean())
