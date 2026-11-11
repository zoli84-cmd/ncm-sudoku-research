"""Level-12 whole-layer equivariance: acceptable deviation before the lock (D59, D68(4), D70(4);
plan v3.6 §8.4, §12.2). Exploratory and non-confirmatory planning output.

Usage: uv run python scripts/lock_equiv_l12.py [--force]
Needs runs/e3prep/<probe_train|probe_val>/ (scripts/e3_extract.py) and the checkpoints.
1. Whole-layer probe (D66 construction, `ncm_sudoku.wholelayer`): PCA-256 of the 21-cell peer
   states fitted on PROBE-TRAIN level-12 empty cells, whitened scores || own state ||
   position one-hot; three linear seed probes (seeds 0-2) trained with `probes.train_probe`
   at the D67 selected configuration (weight decay 0.1, lr 1e-3), D63 budget, early stopping
   on PROBE-VAL Brier (the per-seed training `fit_selected` runs inside its grid). The
   seed-mean per-puzzle PROBE-VAL Brier is compared with the stored D67 grid fit
   (experiments/e3prep/wholelayer.json, stage L12; `matches_d67`, None if absent); on a
   mismatch the script exits non-zero before the equivariance pilot unless --force.
   Seed state dicts, the PCA (tensors) and a JSON config go to runs/lock/equiv_l12/;
   `load_saved` reloads them with torch.load(weights_only=True).
2. `e3equiv.equivariance_pilot` on the first 200 PROBE-VAL puzzles (k = 4 full-group +
   2 digit-only + 2 geometric-only elements per puzzle, seed 0, D59 interleaving), one
   predictor per seed probe: generate through the model -> level-12 cell states ->
   whole-layer features with the fitted PCA -> probe.
Writes experiments/lock/equivariance_l12.json (acceptable deviation = P95 of seed noise,
mean deviation and share within per kind, Brier transformed vs. original, code state,
environment, run times). Rerun-guarded on that file (--force to overwrite).
"""

import json
import os
import sys
import time

import numpy as np
import torch

from ncm_sudoku.e3data import load_level
from ncm_sudoku.e3equiv import equivariance_pilot, model_predict_fn
from ncm_sudoku.g0 import code_state, environment_record
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.probes import SEEDS, _make_model, brier_per_puzzle, build_inputs, train_probe
from ncm_sudoku.wholelayer import fit_cell_pca, whole_layer_features

E3RUNS = ROOT / "runs" / "e3prep"
RUNS = ROOT / "runs" / "lock" / "equiv_l12"
OUT = ROOT / "experiments" / "lock"
WHOLELAYER = ROOT / "experiments" / "e3prep" / "wholelayer.json"
LEVEL = 12
K = 256
CONFIG = (0.1, 1e-3)  # D67 selected (weight decay, lr) for the level-12 whole-layer linear probe
KW: dict = {}  # train_probe budget overrides; empty = D55/D63 defaults (tests shrink it)
N_EQUIV = 200
K_ELEMENTS = 4
NOTE = ("exploratory, non-confirmatory planning output (plan v3.6 §8.4, §12.1; D70(4)): "
        "acceptable deviation for the level-12 whole-layer equivariance analysis")


def guard(force: bool) -> None:
    path = OUT / "equivariance_l12.json"
    if path.exists() and not force:
        sys.exit(f"{path} exists: lock_equiv_l12 is a rerun-guarded script; use --force to overwrite")


def _subset(name: str) -> dict:
    d = E3RUNS / name
    return {"ids": json.loads((d / "ids.json").read_text(encoding="utf-8")),
            **{k: np.load(d / f"{k}.npy") for k in ("puzzles", "mask", "empty")}}


