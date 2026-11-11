"""E3 probe suite on PROBE-TRAIN/PROBE-VAL (plan v3.6 §8.1-§8.3; D55-D58, D62, D63).
Non-confirmatory planning output.

Usage: uv run python scripts/e3_probes.py [--force | --resume]
Reads runs/e3prep/<probe_train|probe_val>/ (written by scripts/e3_extract.py), one
representation level at a time, and runs:
- levels 1-12: linear generated-branch probe (descriptive curve);
- levels 2, 6, 12: MLP probe and the permuted-representation control (level 6 inside
  `run_controls`, levels 2 and 12 via `permuted_control`);
- level 6: all §8.2 controls and the marginal baseline (`run_controls`), the unit-digit
  target (`run_unit_digit`), the training-size curve (first 125/250/500/1,000/2,000
  PROBE-TRAIN puzzles; the full-size point reuses the level-6 fit), the depth breakdown
  (level-6 linear vs. raw-input linear, Brier per depth class), and the three selected
  level-6 linear seed models (state dicts) saved to runs/e3prep/models/.
Writes experiments/e3prep/probes.json after every stage (atomic), the report
experiments/e3prep/probes_report.md (UTF-8), and experiments/e3prep/h1_diffs.json (per
PROBE-VAL puzzle, B_permuted - B_generated at level 6, linear, aligned with the ids).
Refuses to run if probes.json exists, unless --force (start over) or --resume (skip the
stages already in probes.json).
"""

import gc
import json
import os
import sys
import time

import numpy as np
import torch

from ncm_sudoku.e3controls import fit_cells, permuted_control, run_controls, run_unit_digit, summarize_fit
from ncm_sudoku.e3data import TEACHER_LEVELS, load_level, raw_features
from ncm_sudoku.g0 import environment_record
from ncm_sudoku.labels import CENSORED, STUCK
from ncm_sudoku.model import ROOT
from ncm_sudoku.probes import SEEDS, brier_per_puzzle, build_inputs, train_probe

RUNS = ROOT / "runs" / "e3prep"
OUT = ROOT / "experiments" / "e3prep"
MODELS = RUNS / "models"
LEVELS = range(1, 13)
MLP_LEVELS = (2, 6, 12)
H1_LEVEL = 6
SIZES = (125, 250, 500, 1000, 2000)
KW: dict = {}  # fit_selected/train_probe budget overrides; empty = D55/D63 defaults (tests shrink it)
NOTE = "non-confirmatory planning output (plan v3.6 §12.1); not evidence for H1"
DEPTH_CLASSES = {
    "1": lambda d: d == 1,
    "2": lambda d: d == 2,
    "3": lambda d: d == 3,
    ">=4": lambda d: d >= 4,
    "stuck": lambda d: d == STUCK,
    "censored": lambda d: d == CENSORED,
}


def guard(force: bool) -> None:
    path = OUT / "probes.json"
    if path.exists() and not force:
        sys.exit(f"{path} exists: e3_probes is a rerun-guarded script; use --force or --resume")


def depth_breakdown(preds: np.ndarray, mask: np.ndarray, empty: np.ndarray, depth: np.ndarray) -> dict:
    """Brier per depth class over PROBE-VAL empty cells (rows of `preds` in row-major
    (puzzle, cell) order): per puzzle over its cells of the class, then over the
    puzzles that have such cells (§8.3 aggregation)."""
    empty = np.asarray(empty, bool)
    pz, _ = np.nonzero(empty)
    d, y = np.asarray(depth)[empty], np.asarray(mask)[empty]
    out = {}
    for name, rule in DEPTH_CLASSES.items():
        sel = rule(d)
        pb = brier_per_puzzle(np.asarray(preds)[sel], y[sel], pz[sel], len(empty))
        n_cells = int(sel.sum())
        out[name] = {
            "brier": float(np.nanmean(pb)) if n_cells else None,
            "n_cells": n_cells,
            "n_puzzles": int(len(np.unique(pz[sel]))),
        }
    return out


