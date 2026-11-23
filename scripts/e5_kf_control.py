"""E5 positive control, step 2: our probe pipeline on the Kniazev & Fijalkow activations (D94, D95).

Usage: uv run --locked python scripts/e5_kf_control.py [--dtype bfloat16] [--layers 4 5 6] [--force | --resume]

Reads runs/e5/kf/acts_<dtype>.npy and split.npy written by scripts/e5_kf_extract.py
(checked against the SHA-256 in experiments/e5/kf_extract_<dtype>.json) and the
probing puzzles from the released activations.npz. Labels: `labels.candidate_mask`
(cross-checked against the upstream labels in runs/e5/kf/upstream_targets.npy when
scripts/e5_kf_reference.py has written them). Per layer (1..8 = after block 1..8):
the untied linear head of `ncm_sudoku.e5probes`, trained on the upstream per-cell
train entries minus a seeded 1/8 validation carve-out, GRID x SEEDS, scored on the
upstream test entries with the seed-averaged predictions.

Gate (D94): mean over the 81 cells of the per-cell exact match >= 0.99 after each of
blocks 4, 5 and 6. Writes experiments/e5/kf_control_<dtype>.json after every layer;
refuses to overwrite unless --force; --resume keeps finished layers.
"""

import argparse
import hashlib
import json
import sys
import time

import numpy as np
import torch

from ncm_sudoku.e3controls import roc_auc
from ncm_sudoku.e5probes import (
    candidate_targets,
    exact_match_per_cell,
    fit_selected_untied,
    grids_from_strings,
    masked_brier,
    validation_carve,
)
from ncm_sudoku.g0 import code_state, environment_record
from ncm_sudoku.model import ROOT

RUNS = ROOT / "runs" / "e5" / "kf"
META = ROOT / "data" / "kf" / "artifacts" / "results" / "3M-backtracking-packing" / "activations.npz"
GATE_LAYERS = (4, 5, 6)
GATE_THRESHOLD = 0.99
VAL_SHARE, VAL_SEED = 0.125, 0


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gate(layers: dict) -> dict | None:
    if not all(str(k) in layers for k in GATE_LAYERS):
        return None
    values = {k: layers[str(k)]["exact_match_mean"] for k in GATE_LAYERS}
    return {"threshold": GATE_THRESHOLD, "layers": list(GATE_LAYERS), "values": values,
            "passed": all(v >= GATE_THRESHOLD for v in values.values())}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dtype", choices=["bfloat16", "float32"], default="bfloat16")
    ap.add_argument("--layers", type=int, nargs="+", default=[4, 5, 6, 1, 2, 3, 7, 8])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--force", action="store_true")
    g.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    out = ROOT / "experiments" / "e5" / f"kf_control_{args.dtype}.json"
    if out.exists() and not (args.force or args.resume):
        sys.exit(f"{out.relative_to(ROOT)} exists; use --force or --resume")

    ext = json.loads((ROOT / "experiments" / "e5" / f"kf_extract_{args.dtype}.json").read_text())
    acts_path = ROOT / ext["outputs"]["acts"]["path"]
    # The split depends only on the puzzles; the bfloat16 extraction record is its reference.
    split_rec = json.loads((ROOT / "experiments" / "e5" / "kf_extract_bfloat16.json").read_text())["outputs"]["split"]
    split_path = ROOT / split_rec["path"]
    for path, want in ((acts_path, ext["outputs"]["acts"]["sha256"]), (split_path, split_rec["sha256"])):
        if sha256(path) != want:
            sys.exit(f"{path.relative_to(ROOT)} does not match its extraction record")
    acts = np.load(acts_path)
    split = np.load(split_path)
    with np.load(META, allow_pickle=False) as meta:
        puzzles = [str(p) for p in meta["puzzles"]]
    grids = grids_from_strings(puzzles)
    Y, empty = candidate_targets(grids)
    if not np.array_equal(split > 0, empty):
        sys.exit("split does not cover exactly the empty cells")
    upstream = RUNS / "upstream_targets.npy"
    label_check = None
    if upstream.exists():
        theirs = np.load(upstream)
        label_check = bool(np.array_equal(theirs[empty], Y[empty]))
        if not label_check:
            sys.exit("our candidate labels differ from the upstream labels on empty cells")

    train, test = split == 1, split == 2
    fit, val = validation_carve(train, VAL_SHARE, VAL_SEED)
    record = json.loads(out.read_text()) if (args.resume and out.exists()) else {"layers": {}}
    record.update({
        "date": time.strftime("%Y-%m-%d"),
        "note": "E5 positive control (D94, D95), non-confirmatory; our probe pipeline on the Kniazev & Fijalkow model",
        "dtype": args.dtype,
        "inputs": {"acts_sha256": ext["outputs"]["acts"]["sha256"], "split_sha256": split_rec["sha256"],
                   "activations_npz_sha256": ext["inputs"]["activations_npz_sha256"]},
        "labels_equal_upstream": label_check,
        "entries": {"fit": int(fit.sum()), "val": int(val.sum()), "test": int(test.sum())},
        "validation_carve": {"share": VAL_SHARE, "seed": VAL_SEED},
        "environment": environment_record(),
        "code_state": code_state(),
    })
    X_all = torch.from_numpy(acts)
    Yt = torch.from_numpy(Y)
    for layer in args.layers:
        if str(layer) in record["layers"]:
            continue
        t0 = time.perf_counter()
        res = fit_selected_untied(X_all[:, layer - 1], Yt, fit, val)
        pred = res["preds"]
        em = exact_match_per_cell(pred, Y, test)
        seed_em = [float(np.nanmean(exact_match_per_cell(p, Y, test))) for p in res["seed_preds"]]
        aucs = [roc_auc(pred[test[:, c], c, d], Y[test[:, c], c, d]) for c in range(81) for d in range(9)]
        record["layers"][str(layer)] = {
            "config": list(res["config"]),
            "val_brier_mean": res["val_brier_mean"],
            "exact_match_mean": float(np.nanmean(em)),
            "exact_match_min_cell": float(np.nanmin(em)),
            "exact_match_per_cell": [round(float(v), 6) for v in em],
            "exact_match_per_seed": seed_em,
            "test_brier": masked_brier(pred, Y, test),
            "roc_auc_mean": float(np.nanmean(aucs)),
            "roc_auc_nan_count": int(np.isnan(aucs).sum()),
            "budget": {f"{wd}_{lr}_{s}": v for (wd, lr, s), v in res["budget"].items()},
            "seconds": round(time.perf_counter() - t0, 1),
        }
        record["gate"] = gate(record["layers"])
        out.write_text(json.dumps(record, indent=2) + "\n", newline="\n")
        print(f"layer {layer}: exact match {record['layers'][str(layer)]['exact_match_mean']:.4f} "
              f"({record['layers'][str(layer)]['seconds']} s)", flush=True)
    print(json.dumps(record["gate"]))


if __name__ == "__main__":
    main()
