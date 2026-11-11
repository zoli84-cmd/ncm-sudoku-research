"""Whole-layer E3 diagnostic on PROBE-TRAIN/PROBE-VAL (plan v3.6 §8.1-§8.3; D55, D63, D65).
Non-confirmatory planning output.

Usage: uv run python scripts/e3_wholelayer.py [--force]
Reads runs/e3prep/<probe_train|probe_val>/ (written by scripts/e3_extract.py), one
representation level at a time, and runs shared linear probes (D55 grid, D63 budget)
on whole-layer per-cell inputs (`ncm_sudoku.wholelayer`; PCA-K fitted on PROBE-TRAIN
only, K = 256):
- levels 6 and 12 (stages "L06", "L12"): generated-branch whole-layer probe
  [PCA-K of the flattened 81-cell grid state || own cell state || position] and the
  permuted-representation control on the same features (whole grids permuted, tuned on
  permuted PROBE-VAL, scored on unpermuted PROBE-VAL); θ1 preview per PROBE-VAL puzzle
  (B_permuted - B_generated) to experiments/e3prep/wholelayer_h1_diffs_L06.json /
  _L12.json (ids-aligned);
- "teacher_L12": the same construction from the level-12 teacher states with its own
  PCA, and the per-puzzle D65 secondary contrast preview B_teacher - B_generated;
- "raw_projected" / "raw_unprojected": raw-input control [810-d puzzle one-hot, PCA-K
  projected or unprojected || own one-hot (10) || position] (§8.1 requires both).
Writes experiments/e3prep/wholelayer.json after every stage (atomic) and the UTF-8
report experiments/e3prep/wholelayer_report.md. Every Brier is the scored value on
unpermuted PROBE-VAL (`val_brier_mean`). Refuses to run if wholelayer.json exists,
unless --force.
"""

import gc
import json
import os
import sys
import time

import numpy as np
import torch

from ncm_sudoku.e3controls import fit_cells, permuted_control, summarize_fit
from ncm_sudoku.e3data import load_level
from ncm_sudoku.g0 import code_state, environment_record
from ncm_sudoku.model import ROOT
from ncm_sudoku.wholelayer import fit_pca, raw_whole, raw_whole_features, whole_layer_features

RUNS = ROOT / "runs" / "e3prep"
OUT = ROOT / "experiments" / "e3prep"
K = 256
LEVELS = (6, 12)
KW: dict = {}  # fit_selected budget overrides; empty = D55/D63 defaults (tests shrink it)
NOTE = "non-confirmatory planning output (plan v3.6 §12.1); not evidence for H1"


def guard(force: bool) -> None:
    path = OUT / "wholelayer.json"
    if path.exists() and not force:
        sys.exit(f"{path} exists: e3_wholelayer is a rerun-guarded script; use --force")


def _subset(name: str) -> dict:
    d = RUNS / name
    return {
        "ids": json.loads((d / "ids.json").read_text(encoding="utf-8")),
        **{k: np.load(d / f"{k}.npy") for k in ("puzzles", "mask", "empty")},
    }