def _subset(name: str) -> dict:
    d = RUNS / name
    return {
        "ids": json.loads((d / "ids.json").read_text(encoding="utf-8")),
        **{k: np.load(d / f"{k}.npy") for k in ("puzzles", "mask", "empty", "depth")},
    }


def _probe(kind: str, tag: str):
    return lambda tr, va, st: {f"{tag}_{kind}": summarize_fit(fit_cells(tr["rep"], va["rep"], tr, va, kind, **KW))}


def _permuted(tag: str):
    return lambda tr, va, st: {f"{tag}_permuted_linear": summarize_fit(permuted_control(tr["rep"], va["rep"], tr, va, **KW))}


def _h1_level(tr, va, st) -> dict:
    """Level-6 linear probe, its depth breakdown vs. the raw-input linear probe, and the
    selected seed models (retrained deterministically at the selected config)."""
    fit = fit_cells(tr["rep"], va["rep"], tr, va, "linear", **KW)
    raw = fit_cells(raw_features(tr["puzzles"]), raw_features(va["puzzles"]), tr, va, "linear", **KW)
    depth = {
        "generated_linear": depth_breakdown(fit["preds"], va["mask"], va["empty"], va["depth"]),
        "raw_linear": depth_breakdown(raw["preds"], va["mask"], va["empty"], va["depth"]),
    }
    del raw

    wd, lr = fit["config"]
    Xtr, _, _ = build_inputs(tr["rep"], tr["empty"])
    Ytr = torch.from_numpy(np.asarray(tr["mask"])[tr["empty"]].astype(np.float32))
    Xva, pz, _ = build_inputs(va["rep"], va["empty"])
    Yva = torch.from_numpy(np.asarray(va["mask"])[va["empty"]].astype(np.float32))
    n_va = len(va["empty"])
    MODELS.mkdir(parents=True, exist_ok=True)
    files, per = [], []
    for seed in SEEDS:
        model, _, _ = train_probe(Xtr, Ytr, Xva, Yva, pz.numpy(), n_va, "linear", wd, lr, seed, **KW)
        path = MODELS / f"L{H1_LEVEL:02d}_linear_seed{seed}.pt"
        torch.save(model.state_dict(), path)
        files.append(path.name)
        with torch.no_grad():
            per.append(brier_per_puzzle(model(Xva).numpy(), Yva.numpy(), pz.numpy(), n_va))
    meta = {
        "level": H1_LEVEL, "kind": "linear", "config": [wd, lr], "in_dim": int(Xtr.shape[1]),
        "seeds": list(SEEDS), "files": files,
        "retrain_matches": bool(np.allclose(np.mean(per, axis=0), fit["per_puzzle"], equal_nan=True)),
    }
    (MODELS / f"L{H1_LEVEL:02d}_linear.json").write_text(json.dumps(meta, indent=2) + "\n", newline="\n")
    return {f"L{H1_LEVEL:02d}_linear": summarize_fit(fit), f"depth_L{H1_LEVEL:02d}": depth, f"models_L{H1_LEVEL:02d}": meta}


def _training_size(tr, va, st) -> dict:
    """Level-6 linear probe on the first n PROBE-TRAIN puzzles, same selection rule."""
    n_train = len(tr["puzzles"])
    out = {}
    for n in SIZES:
        if n >= n_train:  # identical to the full-size level-6 fit (deterministic): reuse it
            out[str(n)] = {**st[f"L{H1_LEVEL:02d}_linear"], "n_puzzles": n_train, "reused": True}
            continue
        sub = {k: tr[k][:n] for k in ("puzzles", "mask", "empty")}
        out[str(n)] = {**summarize_fit(fit_cells(tr["rep"][:n], va["rep"], sub, va, "linear", **KW)),
                       "n_puzzles": n, "reused": False}
    return {"training_size": out}


