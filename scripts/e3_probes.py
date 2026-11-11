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
PROBE-VAL puzzle, B_permuted - B_generated at level 6, linear, aligned with the ids; read
by scripts/e3_equiv_power.py) plus the same preview at levels 2 and 12
(h1_diffs_L02.json, h1_diffs_L12.json). Every Brier is the scored value on unpermuted
PROBE-VAL (`val_brier_mean`); the permuted control's tuning value is `tune_brier_mean`.
Refuses to run if probes.json exists, unless --force (start over) or --resume (skip the
stages already in probes.json). --resume exits with an error unless n_train, n_val,
val_ids, the budget overrides and the code state (git commit, dirty flag and diff hash
over src/, scripts/, pyproject.toml, uv.lock) all match the stored run; every stage
records its own environment and code state in `stage_environment`.
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
from ncm_sudoku.g0 import code_state, environment_record
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


def depth_breakdown_seeds(preds: list, mask: np.ndarray, empty: np.ndarray, depth: np.ndarray) -> dict:
    """`depth_breakdown` per seed model, then the mean of the per-seed Briers (the scale of
    every headline Brier: mean over seeds, not the Brier of the seed-averaged prediction)."""
    per = [depth_breakdown(p, mask, empty, depth) for p in preds]
    out = {}
    for c in DEPTH_CLASSES:
        b = [x[c]["brier"] for x in per]
        out[c] = {"brier": None if None in b else float(np.mean(b)), "brier_per_seed": b,
                  "n_cells": per[0][c]["n_cells"], "n_puzzles": per[0][c]["n_puzzles"]}
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


def _seed_models(f_tr, f_va, tr, va, cfg) -> tuple[list, list, int]:
    """Retrains the three seed linear probes at `cfg` (deterministic, identical to the
    grid run) and returns (models, per-seed PROBE-VAL predictions, input width)."""
    Xtr, _, _ = build_inputs(f_tr, tr["empty"])
    Ytr = torch.from_numpy(np.asarray(tr["mask"])[tr["empty"]].astype(np.float32))
    Xva, pz, _ = build_inputs(f_va, va["empty"])
    Yva = torch.from_numpy(np.asarray(va["mask"])[va["empty"]].astype(np.float32))
    models, preds = [], []
    for seed in SEEDS:
        model, _, _ = train_probe(Xtr, Ytr, Xva, Yva, pz.numpy(), len(va["empty"]), "linear", *cfg, seed, **KW)
        with torch.no_grad():
            preds.append(model(Xva).numpy())
        models.append(model)
    return models, preds, int(Xtr.shape[1])