def _atomic(path, text: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def _pca_info(pca: dict, dim: int) -> dict:
    return {"k": K, "input_dim": int(dim), "n_components_fitted": pca["n_components_fitted"],
            "explained_variance_share": pca["explained_variance_share"]}


def _diff(a: list, b: list, ids: list, quantity: str) -> dict:
    """Per-puzzle a - b, its mean, and the relative improvement mean_diff / mean(a)."""
    diffs = np.subtract(a, b)
    mean_a = float(np.nanmean(a))
    return {"quantity": quantity, "mean_diff": float(np.nanmean(diffs)), "mean_reference": mean_a,
            "relative_improvement": float(np.nanmean(diffs)) / mean_a, "n": int(len(diffs)),
            "ids": ids, "diffs": diffs.tolist()}


def _whole_layer(teacher: bool, lv: int) -> tuple[dict, np.ndarray, np.ndarray]:
    """Loads one level, fits its PCA on PROBE-TRAIN and returns (pca info, train, val features)."""
    s_tr = load_level(RUNS, "probe_train", lv, teacher=teacher)
    s_va = load_level(RUNS, "probe_val", lv, teacher=teacher)
    pca = fit_pca(np.asarray(s_tr, np.float32).reshape(len(s_tr), -1), K)
    f_tr, f_va = whole_layer_features(s_tr, pca), whole_layer_features(s_va, pca)
    info = _pca_info(pca, s_tr.shape[1] * s_tr.shape[2])
    del s_tr, s_va, pca
    return info, f_tr, f_va


def _level(lv: int):
    def run(tr, va, st) -> dict:
        tag = f"L{lv:02d}"
        info, f_tr, f_va = _whole_layer(False, lv)
        gen = summarize_fit(fit_cells(f_tr, f_va, tr, va, "linear", **KW))
        perm = summarize_fit(permuted_control(f_tr, f_va, tr, va, **KW))
        del f_tr, f_va
        d = _diff(perm["per_puzzle"], gen["per_puzzle"], va["ids"],
                  f"B_permuted - B_generated, whole-layer, level {lv}, linear, mean over 3 seeds")
        path = OUT / f"wholelayer_h1_diffs_{tag}.json"
        _atomic(path, json.dumps({"note": NOTE, "quantity": d["quantity"], "ids": d["ids"], "diffs": d["diffs"]}) + "\n")
        h1 = {k: d[k] for k in ("mean_diff", "relative_improvement", "n")}
        h1.update(mean_permuted=d["mean_reference"], path=f"experiments/e3prep/{path.name}")
        return {"pca": info, "generated_linear": gen, "permuted_linear": perm, "h1": h1}
    return run


def _teacher(tr, va, st) -> dict:
    info, f_tr, f_va = _whole_layer(True, 12)
    t = summarize_fit(fit_cells(f_tr, f_va, tr, va, "linear", **KW))
    del f_tr, f_va
    d = _diff(t["per_puzzle"], st["L12"]["generated_linear"]["per_puzzle"], va["ids"],
              "B_teacher - B_generated, whole-layer, level 12, linear, mean over 3 seeds")
    d.pop("relative_improvement")
    d["mean_teacher"] = d.pop("mean_reference")
    return {"pca": info, "teacher_linear": t, "teacher_minus_generated": d}


def _raw(projected: bool):
    def run(tr, va, st) -> dict:
        out = {}
        pca = None
        if projected:
            pca = fit_pca(raw_whole(tr["puzzles"]), K)
            out["pca"] = _pca_info(pca, 810)
        f_tr, f_va = raw_whole_features(tr["puzzles"], pca), raw_whole_features(va["puzzles"], pca)
        out["linear"] = summarize_fit(fit_cells(f_tr, f_va, tr, va, "linear", **KW))
        return out
    return run


STAGES = [("L06", _level(6)), ("L12", _level(12)), ("teacher_L12", _teacher),
          ("raw_projected", _raw(True)), ("raw_unprojected", _raw(False))]


def _fmt(v, nd: int = 4) -> str:
    return "–" if v is None else f"{v:.{nd}f}"


def _budget(s: dict) -> str:
    """config | best epoch min–max | steps | any hit cap | n_params."""
    b = s["budget"]
    best = [x["best_epoch"] for x in b["selected"]]
    steps = sorted({x["n_steps"] for x in b["selected"]})
    return (f"{s['config']} | {min(best)}–{max(best)} | {'/'.join(map(str, steps))} | "
            f"{b['any_hit_cap']} | {b['n_params']}")


def report(results: dict) -> str:
    st = results["stages"]
    row = lambda name, s: f"| {name} | {_fmt(s['val_brier_mean'])} | {_budget(s)} |"  # noqa: E731
    lines = [
        "# E3 whole-layer diagnostic report (D65)",
        "",
        "**Non-confirmatory planning output (plan v3.6 §12.1).** PROBE-TRAIN/PROBE-VAL only; "
        "this diagnostic informs the form of H1 (D65) and is not evidence for H1.",
        "",
        f"- PROBE-TRAIN {results['n_train']} puzzles, PROBE-VAL {results['n_val']} puzzles",
        f"- Whole-layer input per cell: PCA-{results['k']} projection of the flattened 81-cell grid state "
        "(fitted on PROBE-TRAIN only, same vector for every cell) || the cell's own state || position one-hot; "
        "raw-input control: 810-d puzzle one-hot, projected (PCA) and unprojected, || own one-hot || position",
        "- Val Brier: per-puzzle mean over empty cells, then over puzzles (§8.3), at the selected configuration "
        "(D55 grid, D63 budget), averaged over seeds 0-2, always scored on unpermuted PROBE-VAL (the permuted "
        "control's tuning value is `tune_brier_mean` in wholelayer.json)",
        "",
        "| Probe | Val Brier | Config | best epoch | steps | any hit cap | n_params |",
        "|---|---|---|---|---|---|---|",
    ]
    names = {"generated_linear": "generated", "permuted_linear": "permuted control", "teacher_linear": "teacher"}
    for tag in ("L06", "L12", "teacher_L12"):
        for key, label in names.items():
            if key in st.get(tag, {}):
                lines.append(row(f"{tag} whole-layer {label}", st[tag][key]))
    for tag, label in (("raw_projected", "raw input, projected"), ("raw_unprojected", "raw input, unprojected")):
        if tag in st:
            lines.append(row(label, st[tag]["linear"]))
    lines += ["", "## PCA explained-variance share (top-k, PROBE-TRAIN)", ""]
    for tag in ("L06", "L12", "teacher_L12", "raw_projected"):
        if tag in st:
            p = st[tag]["pca"]
            lines.append(f"- {tag}: {_fmt(p['explained_variance_share'])} of {p['input_dim']} dimensions "
                         f"({p['n_components_fitted']} components fitted)")
    h1 = [(t, st[t]["h1"]) for t in ("L06", "L12") if t in st]
    if h1:
        lines += ["", "## H1 planning quantity (θ1 preview, whole-layer)", ""]
        for tag, h in h1:
            lines.append(f"- Level {int(tag[1:])}, linear: mean per-puzzle B_permuted − B_generated "
                         f"{_fmt(h['mean_diff'], 5)}, relative improvement (mean diff / mean B_permuted) "
                         f"{_fmt(h['relative_improvement'], 4)}, over {h['n']} PROBE-VAL puzzles ({h['path']})")
    if "teacher_L12" in st:
        t = st["teacher_L12"]["teacher_minus_generated"]
        lines += ["", "## Secondary contrast preview (level 12, D65)", "",
                  f"- Mean per-puzzle B_teacher − B_generated {_fmt(t['mean_diff'], 5)} over {t['n']} PROBE-VAL "
                  "puzzles (per-puzzle values in wholelayer.json)"]
    lines += ["", "## Stage run times (s)", ""] + [f"- {k}: {v}" for k, v in results["seconds"].items()]
    return "\n".join(lines) + "\n"


def _write(results: dict) -> None:
    _atomic(OUT / "wholelayer.json", json.dumps(results, indent=2) + "\n")
    (OUT / "wholelayer_report.md").write_text(report(results), encoding="utf-8", newline="\n")


def main() -> None:
    guard(force="--force" in sys.argv)
    torch.use_deterministic_algorithms(True)  # before any environment_record()
    tr, va = _subset("probe_train"), _subset("probe_val")
    results = {"note": NOTE, "date": time.strftime("%Y-%m-%d"), "environment": environment_record(),
               "code": code_state(), "n_train": len(tr["ids"]), "n_val": len(va["ids"]), "val_ids": va["ids"],
               "k": K, "budget_overrides": json.loads(json.dumps(KW)), "stages": {}, "seconds": {}}
    for name, fn in STAGES:
        t0 = time.perf_counter()
        results["stages"][name] = fn(tr, va, results["stages"])
        results["seconds"][name] = round(time.perf_counter() - t0, 1)
        _write(results)
        gc.collect()  # one level's features in memory at a time


if __name__ == "__main__":
    main()
