"""E1 on the released boards or on CAL (plan §6, D37).

Usage: uv run python scripts/wp1_e1.py --subset released|cal
Writes experiments/wp1/e1_<subset>.json.
"""

import argparse
import json
import time

import numpy as np

from ncm_sudoku.e1 import e1_summary
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.released import load_released
from ncm_sudoku.subsets import generate_subset


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subset", required=True, choices=["released", "cal"])
    args = ap.parse_args()
    if args.subset == "released":
        puzzles, solutions = load_released(ROOT / "data" / "released" / "sudoku" / "hard")
    else:
        batch = generate_subset("cal", 300)
        puzzles = np.stack([g.puzzle for g in batch])
        solutions = np.stack([g.solution for g in batch])
    m = load_model(ROOT / "checkpoints" / "sudoku" / "hard")
    t0 = time.perf_counter()
    result = e1_summary(m, puzzles, solutions)
    result.update({"subset": args.subset, "date": time.strftime("%Y-%m-%d"),
                   "seconds": round(time.perf_counter() - t0, 1)})
    out = ROOT / "experiments" / "wp1" / f"e1_{args.subset}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", newline="\n")
    print(json.dumps({k: result[k] for k in ("n", "teacher", "generated", "hamming")}, indent=2))


if __name__ == "__main__":
    main()
