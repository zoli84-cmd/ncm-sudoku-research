"""Cell-relative whole-layer E3 diagnostic on PROBE-TRAIN/PROBE-VAL (plan v3.6 §8.1-§8.3;
D55, D63, D65, D66). Non-confirmatory planning output.

Usage: uv run python scripts/e3_wholelayer.py [--force | --resume]
Reads runs/e3prep/<probe_train|probe_val>/ (written by scripts/e3_extract.py), one
representation level at a time, and runs shared linear probes (D55 grid, D63 budget).
Per-cell input (`ncm_sudoku.wholelayer`, D66): whitened PCA-K scores (K = 256) of the
states of the cell and its 20 peers (PCA fitted on PROBE-TRAIN empty-cell rows only) ||
the cell's own state || position one-hot. Stages:
- "L06", "L12": generated-branch probe and the permuted-representation control on the
  same features (whole grids permuted, tuned on permuted PROBE-VAL, scored on
  unpermuted PROBE-VAL); θ1 preview per PROBE-VAL puzzle (B_permuted - B_generated) to
  experiments/e3prep/wholelayer_h1_diffs_L06.json / _L12.json (ids-aligned);
- "teacher_L12": the same construction from the level-12 teacher states with its own
  PCA, and the per-puzzle D65 secondary contrast preview B_teacher - B_generated;
- "raw_projected" / "raw_unprojected": raw-input control, whitened PCA of
  `e3data.raw_features` (own || 20 peer one-hots, 210-d; k = min(K, 210, rows)) or
  `raw_features` as is, || position (§8.1 requires both).
Reference rows (per-cell L06/L12 linear and permuted, surface, raw linear) are read
from experiments/e3prep/probes.json if present ("n/a" otherwise), with whole-layer
minus per-cell scored Brier at levels 6 and 12.
Writes experiments/e3prep/wholelayer.json and the UTF-8 report wholelayer_report.md
after every stage (both atomic). Every Brier is the scored value on unpermuted
PROBE-VAL (`val_brier_mean`). Refuses to run if wholelayer.json exists, unless --force
(start over) or --resume (skip stages already stored; exits unless n_train, n_val,
val_ids, k, the budget overrides and the code state match the stored run).
"""

import gc
import json
import os
import sys
import time

import numpy as np
import torch

from ncm_sudoku.e3controls import fit_cells, permuted_control, summarize_fit
from ncm_sudoku.e3data import load_level, raw_features
from ncm_sudoku.g0 import code_state, environment_record
from ncm_sudoku.model import ROOT
from ncm_sudoku.wholelayer import (
    cell_variance_share,
    fit_cell_pca,
    fit_pca,
    raw_projected_features,
    variance_share,
    whole_layer_features,
)

RUNS = ROOT / "runs" / "e3prep"
OUT = ROOT / "experiments" / "e3prep"
K = 256
KW: dict = {}  # fit_selected budget overrides; empty = D55/D63 defaults (tests shrink it)
NOTE = "non-confirmatory planning output (plan v3.6 §12.1); not evidence for H1"
# reference row -> path in probes.json["stages"]
REFERENCES = {
    "L06_linear": ("L06_linear",),
    "L12_linear": ("L12_linear",),
    "L06_permuted_linear": ("controls", "permuted_linear"),
    "L12_permuted_linear": ("L12_permuted_linear",),
    "surface_linear": ("controls", "surface_linear"),
    "raw_linear": ("controls", "raw_linear"),
}


def guard(force: bool) -> None:
    path = OUT / "wholelayer.json"
    if path.exists() and not force:
        sys.exit(f"{path} exists: e3_wholelayer is a rerun-guarded script; use --force or --resume")


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


def _pca_info(pca: dict, dim: int, share_val: float) -> dict:
    return {"k": int(pca["components"].shape[0]), "input_dim": int(dim), "n_rows": pca["n_rows"],
            "n_components_fitted": pca["n_components_fitted"],
            "explained_variance_share": pca["explained_variance_share"], "explained_variance_share_val": share_val}


def _diff(a: list, b: list, ids: list, quantity: str) -> dict:
    """Per-puzzle a - b, its mean, and the relative improvement mean_diff / mean(a)
    (None when mean(a) is 0)."""
    diffs = np.subtract(a, b)
    mean_a, mean_d = float(np.nanmean(a)), float(np.nanmean(diffs))
    return {"quantity": quantity, "mean_diff": mean_d, "mean_reference": mean_a,
            "relative_improvement": mean_d / mean_a if mean_a != 0 else None, "n": int(len(diffs)),
            "ids": ids, "diffs": diffs.tolist()}


