"""E5 counterfactual pairs: one solution, two clue masks (D97).

Each pair draws one solution with `generate.random_solution` and then runs the
generator's clue-removal procedure twice with independent random cell orders: one
pass over the order, keeping a removal only if the solution stays unique, until
exactly `n_clues` remain; an attempt ending above `n_clues` restarts with a new order,
up to `max_attempts` (the loop of `generate.generate_puzzle`, which stays frozen and
untouched, D33). Member B is redrawn until its clue mask differs from member A's.
Both members therefore share the solution, the clue count and the generator that
passed the WP1 distribution gate, and differ only in the clue mask.

Random streams: solution `default_rng([seed, index, 0])`, member A
`[seed, index, 1]`, member B `[seed, index, 2]`; the stream depends on numpy (the
generator guard pins it). Seed namespaces continue `subsets.SEEDS` (1..7).
"""

from dataclasses import dataclass

import numpy as np

from ncm_sudoku.generate import GenerationError, random_solution
from ncm_sudoku.solve import count_solutions
from ncm_sudoku.subsets import assert_generator_frozen

PAIR_VERSION = "e5pair-v1"
PAIR_SEEDS = {"pairs_probe_train": 8, "pairs_probe_val": 9, "pairs_test": 10}


@dataclass(frozen=True)
class Pair:
    a: np.ndarray
    b: np.ndarray
    solution: np.ndarray
    pair_id: str
    seed: int
    index: int
    attempts: tuple[int, int]


def remove_clues(solution: np.ndarray, rng: np.random.Generator, n_clues: int = 30, max_attempts: int = 50):
    """The removal loop of `generate.generate_puzzle` on a given solution. Returns (puzzle, attempts)."""
    for attempt in range(1, max_attempts + 1):
        puzzle = solution.copy()
        n = 81
        for c in rng.permutation(81).tolist():
            if n == n_clues:
                break
            v = puzzle[c]
            puzzle[c] = 0
            if count_solutions(puzzle, limit=2) == 1:
                n -= 1
            else:
                puzzle[c] = v
        if n == n_clues:
            return puzzle, attempt
    raise GenerationError(f"{n_clues} clues not reached in {max_attempts} attempts")


def generate_pair(seed: int, index: int, n_clues: int = 30, max_attempts: int = 50) -> Pair:
    solution = random_solution(np.random.default_rng([seed, index, 0]))
    a, att_a = remove_clues(solution, np.random.default_rng([seed, index, 1]), n_clues, max_attempts)
    rng_b = np.random.default_rng([seed, index, 2])
    att_b = 0
    while True:
        b, k = remove_clues(solution, rng_b, n_clues, max_attempts)
        att_b += k
        if not np.array_equal(a > 0, b > 0):
            break
    return Pair(a=a, b=b, solution=solution, pair_id=f"{PAIR_VERSION}-{seed}-{index}", seed=seed, index=index,
                attempts=(att_a, att_b))


def generate_pairs(name: str, n: int, n_clues: int = 30) -> list[Pair]:
    assert_generator_frozen()
    return [generate_pair(PAIR_SEEDS[name], i, n_clues) for i in range(n)]


def contrast_stats(pairs: list[Pair]) -> dict:
    """Descriptive size of the within-pair contrast: shared clues, cells empty in both
    members, and how many of those have a different candidate mask (and how many bits)."""
    from ncm_sudoku.labels import candidate_mask

    shared, both_empty, diff_cells, diff_bits = [], [], [], []
    for p in pairs:
        ma, mb = candidate_mask(p.a), candidate_mask(p.b)
        both = (p.a == 0) & (p.b == 0)
        d = (ma != mb).sum(axis=1)
        shared.append(int(((p.a > 0) & (p.b > 0)).sum()))
        both_empty.append(int(both.sum()))
        diff_cells.append(int((both & (d > 0)).sum()))
        diff_bits.append(int(d[both].sum()))

    def q(x):
        return {"mean": float(np.mean(x)), "min": int(np.min(x)), "median": float(np.median(x)), "max": int(np.max(x))}

    return {"shared_clues": q(shared), "cells_empty_in_both": q(both_empty),
            "both_empty_cells_with_different_mask": q(diff_cells), "different_bits_on_both_empty_cells": q(diff_bits)}
