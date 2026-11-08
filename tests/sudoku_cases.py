"""Shared test grids (Wikipedia's Sudoku example: 30 clues, unique solution)."""

from ncm_sudoku.grid import grid_from_string

S_STR = (
    "534678912672195348198342567859761423426853791"
    "713924856961537284287419635345286179"
)
P_STR = (
    "53..7....6..195....98....6.8...6...34..8.3..17..."
    "2...6.6....28....419..5....8..79"
)

S = grid_from_string(S_STR)
P = grid_from_string(P_STR)