def _h1_level(tr, va, st) -> dict:
    """Level-6 linear probe, its depth breakdown vs. the raw-input linear probe, and the
    selected seed models (retrained deterministically at the selected config)."""
    fit = fit_cells(tr["rep"], va["rep"], tr, va, "linear", **KW)
    MODELS.mkdir(parents=True, exist_ok=True)
    gen_models, gen_preds, in_dim = _seed_models(tr["rep"], va["rep"], tr, va, fit["config"])
    files = []
    for seed, model in zip(SEEDS, gen_models):
        path = MODELS / f"L{H1_LEVEL:02d}_linear_seed{seed}.pt"
        torch.save(model.state_dict(), path)
        files.append(path.name)
    raw_tr, raw_va = raw_features(tr["puzzles"]), raw_features(va["puzzles"])
    raw_cfg = fit_cells(raw_tr, raw_va, tr, va, "linear", **KW)["config"]
    _, raw_preds, _ = _seed_models(raw_tr, raw_va, tr, va, raw_cfg)
    del raw_tr, raw_va
    depth = {
        "aggregation": "per seed model, then mean of the per-seed Briers",
        "generated_linear": depth_breakdown_seeds(gen_preds, va["mask"], va["empty"], va["depth"]),
        "raw_linear": depth_breakdown_seeds(raw_preds, va["mask"], va["empty"], va["depth"]),
    }
    e_va = np.asarray(va["empty"], bool)
    pz, _ = np.nonzero(e_va)
    y_va = np.asarray(va["mask"])[e_va]
    per = [brier_per_puzzle(p, y_va, pz, len(e_va)) for p in gen_preds]
    meta = {
        "level": H1_LEVEL, "kind": "linear", "config": list(fit["config"]), "in_dim": in_dim,
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
    """θ1 preview per level in MLP_LEVELS: per-puzzle B_permuted - B_generated, its mean
    and the relative improvement mean_diff / mean(B_permuted) (D60). The level-6 file
    keeps the name h1_diffs.json (input of scripts/e3_equiv_power.py)."""
    st = results["stages"]
    h1 = {}
    for lv in MLP_LEVELS:
        tag = f"L{lv:02d}"
        perm = st.get("controls", {}).get("permuted_linear") if lv == H1_LEVEL else st.get(f"{tag}_permuted_linear")
        if f"{tag}_linear" not in st or perm is None:
            continue
        diffs = np.subtract(perm["per_puzzle"], st[f"{tag}_linear"]["per_puzzle"])
        name = "h1_diffs.json" if lv == H1_LEVEL else f"h1_diffs_{tag}.json"
        out = {"note": NOTE, "quantity": f"B_permuted - B_generated, level {lv}, linear, mean over 3 seeds",
               "ids": val_ids, "diffs": diffs.tolist()}
        _atomic(OUT / name, json.dumps(out) + "\n")
        mean_diff, mean_perm = float(np.nanmean(diffs)), float(np.nanmean(perm["per_puzzle"]))
        h1[tag] = {"mean_diff": mean_diff, "mean_permuted": mean_perm, "relative_improvement": mean_diff / mean_perm,
                   "n": int(len(diffs)), "path": f"experiments/e3prep/{name}"}
    if h1:
        results["h1"] = h1


def _atomic(path, text: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def _write(results: dict) -> None:
    _atomic(OUT / "probes.json", json.dumps(results, indent=2) + "\n")
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
        "configuration, averaged over seeds 0-2, always scored on unpermuted PROBE-VAL (the permuted "
        "control is tuned on its own permuted PROBE-VAL; that tuning value is `tune_brier_mean` in "
        "probes.json, not shown here); best epoch / steps / hit cap are the training budget "
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
                  "Brier is the mean of the per-seed Briers (same scale as above); exact match and "
                  "ROC-AUC use the seed-averaged predictions (their Brier is `brier_ensemble` in probes.json).", "",
                  "| Input | Exact match | ROC-AUC | Brier | Config | best epoch | steps | any hit cap | n_params |",
                  "|---|---|---|---|---|---|---|---|---|"]
        lines += [f"| {k} | {_fmt(v['exact_match'])} | {_fmt(v['roc_auc'])} | {_fmt(v['brier'])} | {_budget(v)} |"
                  for k, v in st["unit_digit"].items()]
    if "training_size" in st:
        lines += ["", f"## Training-size curve (level {H1_LEVEL}, linear)", "",
                  "The D63 minimum step count gives small-n fits more epochs and hence more early-stopping "
                  "checkpoints on PROBE-VAL (e.g. 1,000 epochs at 125 puzzles vs. 80 at 2,000), a small "
                  "optimistic selection bias at the small-n end of the curve.", "", HEAD]
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
        lines += ["", "## H1 planning quantity (θ1 preview)", ""]
        for tag, h in sorted(results["h1"].items()):
            lines.append(f"- Level {int(tag[1:])}, linear: mean per-puzzle B_permuted − B_generated "
                         f"{_fmt(h['mean_diff'], 5)}, relative improvement (mean diff / mean B_permuted) "
                         f"{_fmt(h['relative_improvement'], 4)}, over {h['n']} PROBE-VAL puzzles ({h['path']})")
    if f"models_L{H1_LEVEL:02d}" in st:
        mm = st[f"models_L{H1_LEVEL:02d}"]
        lines.append(f"- Saved level-{H1_LEVEL} seed models: {', '.join(mm['files'])} at config {mm['config']}; "
                     f"retrain matches the grid fit: {mm['retrain_matches']}")
    lines += ["", "## Stage run times (s)", ""] + [f"- {k}: {v}" for k, v in results["seconds"].items()]
    return "\n".join(lines) + "\n"


def _check_resume(results: dict, current: dict) -> None:
    """Exits unless the stored run matches the current data, budget and code (no override)."""
    bad = [k for k, v in current.items() if results.get(k) != v]
    if bad:
        sys.exit(f"--resume refused: stored probes.json differs from the current run in {bad}; "
                 "rerun from scratch with --force")


def main() -> None:
    resume, force = "--resume" in sys.argv, "--force" in sys.argv
    if resume and force:
        sys.exit("--force and --resume are mutually exclusive")
    guard(force=force or resume)
    torch.use_deterministic_algorithms(True)  # before any environment_record()
    tr0, va0 = _subset("probe_train"), _subset("probe_val")
    path = OUT / "probes.json"
    code = code_state()
    current = {"n_train": len(tr0["ids"]), "n_val": len(va0["ids"]), "val_ids": va0["ids"],
               "budget_overrides": json.loads(json.dumps(KW)), "code": code}
    if resume and path.exists():
        results = json.loads(path.read_text(encoding="utf-8"))
        _check_resume(results, current)
    else:
        results = {"note": NOTE, "date": time.strftime("%Y-%m-%d"), "environment": environment_record(),
                   **current, "stages": {}, "seconds": {}, "stage_environment": {}}
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
            for n in names:
                results["stage_environment"][n] = {"date": time.strftime("%Y-%m-%d"),
                                                   "environment": environment_record(), "code": code}
            _h1_diffs(results, va0["ids"])
            _write(results)
        del train, val  # one level in memory at a time
        gc.collect()


if __name__ == "__main__":
    main()
