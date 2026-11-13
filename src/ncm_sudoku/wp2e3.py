"""Confirmatory E3 stage definitions for WP2 (plan v3.7 §8.1-§8.3; D64, D67, D76-D78;
spec ambiguities 1, 2, 3, 5, 17, 18).

Every stage trains on PROBE-TRAIN, selects on PROBE-VAL (`probes.GRID` x `SEEDS`, D63
budget from the caller's `kw`) and scores on the role's score set (TEST, or PROBE-VAL in
the dry run) through the three-set parameters of `e3controls.fit_cells`,
`permuted_control`, `run_controls` and `run_unit_digit`. With score = PROBE-VAL the
D64 per-cell and D67 whole-layer stages reproduce the pre-lock script outputs exactly
(same RNG streams, seeds, grid and budget); the dry run checks this (Task 13).

`STAGES` (in run order; the last three are new for WP2 and come last, so the order of
the earlier stages is unchanged) are callables `(sets, kw, stored) -> StageResult`,
where `stored` is `{stage: {"summary", "files", "in_dims"}}` of the finished stages
(rebuilt by the runner from verified per-stage checkpoints). A `StageResult` is a dict:

- `summary`: JSON-ready; per fit name `summarize_fit` (or the `run_controls` /
  `run_unit_digit` summary) plus `n_score`, `rows` (`"cell"`, `"unit"` or `"reused"`)
  and `construction` (`"whole_layer"`, `"per_cell"` or `"input"`); stage extras under
  non-fit keys (`pca`: `wholelayer.pca_info` plus `explained_variance_share_score`;
  `pca_matches_saved`). Read fit entries through `STAGE_FITS`, never by iterating.
- `fits`: raw `fit_selected` dicts (`{"preds"}`, plus `probs` for `marginal`, for the
  untrained `rule` and `marginal`); `pcas`: the PCA dict a fit's features used;
  `in_dims`: probe input width incl. the position one-hot; `budget`: `budget_table`
  per trained fit (the §8.1 per-configuration, per-seed record).

Reused fits (`training_size` and `wl_training_size` at the full PROBE-TRAIN size)
copy the stored summary of `pc_L06.linear` / `wl_L06.generated`, flagged `reused: True`
with `reused_from`, and have no fit, budget or files of their own.

`save_stage` writes predictions (`preds/<stage>__<fit>.npz`), seed state dicts,
PCA tensors and a json meta per fit (`models/`), all atomically, and returns
`{fit: {relative path: SHA-256}}`; `load_probe` reloads them with
`torch.load(weights_only=True)`.
"""

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from ncm_sudoku.e3controls import (
    first_n,
    fit_cells,
    permute_labels,
    permuted_control,
    random_features,
    random_rows,
    run_controls,
    run_unit_digit,
    summarize_fit,
)
from ncm_sudoku.e3data import TEACHER_LEVELS, load_level, raw_features
from ncm_sudoku.probes import GRID, SEEDS, _make_model
from ncm_sudoku.wholelayer import cell_pca_features, raw_pca_features, variance_share
from ncm_sudoku.wp2 import atomic_json, atomic_npz, file_sha256

K = 256
SIZES = (125, 250, 500, 1000, 2000)
_ARRAYS = ("puzzles", "mask", "empty", "depth")
_PCA_TENSORS = ("mean", "components", "scale")
_PCA_SCALARS = ("n_components_fitted", "explained_variance_share", "n_rows")
_BUDGET_FIELDS = ("best_epoch", "epochs_run", "n_steps", "hit_cap", "n_params")
CONTROL_CONSTRUCTION = {
    "raw_linear": "input", "raw_mlp": "input", "peer_counts_linear": "input", "rule": "input",
    "surface_linear": "input", "permuted_linear": "per_cell", "random_linear": "per_cell",
    "label_permuted_linear": "per_cell", "teacher_L02_linear": "per_cell", "teacher_L06_linear": "per_cell",
    "teacher_L12_linear": "per_cell", "marginal": "input",
}
WL_PCA_FILE = "models/wl_L06__generated_pca.pt"

StageResult = dict


@dataclass
class Sets:
    probe_runs: Path  # runs/e3prep (probe_train/, probe_val/)
    score_root: Path  # runs/wp2/<role>/e3data (score/)
    out: Path  # runs/wp2/<role>/e3
    train: dict
    val: dict
    score: dict


def _subset(d: Path) -> dict:
    return {"ids": json.loads((d / "ids.json").read_text(encoding="utf-8")),
            **{k: np.load(d / f"{k}.npy") for k in _ARRAYS}}


