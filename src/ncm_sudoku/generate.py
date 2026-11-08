"""Deterministic fresh-puzzle generator (research plan v3.4 §4.1).

Solution: randomized backtracking fill with a shuffled digit order per cell
(not proven uniform over grids). Clues: one pass over a random cell order,
keeping a removal only if the solution stays unique, until exactly `n_clues`
remain; an attempt ending above `n_clues` restarts with a new order on the same
solution, up to `max_attempts`. The puzzle id is the generation provenance.
"""

from dataclasses import dataclass

import numpy as np

from ncm_sudoku.solve import count_solutions

GENERATOR_VERSION = "gen-v1"


class GenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeneratedPuzzle:
    puzzle: np.ndarray
    solution: np.ndarray
    puzzle_id: str
    seed: int
    index: int
    attempts: int


def random_solution(rng: np.random.Generator) -> np.ndarray:
    g = np.zeros(81, dtype=np.int8)
    rows = [set() for _ in range(9)]
    cols = [set() for _ in range(9)]
    boxes = [set() for _ in range(9)]

    def fill(c):
        if c == 81:
            return True
        r, k = divmod(c, 9)
        b = (r // 3) * 3 + k // 3
        for d in rng.permutation(np.arange(1, 10)).tolist():
            if d in rows[r] or d in cols[k] or d in boxes[b]:
                continue
            g[c] = d
            rows[r].add(d)
            cols[k].add(d)
            boxes[b].add(d)
            if fill(c + 1):
                return True
            rows[r].discard(d)
            cols[k].discard(d)
            boxes[b].discard(d)
        g[c] = 0
        return False

    assert fill(0)
    return g


def generate_puzzle(seed: int, index: int, n_clues: int = 30, max_attempts: int = 50) -> GeneratedPuzzle:
    rng = np.random.default_rng([seed, index])
    solution = random_solution(rng)
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
            return GeneratedPuzzle(
                puzzle=puzzle,
                solution=solution,
                puzzle_id=f"{GENERATOR_VERSION}-{seed}-{index}",
                seed=seed,
                index=index,
                attempts=attempt,
            )
    raise GenerationError(f"seed={seed} index={index}: {n_clues} clues not reached in {max_attempts} attempts")


def generate_many(seed: int, n: int, n_clues: int = 30) -> list[GeneratedPuzzle]:
    return [generate_puzzle(seed, i, n_clues=n_clues) for i in range(n)]