def _whole_layer(tr, va, teacher: bool, lv: int) -> tuple[dict, np.ndarray, np.ndarray]:
    """Loads one level, fits its peer-state PCA on PROBE-TRAIN empty cells and returns
    (pca info, train features, val features)."""
    s_tr = load_level(RUNS, "probe_train", lv, teacher=teacher)
    s_va = load_level(RUNS, "probe_val", lv, teacher=teacher)
    pca = fit_cell_pca(s_tr, tr["empty"], K)
    info = _pca_info(pca, 21 * s_tr.shape[2], cell_variance_share(s_va, va["empty"], pca))
    f_tr, f_va = whole_layer_features(s_tr, pca), whole_layer_features(s_va, pca)
    del s_tr, s_va, pca
    return info, f_tr, f_va


def _level(lv: int):
    def run(tr, va, st) -> dict:
        tag = f"L{lv:02d}"
        info, f_tr, f_va = _whole_layer(tr, va, False, lv)
        gen = summarize_fit(fit_cells(f_tr, f_va, tr, va, "linear", **KW))
        perm = summarize_fit(permuted_control(f_tr, f_va, tr, va, **KW))
        del f_tr, f_va
        d = _diff(perm["per_puzzle"], gen["per_puzzle"], va["ids"],
                  f"B_permuted - B_generated, whole-layer (D66), level {lv}, linear, mean over 3 seeds")
        path = OUT / f"wholelayer_h1_diffs_{tag}.json"
        _atomic(path, json.dumps({"note": NOTE, "quantity": d["quantity"], "ids": d["ids"], "diffs": d["diffs"]}) + "\n")
        h1 = {k: d[k] for k in ("mean_diff", "relative_improvement", "n")}
        h1.update(mean_permuted=d["mean_reference"], path=f"experiments/e3prep/{path.name}")
        return {"pca": info, "generated_linear": gen, "permuted_linear": perm, "h1": h1}
    return run


def _teacher(tr, va, st) -> dict:
    info, f_tr, f_va = _whole_layer(tr, va, True, 12)
    t = summarize_fit(fit_cells(f_tr, f_va, tr, va, "linear", **KW))
    del f_tr, f_va
    d = _diff(t["per_puzzle"], st["L12"]["generated_linear"]["per_puzzle"], va["ids"],
              "B_teacher - B_generated, whole-layer (D66), level 12, linear, mean over 3 seeds")
    d.pop("relative_improvement")
    d["mean_teacher"] = d.pop("mean_reference")
    return {"pca": info, "teacher_linear": t, "teacher_minus_generated": d}


def _raw_projected(tr, va, st) -> dict:
    rows_tr = raw_features(tr["puzzles"])[tr["empty"]]
    pca = fit_pca(rows_tr, min(K, *rows_tr.shape))
    info = _pca_info(pca, rows_tr.shape[1], variance_share(raw_features(va["puzzles"])[va["empty"]], pca))
    f_tr, f_va = raw_projected_features(tr["puzzles"], pca), raw_projected_features(va["puzzles"], pca)
    return {"pca": info, "linear": summarize_fit(fit_cells(f_tr, f_va, tr, va, "linear", **KW))}


def _raw_unprojected(tr, va, st) -> dict:
    f_tr, f_va = raw_features(tr["puzzles"]), raw_features(va["puzzles"])
    return {"linear": summarize_fit(fit_cells(f_tr, f_va, tr, va, "linear", **KW))}


STAGES = [("L06", _level(6)), ("L12", _level(12)), ("teacher_L12", _teacher),
          ("raw_projected", _raw_projected), ("raw_unprojected", _raw_unprojected)]


def _load_references(val_ids: list) -> dict:
    """Scored per-cell reference Briers from probes.json (None if missing)."""
    path = OUT / "probes.json"
    if not path.exists():
        return {"available": False, "val_ids_match": None, "rows": {k: None for k in REFERENCES}}
    p = json.loads(path.read_text(encoding="utf-8"))
    rows = {}
    for name, keys in REFERENCES.items():
        node = p.get("stages", {})
        for key in keys:
            node = node.get(key, {}) if isinstance(node, dict) else {}
        rows[name] = node.get("val_brier_mean") if isinstance(node, dict) else None
    return {"available": True, "val_ids_match": p.get("val_ids") == val_ids, "rows": rows,
            "path": "experiments/e3prep/probes.json"}


def _compare(results: dict) -> None:
    """Whole-layer minus per-cell scored Brier at levels 6 and 12 (None if unavailable)."""
    st, rows = results["stages"], results["references"]["rows"]
    results["whole_minus_per_cell"] = {
        tag: (st[tag]["generated_linear"]["val_brier_mean"] - rows[f"{tag}_linear"]
              if tag in st and rows.get(f"{tag}_linear") is not None else None)
        for tag in ("L06", "L12")
    }


