"""TEST subset generation and exact canonical-form screen before the lock (D70(3); plan v3.6 §4.1, §12.2).

Usage: uv run python scripts/lock_test_set.py [--force]
Generates the 600 TEST puzzles (seed namespace 6) with ncm_sudoku.subsets.generate_subset
(frozen-generator guard included); does not load the model. Screens the TEST solution grids by
exact canonical form (symmetry.screen_canonical, as scripts/e3_screen.py) against gate, CAL,
PROBE-TRAIN, PROBE-VAL and the released set. Saves runs/lock/test/ (ids.json, puzzles.npy,
solutions.npy; git-ignored, the PROBE subset layout) and writes experiments/lock/test_set.json
with the count, seed namespace, SHA-256 of the ids (json.dumps(ids) over the ids in generation
order, index 0..count-1, default separators, ensure_ascii; UTF-8)
and of the puzzle and solution arrays (uint8, C order), the screen, generator hashes and the
code state. Refuses to overwrite experiments/lock/test_set.json unless --force.
"""

import json
import os
import sys
import time

import numpy as np

from ncm_sudoku.g0 import code_state
from ncm_sudoku.gate import GATE_N
from ncm_sudoku.model import ROOT
from ncm_sudoku.released import load_released
from ncm_sudoku.subsets import FROZEN_NUMPY, FROZEN_SHA256, SEEDS, generate_subset, sha256_array, sha256_ids
from ncm_sudoku.symmetry import screen_canonical

N_TEST = 600
SIZES = {"gate": GATE_N, "cal": 300, "probe_train": 2000, "probe_val": 500}
OUT = ROOT / "experiments" / "lock" / "test_set.json"
DATA = ROOT / "runs" / "lock" / "test"
NOTE = ("TEST subset identity for the lock (plan v3.6 §12.2); generated before the lock without "
        "running the model; no TEST outcome exists")


def guard(force: bool) -> None:
    if OUT.exists() and not force:
        sys.exit(f"{OUT} exists: the TEST set is rerun-guarded; use --force to overwrite")


def _atomic(path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def main() -> None:
    guard(force="--force" in sys.argv)
    t0 = time.perf_counter()
    test = generate_subset("test", N_TEST)
    others = {name: generate_subset(name, n) for name, n in SIZES.items()}
    _, released_s = load_released(ROOT / "data" / "released" / "sudoku" / "hard")
    scr = screen_canonical({**others, "test": test}, released_s)

    ids = [p.puzzle_id for p in test]
    test_ids = set(ids)
    puzzles = np.stack([p.puzzle for p in test]).astype(np.uint8)
    solutions = np.stack([p.solution for p in test]).astype(np.uint8)
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "ids.json").write_text(json.dumps(ids) + "\n", encoding="utf-8", newline="\n")
    np.save(DATA / "puzzles.npy", puzzles)
    np.save(DATA / "solutions.npy", solutions)

    result = {
        "note": NOTE, "non_confirmatory": True, "date": time.strftime("%Y-%m-%d"), "code": code_state(),
        "subset": "test", "seed_namespace": SEEDS["test"], "count": len(ids), "ids": ids,
        "sha256": {"ids": sha256_ids(ids), "puzzles": sha256_array(puzzles), "solutions": sha256_array(solutions)},
        "hash_format": {"ids": "json.dumps(ids) over the ids in generation order (index 0..count-1), default separators (', ', ': '), ensure_ascii=True, encoded as UTF-8",
                        "puzzles": "uint8 array (count, 81), C order, raw bytes; 0 = empty",
                        "solutions": "uint8 array (count, 81), C order, raw bytes"},
        "storage": str(DATA.relative_to(ROOT)) if DATA.is_relative_to(ROOT) else str(DATA),
        "generator": {"numpy": FROZEN_NUMPY, "sha256": dict(FROZEN_SHA256),
                      "attempts_total": int(sum(p.attempts for p in test))},
        "screen": {
            "method": "exact canonical form of the solution grids (symmetry.screen_canonical)",
            "subsets": {**{k: len(v) for k, v in others.items()}, "test": len(test), "released": len(released_s)},
            "n_entries": scr["n_entries"], "classes": scr["classes"], "exact_duplicates": scr["exact_duplicates"],
            "test_classes": [c for c in scr["classes"] if test_ids & set(c)],
            "test_exact_duplicates": [d for d in scr["exact_duplicates"] if test_ids & set(d)],
        },
        "seconds": round(time.perf_counter() - t0, 1),
    }
    _atomic(OUT, json.dumps(result, indent=2) + "\n")
    print(json.dumps({"count": result["count"], **result["sha256"], "classes": len(scr["classes"]),
                      "test_classes": len(result["screen"]["test_classes"]), "seconds": result["seconds"]}))


if __name__ == "__main__":
    main()
