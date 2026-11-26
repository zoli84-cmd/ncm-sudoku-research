"""E5 causal pilot diagnostic: step-direction cosines for every condition (D104; no model).

Usage: uv run --locked python scripts/e5_causal_cosines.py [--force]

For each both-empty cell of each PROBE-VAL pair, Delta = x_b − x_a at layer 2 from the
saved level-7-pass prefix activations (fp16, `runs/e5/acts/probe_val/<a|b>/prefix_cells.npy`);
the sign of Delta flips with the order, which leaves every cosine below unchanged.
Cosine between the injected step and Delta: for a subspace projection P_S, ||P_S Delta|| / ||Delta||
(independent of the norm-matching scale); for the shuffled-digit step W⁺ Π W Delta, the
plain cosine. Same Q, random bases (seeds 1000..1019), high-variance basis and W as
scripts/e5_causal.py. Validation: the Q cosine is compared with the value the primary
run logged in float32 activations captured online (`experiments/e5/causal/primary.json`).
Writes experiments/e5/causal/cosines.json.
"""

import json
import sys

import numpy as np
import torch

from ncm_sudoku.e5causal import high_variance_basis, orthonormal_rows, random_basis, shuffled_raw, state_weights
from ncm_sudoku.e5pilot import load_subset
from ncm_sudoku.g0 import code_state
from ncm_sudoku.model import ROOT

OUT = ROOT / "experiments" / "e5" / "causal" / "cosines.json"
DRAWS = 20


def cell_deltas(d: dict) -> tuple[np.ndarray, np.ndarray]:
    n = d["n_pairs"]
    xa = np.load(d["acts"] / "a" / "prefix_cells.npy", mmap_mode="r")[:, 2].astype(np.float64)
    xb = np.load(d["acts"] / "b" / "prefix_cells.npy", mmap_mode="r")[:, 2].astype(np.float64)
    both = d["empty"][:n] & d["empty"][n:]
    pair = np.nonzero(both)[0]
    return (xb - xa)[both], pair


def main() -> None:
    if OUT.exists() and "--force" not in sys.argv:
        sys.exit(f"{OUT.relative_to(ROOT)} exists; use --force")
    heads = torch.load(ROOT / "runs" / "e5" / "causal" / "heads" / "P2.pt", weights_only=True)
    W = state_weights(heads)
    Q, _ = orthonormal_rows(W)
    tr = load_subset(ROOT, "probe_train")
    dtr, _ = cell_deltas(tr)
    B = high_variance_basis(dtr, Q)
    val = load_subset(ROOT, "probe_val")
    delta, pair = cell_deltas(val)
    dn = np.linalg.norm(delta, axis=1)

    def proj_cos(S):
        return np.linalg.norm(delta @ S, axis=1) / dn

    sh = shuffled_raw(delta, W)
    cos = {"Q": proj_cos(Q), "high_variance": proj_cos(B),
           "shuffled_digit": (sh * delta).sum(1) / (np.linalg.norm(sh, axis=1) * dn)}
    rand = np.stack([proj_cos(random_basis(1000 + j)) for j in range(DRAWS)])

    def per_pair_mean(c):
        return float(np.mean([c[pair == i].mean() for i in np.unique(pair)]))

    logged = json.loads((ROOT / "experiments" / "e5" / "causal" / "primary.json").read_text())["diagnostics"]["cos_Q"]
    rec = {
        "note": "E5 causal pilot diagnostic (D104): cosine between the injected step and Delta = x_d − x_r per condition; "
                "computed from the saved fp16 level-7-pass prefix activations; no model run",
        "n_cells": int(len(delta)), "n_pairs": int(len(np.unique(pair))),
        "cell_mean": {**{k: float(v.mean()) for k, v in cos.items()},
                      "random_mean_over_draws": float(rand.mean()), "random_draw_min": float(rand.mean(1).min()),
                      "random_draw_max": float(rand.mean(1).max())},
        "pair_mean": {**{k: per_pair_mean(v) for k, v in cos.items()},
                      "random_mean_over_draws": float(np.mean([per_pair_mean(r) for r in rand]))},
        "validation": {"cos_Q_logged_by_primary_run_fp32": logged, "cos_Q_here_fp16": float(cos["Q"].mean())},
        "code_state": code_state(),
    }
    OUT.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: rec[k] for k in ("cell_mean", "pair_mean", "validation")}, indent=1))


if __name__ == "__main__":
    main()