def _jobs(lv: int) -> list:
    """(stage names, fn(train, val, stages) -> {name: result}) for one level."""
    tag = f"L{lv:02d}"
    if lv == H1_LEVEL:
        jobs = [((f"{tag}_linear", f"depth_{tag}", f"models_{tag}"), _h1_level)]
    else:
        jobs = [((f"{tag}_linear",), _probe("linear", tag))]
    if lv in MLP_LEVELS:
        jobs.append(((f"{tag}_mlp",), _probe("mlp", tag)))
    if lv == H1_LEVEL:
        jobs += [
            (("controls",), lambda tr, va, st: {"controls": run_controls(tr, va, **KW)}),
            (("unit_digit",), lambda tr, va, st: {"unit_digit": run_unit_digit(tr, va, **KW)}),
            (("training_size",), _training_size),
        ]
    elif lv in MLP_LEVELS:
        jobs.append(((f"{tag}_permuted_linear",), _permuted(tag)))
    return jobs


def _h1_diffs(results: dict, val_ids: list) -> None:
    st = results["stages"]
    if f"L{H1_LEVEL:02d}_linear" not in st or "controls" not in st:
        return
    diffs = np.subtract(st["controls"]["permuted_linear"]["per_puzzle"], st[f"L{H1_LEVEL:02d}_linear"]["per_puzzle"])
    out = {"note": NOTE, "quantity": "B_permuted - B_generated, level 6, linear, mean over 3 seeds",
           "ids": val_ids, "diffs": diffs.tolist()}
    (OUT / "h1_diffs.json").write_text(json.dumps(out) + "\n", newline="\n")
    results["h1"] = {"mean_diff": float(np.nanmean(diffs)), "n": int(len(diffs)), "path": "experiments/e3prep/h1_diffs.json"}


