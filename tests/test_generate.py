import time

import numpy as np
import pytest

from ncm_sudoku.dlx import dlx_count_solutions
from ncm_sudoku.generate import (
    GenerationError,
    generate_many,
    generate_puzzle,
    random_solution,
)
from ncm_sudoku.solve import count_solutions
from ncm_sudoku.validate import count_violations


def test_random_solution_valid():
    for seed in range(5):
        g = random_solution(np.random.default_rng(seed))
        assert g.dtype == np.int8 and g.shape == (81,)
        assert count_violations(g) == 0


def test_generate_contract():
    t0 = time.perf_counter()
    gp = generate_puzzle(1, 0)
    elapsed = time.perf_counter() - t0
    print(f"generate_puzzle(1, 0): {elapsed:.3f}s, attempts={gp.attempts}")
    assert int((gp.puzzle != 0).sum()) == 30
    clues = gp.puzzle != 0
    assert np.array_equal(gp.puzzle[clues], gp.solution[clues])
    assert count_violations(gp.solution) == 0
    assert count_solutions(gp.puzzle) == 1
    assert dlx_count_solutions(gp.puzzle) == 1
    assert gp.puzzle_id == "gen-v1-1-0"
    assert (gp.seed, gp.index) == (1, 0) and gp.attempts >= 1


def test_generate_deterministic():
    a, b = generate_puzzle(2, 5), generate_puzzle(2, 5)
    assert np.array_equal(a.puzzle, b.puzzle) and np.array_equal(a.solution, b.solution)
    c = generate_puzzle(2, 6)
    assert not np.array_equal(a.solution, c.solution)


def test_generate_retry_bound():
    with pytest.raises(GenerationError):
        generate_puzzle(0, 0, n_clues=17, max_attempts=2)


def test_generate_many_ids_unique():
    batch = generate_many(3, 10)
    assert len({g.puzzle_id for g in batch}) == 10
    assert len({g.solution.tobytes() for g in batch}) == 10