def load_sets(probe_runs: Path, score_root: Path, out: Path) -> Sets:
    """PROBE-TRAIN, PROBE-VAL and the score set (`score_root/"score"`), each with `ids`,
    `puzzles`, `mask`, `empty`, `depth`. Raises if a score id is a PROBE-TRAIN id."""
    probe_runs, score_root, out = Path(probe_runs), Path(score_root), Path(out)
    train, val = _subset(probe_runs / "probe_train"), _subset(probe_runs / "probe_val")
    score = _subset(score_root / "score")
    if set(train["ids"]) & set(score["ids"]):
        raise ValueError("load_sets: score puzzles overlap PROBE-TRAIN")
    return Sets(probe_runs, score_root, out, train, val, score)


def level_triplet(sets: Sets, level: int, teacher: bool = False) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(train, val, score) states of one level, read-only memmaps."""
    return (load_level(sets.probe_runs, "probe_train", level, teacher=teacher),
            load_level(sets.probe_runs, "probe_val", level, teacher=teacher),
            load_level(sets.score_root, "score", level, teacher=teacher))


def whole_layer_triplet(sets: Sets, level: int, teacher: bool = False, k: int | None = None):
    """(pca, info, f_tr, f_va, f_sc) via `wholelayer.cell_pca_features` (PCA on the
    PROBE-TRAIN empty cells only); `k` defaults to the module's `K` at call time."""
    s_tr, s_va, s_sc = level_triplet(sets, level, teacher)
    return cell_pca_features(s_tr, s_va, sets.train["empty"], sets.val["empty"], K if k is None else k,
                             s_sc=s_sc, empty_sc=sets.score["empty"])


def budget_table(fit: dict) -> list[dict]:
    """One entry per (wd, lr, seed) of the `fit_selected` grid (GRID x SEEDS order), with
    `selected` marking the chosen configuration's seeds."""
    cfg = tuple(fit["config"])
    return [{"wd": wd, "lr": lr, "seed": s, **{k: fit["budget"][(wd, lr, s)][k] for k in _BUDGET_FIELDS},
             "selected": (wd, lr) == cfg} for wd, lr in GRID for s in SEEDS]


# --- stage helpers ----------------------------------------------------------------------------

def _new() -> StageResult:
    return {"summary": {}, "fits": {}, "pcas": {}, "in_dims": {}, "budget": {}}


def _keep(res, sets, name, fit, construction, rows="cell", pca=None, summary=None, **extra) -> None:
    s = summarize_fit(fit) if summary is None else summary
    res["summary"][name] = {**s, "n_score": len(sets.score["ids"]), "rows": rows, "construction": construction,
                            **extra}
    res["fits"][name] = fit
    if "state_dicts" in fit:
        res["in_dims"][name] = int(fit["state_dicts"][0]["0.weight"].shape[1])
        res["budget"][name] = budget_table(fit)
    if pca is not None:
        res["pcas"][name] = pca


def _reuse(res, name, stored, source: str, n_train: int) -> None:
    stage, fit = source.split(".")
    res["summary"][name] = {**stored[stage]["summary"][fit], "n_puzzles": n_train, "reused": True,
                            "reused_from": source, "rows": "reused"}
    res["in_dims"][name] = stored[stage]["in_dims"][fit]


def _fit(sets, f_tr, f_va, f_sc, kind, kw, **extra) -> dict:
    return fit_cells(f_tr, f_va, sets.train, sets.val, kind, f_score=f_sc, score=sets.score, **extra, **kw)


def _permuted(sets, f_tr, f_va, f_sc, kw) -> dict:
    return permuted_control(f_tr, f_va, sets.train, sets.val, rep_score=f_sc, score=sets.score, **kw)


def _need(stored: dict, stage: str, who: str) -> dict:
    if stage not in stored:
        raise ValueError(f"{who}: needs the stored {stage} stage")
    return stored[stage]


def _check_saved_pca(sets: Sets, wl: dict, pca: dict, who: str) -> None:
    """Raises unless the refitted level-6 PCA equals the saved wl_L06 one (listed file,
    recorded SHA-256, equal tensors)."""
    listed = wl["files"].get("generated", {})
    if WL_PCA_FILE not in listed:
        raise ValueError(f"{who}: {WL_PCA_FILE} is not listed in the stored wl_L06 files")
    path = sets.out / WL_PCA_FILE
    if file_sha256(path) != listed[WL_PCA_FILE]:
        raise ValueError(f"{who}: {path} differs from its recorded SHA-256")
    saved = torch.load(path, weights_only=True)
    for k in _PCA_TENSORS:
        if not torch.equal(saved[k], torch.from_numpy(np.asarray(pca[k]))):
            raise ValueError(f"{who}: the refitted level-6 PCA differs from the saved wl_L06 PCA ({k})")


