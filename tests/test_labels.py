import numpy as np
import pytest

from ncm_sudoku.grid import grid_from_string
from ncm_sudoku.labels import (
    CENSORED,
    STUCK,
    ConflictError,
    candidate_mask,
    hidden_singles,
    inference_waves,
    naked_singles,
)
from sudoku_cases import P, S

INKALA = grid_from_string(
    "800000000003600000070090200050007000000045700000100030001000068008500010090000400"
)


def test_candidate_mask_basic():
    g = np.zeros(81, dtype=np.int8)
    g[1:9] = np.arange(1, 9)  # row 0 holds 1..8, cell 0 blank
    m = candidate_mask(g)
    assert m.shape == (81, 9) and m.dtype == bool
    assert m[0].tolist() == [False] * 8 + [True]
    assert not m[1:9].any()  # given cells are all-False


def test_naked_equals_popcount():
    m = candidate_mask(P)
    single_cells = {c for c in range(81) if P[c] == 0 and m[c].sum() == 1}
    assert set(naked_singles(P)) == single_cells
    for c, d in naked_singles(P).items():
        assert m[c, d - 1]


def test_hidden_single():
    assert (2, 5, 24) in hidden_singles(P)
    assert 24 not in naked_singles(P)
    assert candidate_mask(P)[24].sum() == 5


def test_waves_depth_one():
    g = S.copy()
    g[40] = 0
    res = inference_waves(g)
    assert res.depth[40] == 1
    assert "naked" in res.rules[40]
    assert res.n_waves == 1
    assert (res.depth[np.arange(81) != 40] == 0).all()


def test_waves_synchronous():
    res = inference_waves(P)
    blanks = P == 0
    wave1 = set(np.flatnonzero(res.depth == 1).tolist())
    singles_p = set(naked_singles(P)) | {c for _, _, c in hidden_singles(P)}
    assert wave1 == singles_p
    # depth-2 cells are not singles in P but become singles once wave 1 is written
    after1 = P.copy()
    after1[list(wave1)] = S[list(wave1)]
    singles_1 = set(naked_singles(after1)) | {c for _, _, c in hidden_singles(after1)}
    depth2 = set(np.flatnonzero(res.depth == 2).tolist())
    assert depth2 and not (depth2 & singles_p)
    assert depth2 == singles_1
    assert (res.depth[blanks] != 0).all()


def test_waves_solves_easy():
    res = inference_waves(P)
    assert not (res.depth == STUCK).any()
    assert res.n_waves >= 2
    assert np.array_equal(res.values, S)


def test_waves_stuck_cells():
    res = inference_waves(INKALA)
    blanks = INKALA == 0
    assert (res.depth[blanks] == STUCK).any()
    assert not (res.depth[blanks] == 0).any()


def test_waves_censored():
    res = inference_waves(P, max_waves=1)
    assert (res.depth == 1).any()
    assert (res.depth == CENSORED).any()
    assert not (res.depth == STUCK).any()
    assert res.n_waves == 1


def test_waves_inconsistent_input_raises():
    g = np.zeros(81, dtype=np.int8)
    g[0] = g[5] = 5
    with pytest.raises(ConflictError):
        inference_waves(g)


def test_labels_do_not_mutate_input():
    g = P.copy()
    inference_waves(g)
    candidate_mask(g)
    assert np.array_equal(g, P)


def test_waves_unsatisfiable_input_raises():
    # Consistent clues, no solution: r0c8 has no candidate (plan §5.2 item 3).
    g = np.zeros(81, dtype=np.int8)
    g[0:8] = np.arange(1, 9)
    g[9 * 4 + 8] = 9
    with pytest.raises(ConflictError):
        inference_waves(g)
