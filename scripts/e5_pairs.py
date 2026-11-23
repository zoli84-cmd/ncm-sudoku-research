"""E5 counterfactual PROBE pairs (D97, D99): one solution, two clue masks.

Usage: uv run --locked python scripts/e5_pairs.py [--force]

Generates PROBE-TRAIN (1,000 pairs, seed namespace 8) and PROBE-VAL (250 pairs,
namespace 9) with `ncm_sudoku.e5pairs` (generator guard included); the TEST pairs
(namespace 10) are generated only after the E5 protocol is fixed, by a later run.
Screens the pair solutions by exact canonical form (`symmetry.screen_canonical`)
against gate, CAL, PROBE-TRAIN, PROBE-VAL, the WP2 TEST, the released hard set and
each other; a pair whose solution shares a class with any other entry is excluded and
replaced by the next index (rule fixed before the run). Does not load the model.

Writes runs/e5/pairs/<subset>/ (ids.json, a.npy, b.npy, solutions.npy; uint8) and
experiments/e5/pairs.json (ids, SHA-256, screen, exclusions, contrast statistics,
generator hashes, code state). Refuses to overwrite unless --force.
"""

import json
import sys
import time
from types import SimpleNamespace

import numpy as np

from ncm_sudoku.e5pairs import PAIR_SEEDS, PAIR_VERSION, contrast_stats, generate_pair
from ncm_sudoku.g0 import code_state
from ncm_sudoku.gate import GATE_N
from ncm_sudoku.model import ROOT
from ncm_sudoku.released import load_released
from ncm_sudoku.subsets import FROZEN_NUMPY, FROZEN_SHA256, assert_generator_frozen, generate_subset, sha256_array, sha256_ids
from ncm_sudoku.symmetry import screen_canonical

SIZES = {"probe_train": 1000, "probe_val": 250}
EXISTING = {"gate": GATE_N, "cal": 300, "probe_train": 2000, "probe_val": 500, "test": 600}
OUT = ROOT / "experiments" / "e5" / "pairs.json"
DATA = ROOT / "runs" / "e5" / "pairs"


def main() -> None:
    if OUT.exists() and "--force" not in sys.argv:
        sys.exit(f"{OUT.relative_to(ROOT)} exists; use --force")
    assert_generator_frozen()
    t0 = time.perf_counter()
    existing = {name: generate_subset(name, n) for name, n in EXISTING.items()}
    _, released_s = load_released(ROOT / "data" / "released" / "sudoku" / "hard")

    pairs, next_index = {}, {}
    for name, n in SIZES.items():
        seed = PAIR_SEEDS[f"pairs_{name}"]
        pairs[name] = [generate_pair(seed, i) for i in range(n)]
        next_index[name] = n
    exclusions = []
    while True:
        entries = {f"existing_{k}": v for k, v in existing.items()}
        for name, ps in pairs.items():
            entries[f"pairs_{name}"] = [SimpleNamespace(puzzle_id=p.pair_id, solution=p.solution) for p in ps]
        scr = screen_canonical(entries, released_s)
        flagged = {pid for cls in scr["classes"] for pid in cls if pid.startswith(PAIR_VERSION)}
        flagged |= {pid for dup in scr["exact_duplicates"] for pid in dup if pid.startswith(PAIR_VERSION)}
        if not flagged:
            break
        for name in SIZES:
            seed = PAIR_SEEDS[f"pairs_{name}"]
            keep = [p for p in pairs[name] if p.pair_id not in flagged]
            exclusions += [p.pair_id for p in pairs[name] if p.pair_id in flagged]
            while len(keep) < SIZES[name]:
                keep.append(generate_pair(seed, next_index[name]))
                next_index[name] += 1
            pairs[name] = keep

    result = {"note": "E5 counterfactual PROBE pairs (D97, D99), non-confirmatory; no model was run",
              "date": time.strftime("%Y-%m-%d"), "code": code_state(), "version": PAIR_VERSION,
              "generator": {"numpy": FROZEN_NUMPY, "sha256": dict(FROZEN_SHA256)}, "subsets": {},
              "screen": {"method": "exact canonical form of the solution grids (symmetry.screen_canonical)",
                         "against": {**EXISTING, "released": len(released_s)}, "n_entries": scr["n_entries"],
                         "classes_without_pairs": len(scr["classes"]), "exclusions": exclusions},
              "seconds": None}
    for name, ps in pairs.items():
        d = DATA / name
        d.mkdir(parents=True, exist_ok=True)
        ids = [p.pair_id for p in ps]
        arrays = {"a": np.stack([p.a for p in ps]).astype(np.uint8), "b": np.stack([p.b for p in ps]).astype(np.uint8),
                  "solutions": np.stack([p.solution for p in ps]).astype(np.uint8)}
        (d / "ids.json").write_text(json.dumps(ids) + "\n", encoding="utf-8", newline="\n")
        for k, v in arrays.items():
            np.save(d / f"{k}.npy", v)
        result["subsets"][name] = {
            "seed_namespace": PAIR_SEEDS[f"pairs_{name}"], "count": len(ids), "ids": ids,
            "sha256": {"ids": sha256_ids(ids), **{k: sha256_array(v) for k, v in arrays.items()}},
            "attempts_total": int(sum(sum(p.attempts) for p in ps)),
            "contrast": contrast_stats(ps),
            "storage": str(d.relative_to(ROOT)).replace("\\", "/"),
        }
    result["seconds"] = round(time.perf_counter() - t0, 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: {"count": v["count"], "contrast": v["contrast"]} for k, v in result["subsets"].items()}, indent=1))
    print("exclusions", exclusions, "seconds", result["seconds"])


if __name__ == "__main__":
    main()