def _fmt(v, nd: int = 4) -> str:
    return "n/a" if v is None else f"{v:.{nd}f}"


def _budget(s: dict) -> str:
    """config | best epoch min–max | steps | any hit cap | n_params."""
    b = s["budget"]
    best = [x["best_epoch"] for x in b["selected"]]
    steps = sorted({x["n_steps"] for x in b["selected"]})
    return (f"{s['config']} | {min(best)}–{max(best)} | {'/'.join(map(str, steps))} | "
            f"{b['any_hit_cap']} | {b['n_params']}")


def report(results: dict) -> str:
    st, ref = results["stages"], results["references"]
    row = lambda name, s: f"| {name} | {_fmt(s['val_brier_mean'])} | {_budget(s)} |"  # noqa: E731
    lines = [
        "# E3 whole-layer diagnostic report (D65, D66)",
        "",
        "**Non-confirmatory planning output (plan v3.6 §12.1).** PROBE-TRAIN/PROBE-VAL only; "
        "this diagnostic informs the form of H1 (D65) and is not evidence for H1.",
        "",
        f"- PROBE-TRAIN {results['n_train']} puzzles, PROBE-VAL {results['n_val']} puzzles",
        f"- Whole-layer input per cell (D66): whitened PCA-{results['k']} scores of the states of the cell and its "
        "20 peers (PCA fitted on PROBE-TRAIN empty-cell rows only) || the cell's own state || position one-hot; "
        "raw-input control: `raw_features` (own || 20 peer one-hots), whitened-PCA projected and unprojected, "
        "|| position",
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
    src = "experiments/e3prep/probes.json" if ref["available"] else "probes.json not found"
    lines += ["", f"## Per-cell reference rows (scored val Brier, read from {src})", ""]
    if ref["available"] and not ref["val_ids_match"]:
        lines.append("- Warning: probes.json was run on different PROBE-VAL ids; references are not comparable")
    lines += [f"- per-cell {k}: {_fmt(v)}" for k, v in ref["rows"].items()]
    lines += [f"- whole-layer minus per-cell, {tag} linear: {_fmt(v, 5)}"
              for tag, v in results["whole_minus_per_cell"].items()]
    lines += ["", "## PCA explained-variance share (top-k; train in-sample, val with the train mean)", ""]
    for tag in ("L06", "L12", "teacher_L12", "raw_projected"):
        if tag in st:
            p = st[tag]["pca"]
            lines.append(f"- {tag}: train {_fmt(p['explained_variance_share'])}, val "
                         f"{_fmt(p['explained_variance_share_val'])}; k = {p['k']} of {p['input_dim']} dimensions, "
                         f"{p['n_rows']} train rows")
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
    _compare(results)
    _atomic(OUT / "wholelayer.json", json.dumps(results, indent=2) + "\n")
    _atomic(OUT / "wholelayer_report.md", report(results))


def _check_resume(results: dict, current: dict) -> None:
    """Exits unless the stored run matches the current data, budget and code (no override)."""
    bad = [k for k, v in current.items() if results.get(k) != v]
    if bad:
        sys.exit(f"--resume refused: stored wholelayer.json differs from the current run in {bad}; "
                 "rerun from scratch with --force")


def main() -> None:
    resume, force = "--resume" in sys.argv, "--force" in sys.argv
    if resume and force:
        sys.exit("--force and --resume are mutually exclusive")
    guard(force=force or resume)
    torch.use_deterministic_algorithms(True)  # before any environment_record()
    tr, va = _subset("probe_train"), _subset("probe_val")
    path = OUT / "wholelayer.json"
    current = {"n_train": len(tr["ids"]), "n_val": len(va["ids"]), "val_ids": va["ids"], "k": K,
               "budget_overrides": json.loads(json.dumps(KW)), "code": code_state()}
    if resume and path.exists():
        results = json.loads(path.read_text(encoding="utf-8"))
        _check_resume(results, current)
    else:
        results = {"note": NOTE, "date": time.strftime("%Y-%m-%d"), "environment": environment_record(),
                   **current, "stages": {}, "seconds": {}}
    results["references"] = _load_references(va["ids"])
    for name, fn in STAGES:
        if name in results["stages"]:
            continue
        t0 = time.perf_counter()
        results["stages"][name] = fn(tr, va, results["stages"])
        results["seconds"][name] = round(time.perf_counter() - t0, 1)
        _write(results)
        gc.collect()  # one level's features in memory at a time
    _write(results)


if __name__ == "__main__":
    main()
