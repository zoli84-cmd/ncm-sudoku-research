import numpy as np

from ncm_sudoku.grid import (
    BOS,
    PEERS,
    SEP,
    UNITS,
    encode_puzzle_tokens,
    encode_solution_tokens,
    grid_from_string,
)

SOLUTION = (
    "534678912672195348198342567859761423426853791"
    "713924856961537284287419635345286179"
)


def test_units_shape_and_coverage():
    assert UNITS.shape == (27, 9)
    counts = np.bincount(UNITS.ravel(), minlength=81)
    assert (counts == 3).all()


def test_peers():
    assert all(len(PEERS[c]) == 20 for c in range(81))
    assert all(c not in PEERS[c] for c in range(81))
    assert {1, 9, 10} <= PEERS[0]


def test_encode_puzzle_tokens():
    grid = np.zeros(81, dtype=np.int8)
    grid[0] = 5
    tokens = encode_puzzle_tokens(grid)
    assert len(tokens) == 91
    assert tokens[0] == BOS and tokens[-1] == BOS
    assert tokens[1] == 5
    assert tokens[10] == SEP
    assert tokens.count(SEP) == 8


def test_encode_solution_tokens():
    grid = grid_from_string(SOLUTION)
    tokens = encode_solution_tokens(grid)
    assert len(tokens) == 89
    assert tokens[9] == SEP
    digits = [t for i, t in enumerate(tokens) if i % 10 != 9]
    assert digits == grid.tolist()


def test_grid_from_string_blanks():
    grid = grid_from_string("." + "0" + SOLUTION[2:])
    assert grid.dtype == np.int8 and grid.shape == (81,)
    assert grid[0] == 0 and grid[1] == 0 and grid[2] == 4


def test_cell_token_indices():
    from ncm_sudoku.grid import CELL_TOKEN_INDICES
    from sudoku_cases import P, S

    assert CELL_TOKEN_INDICES.shape == (81,)
    assert (np.array(encode_solution_tokens(S))[CELL_TOKEN_INDICES] == S).all()
    assert (np.array(encode_puzzle_tokens(P))[1 + CELL_TOKEN_INDICES] == P).all()