def _write(results: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / "probes.tmp"
    tmp.write_text(json.dumps(results, indent=2) + "\n", newline="\n")
    os.replace(tmp, OUT / "probes.json")
    (OUT / "probes_report.md").write_text(report(results), encoding="utf-8", newline="\n")


def _fmt(v, nd: int = 4) -> str:
    return "–" if v is None else f"{v:.{nd}f}"


def _budget(s: dict) -> str:
    """config | best epoch min–max | steps | any hit cap | n_params."""
    b = s.get("budget")
    if not b:
        return "– | – | – | – | –"
    best = [x["best_epoch"] for x in b["selected"]]
    steps = sorted({x["n_steps"] for x in b["selected"]})
    return (f"{s['config']} | {min(best)}–{max(best)} | {'/'.join(map(str, steps))} | "
            f"{b['any_hit_cap']} | {b['n_params']}")


HEAD = "| Probe | Val Brier | Config | best epoch | steps | any hit cap | n_params |\n|---|---|---|---|---|---|---|"


def report(results: dict) -> str:
    st = results["stages"]
    row = lambda name, s: f"| {name} | {_fmt(s['val_brier_mean'])} | {_budget(s)} |"  # noqa: E731
    lines = [
        "# E3 probe-suite report",
        "",
        "**Non-confirmatory planning output (plan v3.6 §12.1).** PROBE-TRAIN/PROBE-VAL only; "
        "these numbers plan the confirmatory E3 study and are not evidence for H1.",
        "",
        f"- PROBE-TRAIN {results['n_train']} puzzles, PROBE-VAL {results['n_val']} puzzles",
        "- Val Brier: per-puzzle mean over empty cells, then over puzzles (§8.3), at the selected "
        "configuration, averaged over seeds 0-2; best epoch / steps / hit cap are the training budget "
        "of the selected configuration's seeds (D63; hit cap is over the whole grid)",
        "",
        "## Representation levels (generated branch)",
        "",
        HEAD,
    ]
    lines += [row(k, v) for k, v in sorted(st.items()) if k[0] == "L" and isinstance(v, dict) and "val_brier_mean" in v]
    if "controls" in st:
        lines += ["", f"## Controls (level {H1_LEVEL})", "", HEAD]
        lines += [row(k, v) for k, v in st["controls"].items()]
    if "unit_digit" in st:
        lines += ["", f"## Unit-digit target (level {H1_LEVEL}, linear; D62)", "",
                  "| Input | Exact match | ROC-AUC | Brier | Config | best epoch | steps | any hit cap | n_params |",
                  "|---|---|---|---|---|---|---|---|---|"]
        lines += [f"| {k} | {_fmt(v['exact_match'])} | {_fmt(v['roc_auc'])} | {_fmt(v['brier'])} | {_budget(v)} |"
                  for k, v in st["unit_digit"].items()]
    if "training_size" in st:
        lines += ["", f"## Training-size curve (level {H1_LEVEL}, linear)", "", HEAD]
        lines += [row(f"first {v['n_puzzles']} puzzles" + (" (reused)" if v["reused"] else ""), v)
                  for v in st["training_size"].values()]
    if f"depth_L{H1_LEVEL:02d}" in st:
        d = st[f"depth_L{H1_LEVEL:02d}"]
        lines += ["", f"## Depth breakdown (level {H1_LEVEL} linear vs. raw-input linear; Brier per class)", "",
                  "| Depth | Generated | Raw input | cells | puzzles |", "|---|---|---|---|---|"]
        for c in DEPTH_CLASSES:
            g, r = d["generated_linear"][c], d["raw_linear"][c]
            lines.append(f"| {c} | {_fmt(g['brier'])} | {_fmt(r['brier'])} | {g['n_cells']} | {g['n_puzzles']} |")
    if "h1" in results:
        h = results["h1"]
        lines += ["", "## H1 planning quantity", "",
                  f"- Mean per-puzzle B_permuted − B_generated (level {H1_LEVEL}, linear): "
                  f"{_fmt(h['mean_diff'], 5)} over {h['n']} PROBE-VAL puzzles ({h['path']})"]
    if f"models_L{H1_LEVEL:02d}" in st:
        mm = st[f"models_L{H1_LEVEL:02d}"]
        lines.append(f"- Saved level-{H1_LEVEL} seed models: {', '.join(mm['files'])} at config {mm['config']}; "
                     f"retrain matches the grid fit: {mm['retrain_matches']}")
    lines += ["", "## Stage run times (s)", ""] + [f"- {k}: {v}" for k, v in results["seconds"].items()]
    return "\n".join(lines) + "\n"


def main() -> None:
    resume = "--resume" in sys.argv
    guard(force="--force" in sys.argv or resume)
    tr0, va0 = _subset("probe_train"), _subset("probe_val")
    path = OUT / "probes.json"
    if resume and path.exists():
        results = json.loads(path.read_text(encoding="utf-8"))
    else:
        results = {"note": NOTE, "date": time.strftime("%Y-%m-%d"), "environment": environment_record(),
                   "n_train": len(tr0["ids"]), "n_val": len(va0["ids"]), "val_ids": va0["ids"],
                   "budget_overrides": KW, "stages": {}, "seconds": {}}
    st = results["stages"]
    for lv in LEVELS:
        jobs = [(names, fn) for names, fn in _jobs(lv) if not all(n in st for n in names)]
        if not jobs:
            continue
        train = {**tr0, "rep": load_level(RUNS, "probe_train", lv)}
        val = {**va0, "rep": load_level(RUNS, "probe_val", lv)}
        if lv == H1_LEVEL:
            train["teacher"] = {t: load_level(RUNS, "probe_train", t, teacher=True) for t in TEACHER_LEVELS}
            val["teacher"] = {t: load_level(RUNS, "probe_val", t, teacher=True) for t in TEACHER_LEVELS}
        for names, fn in jobs:
            t0 = time.perf_counter()
            st.update(fn(train, val, st))
            results["seconds"][names[0]] = round(time.perf_counter() - t0, 1)
            _h1_diffs(results, va0["ids"])
            _write(results)
        del train, val  # one level in memory at a time
        gc.collect()


if __name__ == "__main__":
    main()