# --- stages -----------------------------------------------------------------------------------

def _wl(level: int, teacher: bool = False):
    def stage(sets: Sets, kw: dict, stored: dict) -> StageResult:
        pca, info, f_tr, f_va, f_sc = whole_layer_triplet(sets, level, teacher)
        res = _new()
        if teacher:
            _keep(res, sets, "teacher", _fit(sets, f_tr, f_va, f_sc, "linear", kw), "whole_layer", pca=pca)
        else:
            _keep(res, sets, "generated", _fit(sets, f_tr, f_va, f_sc, "linear", kw), "whole_layer", pca=pca)
            _keep(res, sets, "permuted", _permuted(sets, f_tr, f_va, f_sc, kw), "whole_layer", pca=pca)
        res["summary"]["pca"] = info
        return res
    return stage


def _raw_projected(sets: Sets, kw: dict, stored: dict) -> StageResult:
    tr, va, sc = sets.train, sets.val, sets.score
    pca, info, f_tr, f_va, f_sc = raw_pca_features(tr["puzzles"], va["puzzles"], tr["empty"], va["empty"], K,
                                                   p_sc=sc["puzzles"])
    info["explained_variance_share_score"] = variance_share(raw_features(sc["puzzles"])[sc["empty"]], pca)
    res = _new()
    _keep(res, sets, "linear", _fit(sets, f_tr, f_va, f_sc, "linear", kw), "input", pca=pca)
    res["summary"]["pca"] = info
    return res


def _raw_unprojected(sets: Sets, kw: dict, stored: dict) -> StageResult:
    f = [raw_features(d["puzzles"]) for d in (sets.train, sets.val, sets.score)]
    res = _new()
    _keep(res, sets, "linear", _fit(sets, *f, "linear", kw), "input")
    return res


def _pc(level: int):
    def stage(sets: Sets, kw: dict, stored: dict) -> StageResult:
        rep = level_triplet(sets, level)
        res = _new()
        for kind in ("linear", "mlp"):
            _keep(res, sets, kind, _fit(sets, *rep, kind, kw), "per_cell")
        if level != 6:  # level 6: the permuted control is part of `controls` (D64)
            _keep(res, sets, "permuted", _permuted(sets, *rep, kw), "per_cell")
        return res
    return stage


def _with_rep(sets: Sets, rep, teacher=None) -> list[dict]:
    out = []
    for i, d in enumerate((sets.train, sets.val, sets.score)):
        e = {**d, "rep": rep[i]}
        if teacher is not None:
            e["teacher"] = {lv: teacher[lv][i] for lv in TEACHER_LEVELS}
        out.append(e)
    return out


def _controls(sets: Sets, kw: dict, stored: dict) -> StageResult:
    teacher = {lv: level_triplet(sets, lv, teacher=True) for lv in TEACHER_LEVELS}
    d_tr, d_va, d_sc = _with_rep(sets, level_triplet(sets, 6), teacher)
    fits: dict = {}
    out = run_controls(d_tr, d_va, score=d_sc, fits=fits, **kw)
    if list(out) != list(STAGE_FITS["controls"]):
        raise ValueError(f"controls: run_controls returned {list(out)}, expected {list(STAGE_FITS['controls'])}")
    res = _new()
    for name in STAGE_FITS["controls"]:
        _keep(res, sets, name, fits[name], CONTROL_CONSTRUCTION[name], summary=out[name])
    return res


def _unit_digit(sets: Sets, kw: dict, stored: dict) -> StageResult:
    d_tr, d_va, d_sc = _with_rep(sets, level_triplet(sets, 6))
    fits: dict = {}
    out = run_unit_digit(d_tr, d_va, score=d_sc, fits=fits, **kw)
    res = _new()
    for name, construction in (("generated", "per_cell"), ("raw", "input")):
        _keep(res, sets, name, fits[name], construction, rows="unit", summary=out[name])
    return res


def _training_size(sets: Sets, kw: dict, stored: dict) -> StageResult:
    """D64 per-cell level-6 linear curve on the first n PROBE-TRAIN puzzles; the full
    size reuses the stored `pc_L06.linear` fit (identical, deterministic)."""
    _need(stored, "pc_L06", "training_size")
    n_train = len(sets.train["puzzles"])
    res, rep = _new(), None
    for n in SIZES:
        if n >= n_train:
            _reuse(res, f"n{n}", stored, "pc_L06.linear", n_train)
            continue
        if rep is None:
            rep = level_triplet(sets, 6)
        sub = first_n({**sets.train, "rep": rep[0]}, n)
        fit = fit_cells(sub["rep"], rep[1], sub, sets.val, "linear", f_score=rep[2], score=sets.score, **kw)
        _keep(res, sets, f"n{n}", fit, "per_cell", n_puzzles=n, reused=False)
    return res


