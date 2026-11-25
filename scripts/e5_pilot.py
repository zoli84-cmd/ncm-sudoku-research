"""E5 pilot probes (D100; non-confirmatory).

Usage: uv run --locked python scripts/e5_pilot.py --reps P4 z6 ... --readouts shared whole global
                                                 [--controls none permuted labels] [--force]

Fits on the PROBE-TRAIN pairs and selects and scores on the PROBE-VAL pairs
(`ncm_sudoku.e5pilot`). Cell-level readouts ("shared", "whole") apply to z6,
z6_teacher and P<k>; "global" applies to B<k>; other combinations are skipped.
Each (representation, readout, control) result goes to
experiments/e5/pilot/<rep>__<readout>__<control>.json (W-AUC overall, by code
identity and per pair; Brier per puzzle; exact match; ROC-AUC; config and budget;
seconds) and its PROBE-VAL predictions to runs/e5/pilot/ (same stem, .npy).
Finished results are skipped unless --force.
"""

import argparse
import json
import time

from ncm_sudoku.e5pilot import load_subset, representation, run_cell, run_global, save
from ncm_sudoku.g0 import code_state
from ncm_sudoku.model import ROOT

OUT = ROOT / "experiments" / "e5" / "pilot"
RAW = ROOT / "runs" / "e5" / "pilot"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", nargs="+", required=True)
    ap.add_argument("--readouts", nargs="+", default=["shared", "whole", "global"])
    ap.add_argument("--controls", nargs="+", default=["none"])
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    train, val = load_subset(ROOT, "probe_train"), load_subset(ROOT, "probe_val")
    state = code_state()
    for rep in args.reps:
        cell_rep = not rep.startswith("B")
        r_tr = r_va = None
        for readout in args.readouts:
            if (readout == "global") == cell_rep:
                continue
            for control in args.controls:
                if readout == "global" and control != "none":
                    continue
                stem = f"{rep}__{readout}__{control}"
                if (OUT / f"{stem}.json").exists() and not args.force:
                    print(f"skip {stem}", flush=True)
                    continue
                if r_tr is None:
                    r_tr, r_va = representation(train, rep), representation(val, rep)
                t0 = time.perf_counter()
                if readout == "global":
                    res = run_global(r_tr, r_va, train, val)
                else:
                    res = run_cell(r_tr, r_va, train, val, readout, None if control == "none" else control)
                res.update({"representation": rep, "readout": readout, "control": control,
                            "seconds": round(time.perf_counter() - t0, 1), "code_state": state,
                            "note": "E5 pilot (D100), non-confirmatory; fit on PROBE-TRAIN pairs, scored on PROBE-VAL pairs"})
                save(res, OUT / f"{stem}.json", RAW / f"{stem}.npy")
                w = res["w_auc"]
                print(json.dumps({"stem": stem, "seconds": res["seconds"], "w_auc": w["overall"],
                                  "w_auc_codes_differ": w["codes_differ"], "w_auc_codes_same": w["codes_same"],
                                  "brier": res["summary"]["val_brier_mean"], **res["metrics"]}), flush=True)


if __name__ == "__main__":
    main()
