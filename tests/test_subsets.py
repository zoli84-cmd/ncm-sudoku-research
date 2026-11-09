import numpy as np

from ncm_sudoku.generate import generate_puzzle
from ncm_sudoku.subsets import SEEDS, assert_generator_frozen, screen, solution_signature
from sudoku_cases import S


def test_seed_namespaces():
    assert SEEDS == {"gate": 1, "cal": 2, "probe_train": 3, "probe_val": 4, "select": 5, "test": 6, "e4_test": 7}


def test_assert_generator_frozen_passes():
    assert_generator_frozen()


def _variants(s):
    g = s.reshape(9, 9)
    relabel = np.array([0, 3, 1, 4, 2, 5, 9, 7, 8, 6])[s]
    return [
        relabel,
        g[[1, 0, 2, 3, 4, 5, 6, 7, 8]].ravel(),  # row swap within a band
        g[[3, 4, 5, 0, 1, 2, 6, 7, 8]].ravel(),  # band swap
        g[:, [0, 2, 1, 3, 4, 5, 6, 7, 8]].ravel(),  # column swap within a stack
        g.T.ravel(),
    ]


def test_signature_invariant_under_symmetries():
    base = solution_signature(S)
    assert all(solution_signature(v) == base for v in _variants(S))


def test_signature_differs():
    a, b = generate_puzzle(2, 0).solution, generate_puzzle(2, 1).solution
    assert solution_signature(a) != solution_signature(b)


def test_screen_flags_duplicates():
    p0, p1 = generate_puzzle(2, 0), generate_puzzle(2, 1)
    released = np.stack([_variants(p1.solution)[0]])  # relabeled copy of p1
    result = screen({"cal": [p0, p0]}, released)
    assert result["exact_duplicates"] == [("gen-v1-2-0", "gen-v1-2-0")]
    assert ("released-0", "gen-v1-2-1") not in result["signature_collisions"]
    result2 = screen({"cal": [p0, p1]}, released)
    assert ("released-0", "gen-v1-2-1") in result2["signature_collisions"]
