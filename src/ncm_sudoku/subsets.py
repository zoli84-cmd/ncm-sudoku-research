"""Analysis subsets: seed namespaces, frozen-generator guard, duplicate screening (D33, D36)."""

import hashlib
import json
from pathlib import Path

import numpy as np

from ncm_sudoku.generate import GeneratedPuzzle, generate_many

SEEDS = {"gate": 1, "cal": 2, "probe_train": 3, "probe_val": 4, "select": 5, "test": 6, "e4_test": 7}
DEV_SEED = 20261109
FROZEN_NUMPY = "2.5.4"  # the generator RNG stream depends on numpy (D33)
FROZEN_SHA256 = {
    "generate.py": "57a8bfe55767c3e0be450307d5a09a390e13fa5aabe884ed826e200276d2a2ec",
    "solve.py": "9f3e6df5ca6e0c91c448c459cb164c398ada77c462308d9bc2e07043948c0e5e",
}
_PKG = Path(__file__).resolve().parent


def assert_generator_frozen() -> None:
    if np.__version__ != FROZEN_NUMPY:
        raise RuntimeError(f"numpy {np.__version__} != frozen {FROZEN_NUMPY} (D33)")
    for name, expected in FROZEN_SHA256.items():
        actual = hashlib.sha256((_PKG / name).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"{name} changed since the D33 freeze ({actual} != {expected})")


def generate_subset(name: str, n: int) -> list[GeneratedPuzzle]:
    assert_generator_frozen()
    return generate_many(SEEDS[name], n)


def sha256_ids(ids) -> str:
    """SHA-256 of json.dumps(ids) (generation order, default separators, ensure_ascii), UTF-8."""
    return hashlib.sha256(json.dumps(list(ids)).encode("utf-8")).hexdigest()


def sha256_array(a) -> str:
    return hashlib.sha256(np.ascontiguousarray(np.asarray(a, dtype=np.uint8)).tobytes(order="C")).hexdigest()


def solution_signature(solution: np.ndarray) -> tuple:
    """Symmetry-invariant screen: cycle types of all 36 digit-pair row permutations.

    For digits a, b let col_d(r) be the column of d in row r; the row permutation
    r -> col_a^{-1}(col_b(r)) has a cycle type that is unchanged by row and column
    permutations (conjugation), transposition and digit relabeling (which only
    permutes the pairs). Equal signatures flag candidate orbit duplicates; it is a
    screen, not a canonical form.
    """
    g = np.asarray(solution).reshape(9, 9)
    col = {d: [int(np.flatnonzero(g[r] == d)[0]) for r in range(9)] for d in range(1, 10)}
    row_of = {d: {c: r for r, c in enumerate(col[d])} for d in col}
    types = []
    for a in range(1, 10):
        for b in range(a + 1, 10):
            seen, cycles = set(), []
            for r0 in range(9):
                if r0 in seen:
                    continue
                r, length = r0, 0
                while r not in seen:
                    seen.add(r)
                    length += 1
                    r = row_of[a][col[b][r]]
                cycles.append(length)
            types.append(tuple(sorted(cycles)))
    return tuple(sorted(types))


def screen(subsets: dict[str, list[GeneratedPuzzle]], released_solutions: np.ndarray) -> dict:
    entries = [(f"released-{i}", s) for i, s in enumerate(released_solutions)]
    for puzzles in subsets.values():
        entries += [(p.puzzle_id, p.solution) for p in puzzles]
    by_bytes: dict[bytes, str] = {}
    by_sig: dict[tuple, list[tuple[str, bytes]]] = {}
    exact, collisions = [], []
    for pid, sol in entries:
        key = np.asarray(sol, dtype=np.int8).tobytes()
        if key in by_bytes:
            exact.append((by_bytes[key], pid))
            continue
        by_bytes[key] = pid
        sig = solution_signature(sol)
        for other_id, _ in by_sig.get(sig, []):
            collisions.append((other_id, pid))
        by_sig.setdefault(sig, []).append((pid, key))
    return {"n_entries": len(entries), "exact_duplicates": exact, "signature_collisions": collisions}
