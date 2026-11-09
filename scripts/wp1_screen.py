"""Duplicate and signature screen across all generated WP1 subsets (D36).

Usage: uv run python scripts/wp1_screen.py
Writes experiments/wp1/screen.json. Model-free; safe to rerun (deterministic).
"""

import json
import time

from ncm_sudoku.gate import GATE_N
from ncm_sudoku.model import ROOT
from ncm_sudoku.released import load_released
from ncm_sudoku.subsets import assert_generator_frozen, generate_subset, screen

N_CAL = 300


def main() -> None:
    assert_generator_frozen()
    _, released_s = load_released(ROOT / "data" / "released" / "sudoku" / "hard")
    subsets = {"gate": generate_subset("gate", GATE_N), "cal": generate_subset("cal", N_CAL)}
    scr = screen(subsets, released_s)
    out = ROOT / "experiments" / "wp1" / "screen.json"
    out.write_text(json.dumps({"date": time.strftime("%Y-%m-%d"), "subsets": {k: len(v) for k, v in subsets.items()},
                               **scr}, indent=2) + "\n", newline="\n")
    cal = [p for p in scr["signature_collisions"] if any("-2-" in x for x in p)]
    print(json.dumps({"n_entries": scr["n_entries"], "exact_duplicates": scr["exact_duplicates"],
                      "signature_collisions": len(scr["signature_collisions"]), "involving_cal": len(cal)}))


if __name__ == "__main__":
    main()
