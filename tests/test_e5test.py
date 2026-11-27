import numpy as np
import pytest

from ncm_sudoku.e5pairs import Pair
from ncm_sudoku.e5test import canonical_key, eligibility, external_index, internal_collisions, screen_pairs
from ncm_sudoku.generate import random_solution
from ncm_sudoku.labels import candidate_mask
from ncm_sudoku.symmetry import apply_symmetry, random_symmetry


def _pair(index, solution, pair_id=None):
    return Pair(a=solution.copy(), b=solution.copy(), solution=solution, pair_id=pair_id or f"test-{index}",
                seed=10, index=index, attempts=(1, 1))


def test_screen_rejects_external_collisions_steps_and_logs():
    external_solution = random_solution(np.random.default_rng(1))
    s0 = random_solution(np.random.default_rng(2))
    s2 = random_solution(np.random.default_rng(3))
    s3 = random_solution(np.random.default_rng(4))
    solutions = [s0, external_solution, s2, s3]
    index = external_index({"external": [("external-id", external_solution)]})

    def make_pair(i):
        return _pair(i, solutions[i])

    accepted, log = screen_pairs(make_pair, index, n=3)

    assert [p.pair_id for p in accepted] == ["test-0", "test-2", "test-3"]
    assert len(log) == 4
    assert log[1] == {"index": 1, "pair_id": "test-1", "accepted": False,
                       "reason": "external_collision", "colliding_id": "external-id"}
    assert all(row["accepted"] and row["reason"] is None for row in (log[0], log[2], log[3]))


def test_screen_propagates_generation_errors():
    def make_pair(i):
        if i == 1:
            raise RuntimeError("boom")
        return _pair(i, random_solution(np.random.default_rng(i)))

    with pytest.raises(RuntimeError):
        screen_pairs(make_pair, {}, n=3)


def test_internal_collisions_lists_both_ids():
    sol = random_solution(np.random.default_rng(5))
    relabelled = apply_symmetry(sol, random_symmetry(np.random.default_rng(6), kind="digit"))
    other = random_solution(np.random.default_rng(7))
    pairs = [_pair(0, sol, "p0"), _pair(1, relabelled, "p1"), _pair(2, other, "p2")]
    assert canonical_key(sol) == canonical_key(relabelled)
    assert internal_collisions(pairs) == [("p0", "p1")]


def test_eligibility_from_labels():
    sol = random_solution(np.random.default_rng(8))
    a = sol.copy()
    a[:21] = 0  # at least one both-empty cell
    b = a.copy()  # identical clue mask -> identical candidates on every both-empty cell
    mask = np.stack([candidate_mask(a), candidate_mask(b)])
    empty = np.stack([a == 0, b == 0])
    elig_a, elig_b = eligibility(mask, empty, n=1)
    assert elig_a.tolist() == [False]
    assert elig_b.tolist() == [True]