def _wl_L06_controls(sets: Sets, kw: dict, stored: dict) -> StageResult:
    """Whole-layer level-6 random features (width K + F, seed 0, `random_rows` stream)
    and label permutation (seed 0) with the refitted (= saved) PROBE-TRAIN PCA."""
    wl = _need(stored, "wl_L06", "wl_L06_controls")
    pca, info, f_tr, f_va, f_sc = whole_layer_triplet(sets, 6)
    _check_saved_pca(sets, wl, pca, "wl_L06_controls")
    tr, va, sc = sets.train, sets.val, sets.score
    dim = K + (f_tr.shape[2] - pca["components"].shape[0])  # K + F
    if dim + 81 != wl["in_dims"]["generated"]:
        raise ValueError(f"wl_L06_controls: random-feature input width {dim + 81} differs from the "
                         f"wl_L06 probe width {wl['in_dims']['generated']}")
    n_tr, n_va = len(tr["puzzles"]), len(va["puzzles"])
    rows = random_rows(n_tr, va["ids"], sc["ids"])
    n_new = int((rows >= n_tr + n_va).sum())
    rnd = random_features(n_tr + n_va + n_new, seed=0, dim=dim)
    res = _new()
    _keep(res, sets, "random", _fit(sets, rnd[:n_tr], rnd[n_tr: n_tr + n_va], rnd[rows], "linear", kw), "whole_layer")
    del rnd
    mask_tr = permute_labels(tr["mask"], tr["empty"], 0)
    _keep(res, sets, "label_permuted", _fit(sets, f_tr, f_va, f_sc, "linear", kw, mask_tr=mask_tr), "whole_layer",
          pca=pca)
    res["summary"].update(pca=info, pca_matches_saved=True)
    return res


def _wl_training_size(sets: Sets, kw: dict, stored: dict) -> StageResult:
    """Whole-layer level-6 curve: the full-PROBE-TRAIN PCA (refitted, = saved), probe
    trained on the first n puzzles, selected on the full PROBE-VAL; the full size
    reuses the stored `wl_L06.generated` fit."""
    wl = _need(stored, "wl_L06", "wl_training_size")
    pca, info, f_tr, f_va, f_sc = whole_layer_triplet(sets, 6)
    _check_saved_pca(sets, wl, pca, "wl_training_size")
    n_train = len(sets.train["puzzles"])
    res = _new()
    for n in SIZES:
        if n >= n_train:
            _reuse(res, f"n{n}", stored, "wl_L06.generated", n_train)
            continue
        fit = fit_cells(f_tr[:n], f_va, first_n(sets.train, n), sets.val, "linear", f_score=f_sc, score=sets.score,
                        **kw)
        _keep(res, sets, f"n{n}", fit, "whole_layer", pca=pca, n_puzzles=n, reused=False)
    res["summary"].update(pca=info, pca_matches_saved=True)
    return res


STAGES: list[tuple[str, Callable[[Sets, dict, dict], StageResult]]] = [
    ("wl_L06", _wl(6)),
    ("wl_L12", _wl(12)),
    ("wl_teacher_L12", _wl(12, teacher=True)),
    ("wl_L02", _wl(2)),
    ("raw_projected", _raw_projected),
    ("raw_unprojected", _raw_unprojected),
    ("pc_L02", _pc(2)),
    ("pc_L06", _pc(6)),
    ("pc_L12", _pc(12)),
    ("controls", _controls),
    ("unit_digit", _unit_digit),
    ("training_size", _training_size),
    ("wl_L06_controls", _wl_L06_controls),
    ("wl_teacher_L06", _wl(6, teacher=True)),
    ("wl_training_size", _wl_training_size),
]

_SIZE_FITS = tuple(f"n{n}" for n in SIZES)
STAGE_FITS: dict[str, tuple[str, ...]] = {
    "wl_L06": ("generated", "permuted"),
    "wl_L12": ("generated", "permuted"),
    "wl_teacher_L12": ("teacher",),
    "wl_L02": ("generated", "permuted"),
    "raw_projected": ("linear",),
    "raw_unprojected": ("linear",),
    "pc_L02": ("linear", "mlp", "permuted"),
    "pc_L06": ("linear", "mlp"),
    "pc_L12": ("linear", "mlp", "permuted"),
    "controls": tuple(CONTROL_CONSTRUCTION),
    "unit_digit": ("generated", "raw"),
    "training_size": _SIZE_FITS,
    "wl_L06_controls": ("random", "label_permuted"),
    "wl_teacher_L06": ("teacher",),
    "wl_training_size": _SIZE_FITS,
}


