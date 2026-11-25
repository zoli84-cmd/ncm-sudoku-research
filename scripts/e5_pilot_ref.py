"""E5 remaining pilot items (D101(6); non-confirmatory).

Usage: uv run --locked python scripts/e5_pilot_ref.py [--force]

Converged L-BFGS L2 logistic reference (inputs standardized with PROBE-TRAIN statistics,
C grid `e5pilot.LBFGS_CS`, selection on the PROBE-VAL Brier) for z6 (shared and whole),
P2 and P8 (shared); online MDL code length (`e5pilot.online_mdl`, C = 1) for z6, P0 and
P2 on the shared own-position rows of PROBE-TRAIN. Writes
experiments/e5/pilot/<rep>__<readout>__lbfgs.json (+ predictions in runs/e5/pilot/) and
experiments/e5/pilot/<rep>__shared__mdl.json; finished items are skipped unless --force.
"""

import argparse
import json
import time

from ncm_sudoku.e5pilot import PCA_K, load_subset, online_mdl, representation, run_lbfgs, save
from ncm_sudoku.g0 import code_state
from ncm_sudoku.model import ROOT
from ncm_sudoku.wholelayer import cell_pca_features

OUT = ROOT / "experiments" / "e5" / "pilot"
RAW = ROOT / "runs" / "e5" / "pilot"
LBFGS = [("z6", "shared"), ("z6", "whole"), ("P2", "shared"), ("P8", "shared")]
MDL = ["z6", "P0", "P2"]
NOTE = "E5 pilot (D101(6)), non-confirmatory; fit on PROBE-TRAIN pairs, scored on PROBE-VAL pairs"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    train, val = load_subset(ROOT, "probe_train"), load_subset(ROOT, "probe_val")
    state = code_state()
    for rep, readout in LBFGS:
        stem = f"{rep}__{readout}__lbfgs"
        if (OUT / f"{stem}.json").exists() and not args.force:
            continue
        t0 = time.perf_counter()
        r_tr, r_va = representation(train, rep), representation(val, rep)
        if readout == "whole":
            _, _, r_tr, r_va, _ = cell_pca_features(r_tr, r_va, train["empty"], val["empty"], PCA_K)
        res = run_lbfgs(r_tr, r_va, train, val)
        res.update({"representation": rep, "readout": readout, "control": "lbfgs_reference",
                    "seconds": round(time.perf_counter() - t0, 1), "code_state": state, "note": NOTE})
        save(res, OUT / f"{stem}.json", RAW / f"{stem}.npy")
        print(json.dumps({"stem": stem, "seconds": res["seconds"], "w_auc": res["w_auc"]["overall"],
                          "brier": res["summary"]["val_brier_mean"], "C": res["summary"]["config"][1],
                          "converged": [g["converged"] for g in res["summary"]["grid"]], **res["metrics"]}), flush=True)
    for rep in MDL:
        path = OUT / f"{rep}__shared__mdl.json"
        if path.exists() and not args.force:
            continue
        t0 = time.perf_counter()
        res = online_mdl(representation(train, rep), train)
        res.update({"representation": rep, "readout": "shared", "seconds": round(time.perf_counter() - t0, 1),
                    "code_state": state, "note": NOTE})
        path.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"mdl": rep, "compression": res["compression"], "bits": res["online_codelength_bits"],
                          "uniform": res["uniform_codelength_bits"], "seconds": res["seconds"]}), flush=True)


if __name__ == "__main__":
    main()
