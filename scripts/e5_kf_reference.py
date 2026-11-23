"""E5 positive control, reference: the upstream scikit-learn probes on our extracted activations (D94).

Runs in the separate KF environment:

    UV_PROJECT_ENVIRONMENT=.venv-kf PYTHONPATH=third_party/sudoku-residual \
        .venv-kf/Scripts/python.exe scripts/e5_kf_reference.py [--dtype bfloat16] [--layers 4 5 6] [--force | --resume]

Calls `_probe_cell_accs(acts, puzzles, cell, "candidates")` from the upstream
`plots/scripts/fig_probe_acc_by_layer.py` (pinned commit) unchanged, for the 81 cells
of each layer, and averages the per-cell exact match with `np.nanmean`, as their
figure does. Also writes the upstream candidate labels (`CandidatesMode.build_targets`)
to runs/e5/kf/upstream_targets.npy so that scripts/e5_kf_control.py can check our
labels against them. Record: experiments/e5/kf_reference_<dtype>.json, written after
every layer.
"""

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
KF = ROOT / "third_party" / "sudoku-residual"
RUNS = ROOT / "runs" / "e5" / "kf"
META = ROOT / "data" / "kf" / "artifacts" / "results" / "3M-backtracking-packing" / "activations.npz"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dtype", choices=["bfloat16", "float32"], default="bfloat16")
    ap.add_argument("--layers", type=int, nargs="+", default=[4, 5, 6, 1, 2, 3, 7, 8])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--force", action="store_true")
    g.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    out = ROOT / "experiments" / "e5" / f"kf_reference_{args.dtype}.json"
    if out.exists() and not (args.force or args.resume):
        sys.exit(f"{out.relative_to(ROOT)} exists; use --force or --resume")

    sys.path.insert(0, str(KF))
    import os
    os.chdir(KF)  # the figure module resolves its defaults relative to the repository root
    spec = importlib.util.spec_from_file_location("fig_probe_acc_by_layer", KF / "plots" / "scripts" / "fig_probe_acc_by_layer.py")
    fig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fig)
    from sudoku.probes.modes import CandidatesMode

    ext = json.loads((ROOT / "experiments" / "e5" / f"kf_extract_{args.dtype}.json").read_text())
    acts_path = ROOT / ext["outputs"]["acts"]["path"]
    if sha256(acts_path) != ext["outputs"]["acts"]["sha256"]:
        sys.exit("activations do not match their extraction record")
    acts = np.load(acts_path)
    with np.load(META, allow_pickle=False) as meta:
        puzzles = [str(p) for p in meta["puzzles"]]

    targets_path = RUNS / "upstream_targets.npy"
    if not targets_path.exists():
        mode = CandidatesMode()
        targets = np.stack([mode.build_targets(puzzles, c)[0] for c in range(81)], axis=1).astype(np.float32)
        np.save(targets_path, targets)

    record = json.loads(out.read_text()) if (args.resume and out.exists()) else {"layers": {}}
    record.update({
        "date": time.strftime("%Y-%m-%d"),
        "note": "E5 positive-control reference (D94): upstream _probe_cell_accs (candidates) on our extracted activations",
        "dtype": args.dtype,
        "acts_sha256": ext["outputs"]["acts"]["sha256"],
        "upstream_targets_sha256": sha256(targets_path),
        "upstream_code": "plots/scripts/fig_probe_acc_by_layer.py::_probe_cell_accs at a9b206955bfd1089a7253511fa9371066ecca570",
    })
    for layer in args.layers:
        if str(layer) in record["layers"]:
            continue
        t0 = time.perf_counter()
        pairs = [fig._probe_cell_accs(acts[:, layer - 1], puzzles, c, "candidates") for c in range(81)]
        ew, em = zip(*pairs)
        record["layers"][str(layer)] = {
            "exact_match_mean": float(np.nanmean(em)),
            "elementwise_mean": float(np.nanmean(ew)),
            "exact_match_per_cell": [round(float(v), 6) for v in em],
            "seconds": round(time.perf_counter() - t0, 1),
        }
        out.write_text(json.dumps(record, indent=2) + "\n", newline="\n")
        print(f"layer {layer}: exact match {record['layers'][str(layer)]['exact_match_mean']:.4f} "
              f"({record['layers'][str(layer)]['seconds']} s)", flush=True)


if __name__ == "__main__":
    main()