def _atomic(path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def _matches_d67(per_puzzle: np.ndarray, val_ids: list) -> bool | None:
    """True if the seed-mean per-puzzle Brier equals the stored D67 L12 grid fit on the same ids."""
    if not WHOLELAYER.exists():
        return None
    wl = json.loads(WHOLELAYER.read_text(encoding="utf-8"))
    g = wl.get("stages", {}).get("L12", {}).get("generated_linear")
    if g is None or wl.get("val_ids") != val_ids or tuple(g["config"]) != CONFIG:
        return False
    stored = np.asarray(g["per_puzzle"], dtype=float)
    return bool(stored.shape == per_puzzle.shape and np.allclose(stored, per_puzzle, equal_nan=True))


def train(tr: dict, va: dict) -> tuple[list, dict, dict]:
    """Fits the PCA and the three seed probes, saves them to RUNS and returns (probes, pca, meta)."""
    s_tr = load_level(E3RUNS, "probe_train", LEVEL)
    s_va = load_level(E3RUNS, "probe_val", LEVEL)
    pca = fit_cell_pca(s_tr, tr["empty"], K)
    f_tr, f_va = whole_layer_features(s_tr, pca), whole_layer_features(s_va, pca)
    del s_tr, s_va
    Xtr, _, _ = build_inputs(f_tr, tr["empty"])
    Ytr = torch.from_numpy(np.asarray(tr["mask"])[tr["empty"]].astype(np.float32))
    Xva, pz, _ = build_inputs(f_va, va["empty"])
    Yva = torch.from_numpy(np.asarray(va["mask"])[va["empty"]].astype(np.float32))
    del f_tr, f_va
    n_va = len(va["empty"])
    RUNS.mkdir(parents=True, exist_ok=True)
    probes, per, budget, files = [], [], [], []
    for seed in SEEDS:
        model, _, info = train_probe(Xtr, Ytr, Xva, Yva, pz.numpy(), n_va, "linear", *CONFIG, seed, **KW)
        with torch.no_grad():
            per.append(brier_per_puzzle(model(Xva).numpy(), Yva.numpy(), pz.numpy(), n_va))
        name = f"L{LEVEL:02d}_wholelayer_seed{seed}.pt"
        torch.save(model.state_dict(), RUNS / name)
        probes.append(model.eval()); budget.append(info); files.append(name)
    torch.save({k: torch.from_numpy(np.asarray(pca[k])) for k in ("mean", "components", "scale")}
               | {k: pca[k] for k in ("n_components_fitted", "explained_variance_share", "n_rows")}, RUNS / "pca.pt")
    per_puzzle = np.mean(per, axis=0)
    meta = {
        "level": LEVEL, "kind": "linear", "features": "whole-layer (D66)", "k": int(K),
        "config": list(CONFIG), "in_dim": int(Xtr.shape[1]), "seeds": list(SEEDS), "files": files,
        "pca_file": "pca.pt", "budget_overrides": json.loads(json.dumps(KW)), "budget": budget,
        "pca_explained_variance_share": float(pca["explained_variance_share"]), "pca_n_rows": int(pca["n_rows"]),
        "val_brier_mean": float(np.nanmean(per_puzzle)), "per_puzzle": per_puzzle.tolist(),
        "matches_d67": _matches_d67(per_puzzle, va["ids"]),
    }
    (RUNS / f"L{LEVEL:02d}_wholelayer.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8",
                                                         newline="\n")
    return probes, pca, meta


def load_saved(dirpath) -> tuple[list, dict, dict]:
    """Reloads (probes in eval mode, pca with numpy arrays, meta) with weights_only=True."""
    meta = json.loads((dirpath / f"L{LEVEL:02d}_wholelayer.json").read_text(encoding="utf-8"))
    probes = []
    for f in meta["files"]:
        p = _make_model(meta["kind"], meta["in_dim"])
        p.load_state_dict(torch.load(dirpath / f, weights_only=True))
        probes.append(p.eval())
    raw = torch.load(dirpath / meta["pca_file"], weights_only=True)
    pca = {k: (v.numpy() if isinstance(v, torch.Tensor) else v) for k, v in raw.items()}
    return probes, pca, meta


def main() -> None:
    force = "--force" in sys.argv
    guard(force=force)
    torch.use_deterministic_algorithms(True)  # before environment_record()
    environment = environment_record()
    tr, va = _subset("probe_train"), _subset("probe_val")
    t0 = time.perf_counter()
    probes, pca, meta = train(tr, va)
    t_train = round(time.perf_counter() - t0, 1)
    if meta["matches_d67"] is False:
        msg = "the level-12 seed probes do not reproduce the stored D67 whole-layer fit (matches_d67=False)"
        if not force:
            sys.exit(f"ERROR: {msg}; stopping before the equivariance pilot (use --force to continue)")
        print(f"WARNING: {msg}; continuing because of --force")
    m = load_model(ROOT / "checkpoints" / "sudoku" / "hard")
    feats = lambda s: whole_layer_features(s, pca)  # noqa: E731  one object: the shared cache keys on it
    cache: dict = {}
    t1 = time.perf_counter()
    r = equivariance_pilot(va["puzzles"][:N_EQUIV],
                           [model_predict_fn(m, p, cache, level=LEVEL, features=feats) for p in probes],
                           n=N_EQUIV, k=K_ELEMENTS, seed=0)
    out = {
        "note": NOTE, "non_confirmatory": True, "date": time.strftime("%Y-%m-%d"), "environment": environment,
        "code": code_state(), "level": LEVEL, "matches_d67": meta["matches_d67"],
        "probe": {k: v for k, v in meta.items() if k != "per_puzzle"}, "ids": va["ids"][: r["n"]],
        **{k: r[k] for k in ("n", "k", "seed", "n_predictors", "acceptable", "share_within", "mean_deviation",
                             "mean_brier", "mean_brier_original")},
        "elements_per_puzzle": {"all": r["k"], "digit": 2, "geometric": 2},
        "deviation": {k: np.asarray(v).tolist() for k, v in r["deviation"].items()},
        "seed_noise": np.asarray(r["seed_noise"]).tolist(),
        "brier": {k: np.asarray(v).tolist() for k, v in r["brier"].items()},
        "brier_original": np.asarray(r["brier_original"]).tolist(),
        "seconds": {"train": t_train, "equivariance": round(time.perf_counter() - t1, 1)},
    }
    _atomic(OUT / "equivariance_l12.json", json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("acceptable", "mean_deviation", "share_within", "seconds")}))


if __name__ == "__main__":
    main()
