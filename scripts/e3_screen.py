"""Exact canonical-form (orbit) screen across the E3 preparation subsets and the released set.

Usage: uv run python scripts/e3_screen.py
Writes experiments/e3prep/screen.json (with the code state). Model-free; safe to rerun (deterministic).
Non-confirmatory planning output.
"""

import json
import time

from ncm_sudoku.g0 import code_state
from ncm_sudoku.gate import GATE_N
from ncm_sudoku.model import ROOT
from ncm_sudoku.released import load_released
from ncm_sudoku.subsets import assert_generator_frozen, generate_subset
from ncm_sudoku.symmetry import screen_canonical

SIZES = {"gate": GATE_N, "cal": 300, "probe_train": 2000, "probe_val": 500}


def main() -> None:
    t0 = time.perf_counter()
    assert_generator_frozen()
    _, released_s = load_released(ROOT / "data" / "released" / "sudoku" / "hard")
    subsets = {name: generate_subset(name, n) for name, n in SIZES.items()}
    scr = screen_canonical(subsets, released_s)
    out = ROOT / "experiments" / "e3prep" / "screen.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    result = {"note": "non-confirmatory planning output", "date": time.strftime("%Y-%m-%d"),
              "code": code_state(), "subsets": {k: len(v) for k, v in subsets.items()}, **scr,
              "seconds": round(time.perf_counter() - t0, 1)}
    out.write_text(json.dumps(result, indent=2) + "\n", newline="\n")
    print(json.dumps({k: result[k] for k in ("n_entries", "exact_duplicates", "seconds")} | {"classes": len(scr["classes"])}))


if __name__ == "__main__":
    main()
