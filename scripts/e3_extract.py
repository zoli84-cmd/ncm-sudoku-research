"""E3 PROBE data extraction (plan v3.6 §8.1-§8.3, §12.1; D54-D57). Non-confirmatory
planning output.

Generates PROBE-TRAIN (2,000) and PROBE-VAL (500) from the frozen generator, extracts
generated and teacher cell states (12/3 levels) plus logical labels, and streams them to
runs/e3prep/<name>/ (ids.json, puzzles.npy, solutions.npy, solve.npy, mask.npy, empty.npy,
depth.npy, L01.npy..L12.npy, T02.npy, T06.npy, T12.npy). Writes a summary to
experiments/e3prep/extract.json.

Usage: uv run python scripts/e3_extract.py [--force]
Refuses to run if runs/e3prep/probe_val/L12.npy already exists, unless --force.
"""

import json
import os
import sys
import time

import numpy as np

from ncm_sudoku.e3data import TEACHER_LEVELS, extract_streamed, labels, save_subset
from ncm_sudoku.g0 import environment_record
from ncm_sudoku.labels import CENSORED, STUCK
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.subsets import SEEDS, assert_generator_frozen, generate_subset

RUNS = ROOT / "runs" / "e3prep"
OUT = ROOT / "experiments" / "e3prep" / "extract.json"
GUARD = RUNS / "probe_val" / "L12.npy"
SUBSETS = {"probe_train": 2000, "probe_val": 500}
BATCH = 50


def guard(force: bool) -> None:
    if GUARD.exists() and not force:
        sys.exit(f"{GUARD} exists: e3_extract is a rerun-guarded script; use --force to overwrite")


def _depth_distribution(depth: np.ndarray, empty: np.ndarray) -> dict:
    """Counts over empty cells only, binned 1, 2, 3, >=4, stuck, censored (plan §8.2)."""
    d = depth[empty]
    return {
        "1": int((d == 1).sum()),
        "2": int((d == 2).sum()),
        "3": int((d == 3).sum()),
        ">=4": int((d >= 4).sum()),
        "stuck": int((d == STUCK).sum()),
        "censored": int((d == CENSORED).sum()),
    }


def _subset_stats(puzzles: np.ndarray, lab: dict, solve: np.ndarray) -> dict:
    empty, mask = lab["empty"], lab["mask"]
    n_empty = int(empty.sum())
    prevalence = [float(mask[..., d][empty].mean()) for d in range(9)]
    mean_candidates = float(mask[empty].sum(axis=-1).mean()) if n_empty else None
    return {
        "n": len(puzzles),
        "n_empty_cells": n_empty,
        "label_prevalence_per_digit": prevalence,
        "mean_candidates_per_empty_cell": mean_candidates,
        "depth_distribution": _depth_distribution(lab["depth"], empty),
        "generated_solve_rate": float(np.mean(solve)),
    }


def main() -> None:
    guard(force="--force" in sys.argv)
    assert_generator_frozen()
    t0 = time.perf_counter()
    environment = environment_record()  # before the long run, so a late failure loses nothing
    m = load_model(ROOT / "checkpoints" / "sudoku" / "hard")
    stats = {}
    for name, n in SUBSETS.items():
        batch = generate_subset(name, n)
        puzzles = np.stack([g.puzzle for g in batch])
        solutions = np.stack([g.solution for g in batch])
        ids = [g.puzzle_id for g in batch]
        lab = labels(puzzles)
        solve = extract_streamed(m, RUNS / name, puzzles, solutions, batch=BATCH)
        save_subset(RUNS, name, ids, puzzles, solutions, {"solve": solve}, lab)
        stats[name] = _subset_stats(puzzles, lab, solve)
    result = {
        "note": "non-confirmatory planning output",
        "date": time.strftime("%Y-%m-%d"),
        "environment": environment,
        "seed_namespaces": {name: SEEDS[name] for name in SUBSETS},
        "levels": list(range(1, 13)),
        "teacher_levels": list(TEACHER_LEVELS),
        "subsets": stats,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, indent=2) + "\n", newline="\n")
    os.replace(tmp, OUT)
    print(json.dumps({k: result[k] for k in ("subsets", "seconds")}, indent=2))


if __name__ == "__main__":
    main()
