import numpy as np
import pytest

from ncm_sudoku.dlx import dlx_count_solutions
from ncm_sudoku.solve import check_puzzle, count_solutions, solve_one
from sudoku_cases import P, S

COUNTERS = [count_solutions, dlx_count_solutions]


@pytest.mark.parametrize("counter", COUNTERS)
def test_unique_puzzle(counter):
    assert counter(P) == 1


def test_solve_one():
    assert np.array_equal(solve_one(P), S)


@pytest.mark.parametrize("counter", COUNTERS)
def test_multiple_solutions(counter):
    g = S.copy()
    g[27:] = 0  # keep only the first three rows
    assert counter(g) == 2


@pytest.mark.parametrize("counter", COUNTERS)
def test_unsatisfiable(counter):
    g = np.zeros(81, dtype=np.int8)
    g[0:8] = np.arange(1, 9)  # row 0: 1..8 in columns 0-7
    g[9 * 4 + 8] = 9  # 9 in column 8, row 4 -> r0c8 has no candidate
    assert check_puzzle(g).consistent
    assert counter(g) == 0


def test_check_inconsistent():
    g = np.zeros(81, dtype=np.int8)
    g[0] = g[5] = 5
    status = check_puzzle(g)
    assert not status.consistent and status.n_solutions == 0


def test_check_unique():
    status = check_puzzle(P)
    assert status.consistent and status.n_solutions == 1


@pytest.mark.parametrize("counter", COUNTERS)
def test_empty_grid_limit(counter):
    assert counter(np.zeros(81, dtype=np.int8), limit=2) == 2


def test_inputs_not_mutated():
    g = P.copy()
    count_solutions(g)
    dlx_count_solutions(g)
    solve_one(g)
    assert np.array_equal(g, P)


def test_cross_check_random_masks():
    rng = np.random.default_rng(0)
    for _ in range(50):
        n_clues = int(rng.integers(22, 36))
        keep = rng.choice(81, size=n_clues, replace=False)
        g = np.zeros(81, dtype=np.int8)
        g[keep] = S[keep]
        assert count_solutions(g) == dlx_count_solutions(g)
