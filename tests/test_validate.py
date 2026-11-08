import numpy as np
import pytest

from ncm_sudoku.grid import SEP, encode_solution_tokens
from ncm_sudoku.validate import cell_hamming, evaluate, parse_output_tokens
from sudoku_cases import P, S

N_BLANK = int((P == 0).sum())


def _eval(grid_or_tokens, tokens=False):
    toks = grid_or_tokens if tokens else encode_solution_tokens(grid_or_tokens)
    return evaluate(P, parse_output_tokens(toks), S)


def test_fixture_shape():
    assert N_BLANK == 51
    assert ((P == 0) | (P == S)).all()


def test_correct_grid():
    m = _eval(S)
    assert m.well_formed and m.solve and m.valid_grid and m.reference_match
    assert m.constraint_violations == 0
    assert m.cell_acc_all == 1.0 and m.cell_acc_empty == 1.0
    assert m.all_clues_preserved and m.clue_preservation == 1.0


def test_altered_clue():
    g = S.copy()
    ones, twos = g == 1, g == 2
    g[ones], g[twos] = 2, 1
    m = _eval(g)
    assert m.valid_grid
    assert not m.solve
    assert not m.all_clues_preserved
    assert m.clue_preservation < 1.0


def test_row_repeat():
    # Single-cell edit: duplicates a digit in its row, column and box.
    g = S.copy()
    g[0] = g[1]
    m = _eval(g)
    assert not m.valid_grid and not m.solve
    assert m.constraint_violations == 3


def test_col_repeat():
    # Swap two cells of one row in different boxes: row stays valid,
    # both columns and both boxes break.
    g = S.copy()
    g[0], g[8] = g[8], g[0]
    m = _eval(g)
    assert not m.valid_grid
    assert m.constraint_violations == 4


def test_box_repeat():
    # Swap two cells of one box in different rows and columns:
    # box stays valid, two rows and two columns break.
    g = S.copy()
    g[0], g[10] = g[10], g[0]
    m = _eval(g)
    assert not m.valid_grid
    assert m.constraint_violations == 4


@pytest.mark.parametrize("length", [88, 90])
def test_wrong_length(length):
    toks = encode_solution_tokens(S)
    toks = toks[:length] if length < 89 else toks + [5]
    out = parse_output_tokens(toks)
    assert out.format_error and not out.positions_identified
    assert (out.cells == -1).all()
    m = evaluate(P, out, S)
    assert not m.solve and not m.valid_grid and not m.well_formed
    assert m.cell_acc_all == 0.0 and m.cell_acc_empty == 0.0
    assert m.constraint_violations is None


def test_invalid_char():
    toks = encode_solution_tokens(S)
    toks[0] = 11
    out = parse_output_tokens(toks)
    assert out.format_error and out.positions_identified
    assert out.cells[0] == -1
    m = evaluate(P, out, S)
    assert m.cell_acc_all == pytest.approx(80 / 81)
    assert not m.solve and not m.valid_grid


def test_parse_misplaced_separator():
    toks = encode_solution_tokens(S)
    toks[1] = SEP  # separator in a digit slot
    toks[9] = 4  # digit in a separator slot
    out = parse_output_tokens(toks)
    assert out.format_error and out.positions_identified
    assert out.cells[1] == -1
    m = evaluate(P, out, S)
    assert m.constraint_violations is None
    assert not m.solve


def test_no_repair():
    g = S.copy()
    clue = int(np.flatnonzero(P)[0])
    g[clue] = g[clue] % 9 + 1
    out = parse_output_tokens(encode_solution_tokens(g))
    m = evaluate(P, out, S)
    assert not m.all_clues_preserved and not m.solve
    assert out.cells[clue] == g[clue]


def test_cell_hamming():
    assert cell_hamming(S, S) == 0.0
    g = S.copy()
    blank = int(np.flatnonzero(P == 0)[0])
    g[blank] = g[blank] % 9 + 1
    assert cell_hamming(S, g) == pytest.approx(1 / 81)
    assert cell_hamming(S, g, cells=np.flatnonzero(P == 0)) == pytest.approx(1 / 51)