# --- saved predictions and models -------------------------------------------------------------

def _atomic_pt(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        torch.save(obj, tmp)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _fit_files(out: Path, stage: str, fit: str) -> dict[str, str]:
    """{relative path: SHA-256} of a saved fit, read from its json meta."""
    base = f"{stage}__{fit}"
    meta = json.loads((out / "models" / f"{base}.json").read_text(encoding="utf-8"))
    names = [f"preds/{base}.npz", f"models/{base}.json", *(f"models/{f}" for f in meta["files"])]
    if meta["pca_file"]:
        names.append(f"models/{meta['pca_file']}")
    return {n: file_sha256(out / n) for n in names}


def _fit_names(res: StageResult) -> list[str]:
    return [k for k, v in res["summary"].items()
            if k in res["fits"] or (isinstance(v, dict) and v.get("reused") is True)]


def save_stage(out: Path, stage: str, res: StageResult) -> dict[str, dict[str, str]]:
    """Writes per fit `preds/<stage>__<fit>.npz` (`seed0..2` and `mean` on the score rows,
    float32; `mean` only for `rule` and `marginal`), `models/<stage>__<fit>_seed<s>.pt`
    (state dicts), `models/<stage>__<fit>_pca.pt` (tensors `mean`, `components`, `scale`
    plus scalars) and `models/<stage>__<fit>.json` (`kind`, `in_dim`, `config`, `files`,
    `pca_file`, `rows`; `marginal` also `probs`), all atomically. Reused fits write
    nothing and list the reused fit's files. Returns {fit: {relative path: SHA-256}}."""
    out = Path(out)
    files = {}
    for fit in _fit_names(res):
        s = res["summary"][fit]
        if s.get("reused") is True:
            files[fit] = _fit_files(out, *s["reused_from"].split("."))
            continue
        raw, base = res["fits"][fit], f"{stage}__{fit}"
        arrays = {f"seed{sd}": np.asarray(p, np.float32) for sd, p in zip(SEEDS, raw.get("seed_preds", []))}
        atomic_npz(out / "preds" / f"{base}.npz", **arrays, mean=np.asarray(raw["preds"], np.float32))
        model_files = []
        for sd, state in zip(SEEDS, raw.get("state_dicts", [])):
            model_files.append(f"{base}_seed{sd}.pt")
            _atomic_pt(out / "models" / model_files[-1], state)
        pca_file = None
        if fit in res["pcas"]:
            pca = res["pcas"][fit]
            pca_file = f"{base}_pca.pt"
            _atomic_pt(out / "models" / pca_file, {k: torch.from_numpy(np.asarray(pca[k])) for k in _PCA_TENSORS}
                       | {k: pca[k] for k in _PCA_SCALARS})
        if "state_dicts" in raw:
            kind = "mlp" if "2.weight" in raw["state_dicts"][0] else "linear"
        else:
            kind = fit
        meta = {"kind": kind, "in_dim": res["in_dims"].get(fit), "config": s.get("config"), "files": model_files,
                "pca_file": pca_file, "rows": s["rows"]}
        if "probs" in raw:
            meta["probs"] = np.asarray(raw["probs"], np.float64).tolist()
        atomic_json(out / "models" / f"{base}.json", meta)
        files[fit] = _fit_files(out, stage, fit)
    return files


def load_probe(out: Path, stage: str, fit: str) -> tuple[list[torch.nn.Module], dict | None, dict]:
    """(seed probes in eval mode, pca with numpy arrays or None, meta), loaded with
    `torch.load(weights_only=True)`; the pca goes straight into `whole_layer_features`."""
    d = Path(out) / "models"
    meta = json.loads((d / f"{stage}__{fit}.json").read_text(encoding="utf-8"))
    probes = []
    for f in meta["files"]:
        p = _make_model(meta["kind"], meta["in_dim"])
        p.load_state_dict(torch.load(d / f, weights_only=True))
        probes.append(p.eval())
    pca = None
    if meta["pca_file"]:
        raw = torch.load(d / meta["pca_file"], weights_only=True)
        pca = {k: (v.numpy() if isinstance(v, torch.Tensor) else v) for k, v in raw.items()}
    return probes, pca, meta
