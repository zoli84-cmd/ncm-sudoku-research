"""E5 causal pilot step 1 (D102(1)): refit and save the P2, P4, P8 shared heads.

Usage: uv run --locked python scripts/e5_causal_heads.py [--force]

Refits each head at its selected pilot configuration (`ncm_sudoku.e5causal.refit_head`),
compares the seed-averaged PROBE-VAL predictions with the saved pilot predictions,
saves the seed state dicts to runs/e5/causal/heads/<rep>.pt and writes
experiments/e5/causal/heads.json (configs, reproduction differences, the P2 row-space
singular values and the SHA-256 of each saved file). Refuses to overwrite unless --force.
"""

import hashlib
import json
import sys
import time

import numpy as np
import torch

from ncm_sudoku.e5causal import orthonormal_rows, refit_head, state_weights
from ncm_sudoku.g0 import code_state
from ncm_sudoku.model import ROOT

OUT = ROOT / "experiments" / "e5" / "causal" / "heads.json"
DIR = ROOT / "runs" / "e5" / "causal" / "heads"


def main() -> None:
    if OUT.exists() and "--force" not in sys.argv:
        sys.exit(f"{OUT.relative_to(ROOT)} exists; use --force")
    DIR.mkdir(parents=True, exist_ok=True)
    rec = {"note": "E5 causal pilot (D102(1)): refitted pilot heads", "date": time.strftime("%Y-%m-%d"),
           "code_state": code_state(), "heads": {}}
    for rep in ("P2", "P4", "P8"):
        t0 = time.perf_counter()
        res = refit_head(ROOT, rep)
        path = DIR / f"{rep}.pt"
        torch.save(res["state_dicts"], path)
        entry = {"config": res["config"], "max_abs_diff_vs_pilot": res["max_abs_diff_vs_pilot"],
                 "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "seconds": round(time.perf_counter() - t0, 1)}
        if rep == "P2":
            _, s = orthonormal_rows(state_weights(res["state_dicts"]))
            entry["state_row_singular_values"] = [float(x) for x in s]
        rec["heads"][rep] = entry
        print(rep, json.dumps(entry), flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
