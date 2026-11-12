"""Frozen CAL code frequencies for every level (v3.7 review CARBON-1; plan §7, §12.2).

Usage: uv run python scripts/lock_cal_freqs.py [--force]
Regenerates the clean generated codes A of the 300 CAL puzzles exactly as
scripts/e2_pilot2.py does (frozen-generator guard, `generate_subset("cal", 300)`,
`load_model`, `e2p2.clean_codes` with chunks of 50, the path `run_pilot2` uses) and
writes experiments/lock/cal_freqs.json (atomic): per level 1..12 the 16 code counts and
the frequencies (`perturb.code_frequencies`: counts / sum in float64, stored as float32),
n_cal, the CAL ids, code state and environment. The level-1 frequencies must equal
experiments/e2p2/summary.json `freqs_level1` exactly; otherwise the script exits non-zero
without writing. `e2p2.load_frozen_freqs` reads the file for `run_pilot2(frozen_freqs=...)`.
Refuses to overwrite experiments/lock/cal_freqs.json unless --force.
"""

import json
import os
import sys
import time

import numpy as np
import torch

from ncm_sudoku.e2p2 import clean_codes
from ncm_sudoku.g0 import code_state, environment_record
from ncm_sudoku.model import ROOT, level_slices, load_model
from ncm_sudoku.perturb import N_CODES, code_frequencies
from ncm_sudoku.subsets import assert_generator_frozen, generate_subset

N_CAL = 300
CHUNK = 50  # run_pilot2 default
OUT = ROOT / "experiments" / "lock" / "cal_freqs.json"
SUMMARY = ROOT / "experiments" / "e2p2" / "summary.json"
NOTE = ("CAL code frequencies frozen before the lock (v3.7 review CARBON-1): the E2 frequency policy "
        "on TEST uses these instead of re-estimating them from the TEST codes")


def guard(force: bool) -> None:
    if OUT.exists() and not force:
        sys.exit(f"{OUT} exists: lock_cal_freqs is a rerun-guarded script; use --force to overwrite")


def main() -> None:
    guard(force="--force" in sys.argv)
    assert_generator_frozen()
    environment = environment_record()
    batch = generate_subset("cal", N_CAL)
    puzzles = np.stack([g.puzzle for g in batch])
    m = load_model(ROOT / "checkpoints" / "sudoku" / "hard")
    t0 = time.perf_counter()
    A = clean_codes(m, puzzles, CHUNK)
    freqs = code_frequencies(A, m.levels)
    levels = {}
    for lv, (sl, f) in enumerate(zip(level_slices(m.levels), freqs), start=1):
        counts = torch.bincount(A[:, sl].reshape(-1), minlength=N_CODES)
        levels[str(lv)] = {"n_codes_per_puzzle": sl.stop - sl.start, "counts": counts.tolist(),
                           "frequencies": f.tolist()}
    pilot = json.loads(SUMMARY.read_text(encoding="utf-8"))["freqs_level1"]
    if levels["1"]["frequencies"] != pilot:
        sys.exit(f"ERROR: level-1 CAL frequencies {levels['1']['frequencies']} differ from {SUMMARY} "
                 f"freqs_level1 {pilot}; nothing written")
    out = {
        "note": NOTE, "date": time.strftime("%Y-%m-%d"), "code": code_state(), "environment": environment,
        "subset": "cal", "n_cal": len(batch), "ids": [g.puzzle_id for g in batch], "chunk": CHUNK,
        "frequency_rule": "counts / sum in float64, cast to float32 (perturb.code_frequencies)",
        "level1_matches_pilot": True, "levels": levels,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, OUT)
    print(json.dumps({"n_cal": out["n_cal"], "level1_matches_pilot": True, "seconds": out["seconds"]}))


if __name__ == "__main__":
    main()
