"""E2 sample-size simulation from the pilot-2 output (plan v3.6 §11.4). Non-confirmatory.

Usage: uv run python scripts/e2_sample_size.py
Reads runs/e2p2/pilot2.json, builds the frequency-policy puzzle-level arrays for theta2,
theta_comp and theta2_prime with ncm_sudoku.e2p2.puzzle_values, and writes
experiments/e2p2/sample_size_e2.json from ncm_sudoku.power.e2_sample_size. Deterministic
(fixed simulation seed); safe to rerun.
"""

import json

from ncm_sudoku.e2p2 import puzzle_values
from ncm_sudoku.model import ROOT
from ncm_sudoku.power import e2_sample_size

RAW = ROOT / "runs" / "e2p2" / "pilot2.json"
OUT = ROOT / "experiments" / "e2p2" / "sample_size_e2.json"


def main() -> None:
    out = json.loads(RAW.read_text(encoding="utf-8"))
    values = {c: list(puzzle_values(out, c, "frequency").values())
              for c in ("theta2", "theta_comp", "theta2_prime")}
    result = e2_sample_size(values)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", newline="\n")


if __name__ == "__main__":
    main()
