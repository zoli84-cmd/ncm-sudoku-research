"""E3 equivariance pilot (D59) and H1 sample size (D60). Non-confirmatory planning output.

Usage: uv run python scripts/e3_equiv_power.py [--force | --power-only]
Needs scripts/e3_probes.py output: the selected level-6 linear seed models
(runs/e3prep/models/L06_linear*.{json,pt}) and experiments/e3prep/h1_diffs.json.
- Equivariance: the first 200 PROBE-VAL puzzles (runs/e3prep/probe_val/puzzles.npy, id
  order), 4 full-group + 2 digit-only + 2 geometric-only elements each (seed 0), every
  transformed puzzle re-run through the model; deviation and Brier against the original's
  candidate mask (plan §8.4); writes experiments/e3prep/equivariance.json.
  Rerun-guarded on that file (--force to overwrite).
- H1 sample size: `power.h1_sample_size` on the per-puzzle differences; writes
  experiments/e3prep/sample_size_h1.json with test_size = ceil(max(h1, 600) / 100) * 100.
  Deterministic; --power-only runs only this part (no model, no guard).
"""

import json
import os
import sys
import time

import numpy as np
import torch

from ncm_sudoku.e3equiv import equivariance_pilot, model_predict_fn
from ncm_sudoku.g0 import code_state, environment_record
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.power import h1_sample_size
from ncm_sudoku.probes import _make_model

RUNS = ROOT / "runs" / "e3prep"
OUT = ROOT / "experiments" / "e3prep"
MODELS = RUNS / "models"
N_EQUIV = 200
MIN_TEST = 600
NOTE = "non-confirmatory planning output (plan v3.6 §12.1)"


def guard(force: bool) -> None:
    path = OUT / "equivariance.json"
    if path.exists() and not force:
        sys.exit(f"{path} exists: the equivariance pilot is rerun-guarded; use --force or --power-only")


def test_size(h1: int | None) -> int | None:
    """Final TEST size = max(H1, 600), rounded up to 100 (D60)."""
    return None if h1 is None else -(-max(h1, MIN_TEST) // 100) * 100


def _dump(path, obj) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n", newline="\n")
    os.replace(tmp, path)


def _probes() -> tuple[dict, list[torch.nn.Module]]:
    meta = json.loads((MODELS / "L06_linear.json").read_text(encoding="utf-8"))
    probes = []
    for f in meta["files"]:
        p = _make_model(meta["kind"], meta["in_dim"])
        p.load_state_dict(torch.load(MODELS / f, weights_only=True))
        probes.append(p.eval())
    return meta, probes


def equivariance() -> None:
    torch.use_deterministic_algorithms(True)
    environment = environment_record()
    meta, probes = _probes()
    if not meta.get("retrain_matches"):
        print("WARNING: the saved level-6 seed models do not reproduce the selected grid fit "
              f"(retrain_matches={meta.get('retrain_matches')}); equivariance uses the saved models")
    puzzles = np.load(RUNS / "probe_val" / "puzzles.npy")[:N_EQUIV]
    ids = json.loads((RUNS / "probe_val" / "ids.json").read_text(encoding="utf-8"))[:N_EQUIV]
    m = load_model(ROOT / "checkpoints" / "sudoku" / "hard")
    cache: dict = {}  # the three seed probes share one model run per puzzle batch
    t0 = time.perf_counter()
    r = equivariance_pilot(puzzles, [model_predict_fn(m, p, cache) for p in probes], n=N_EQUIV)
    out = {
        "note": NOTE, "date": time.strftime("%Y-%m-%d"), "environment": environment, "code": code_state(),
        "probe": meta, "ids": ids,
        **{k: r[k] for k in ("n", "k", "seed", "n_predictors", "acceptable", "share_within", "mean_deviation",
                             "mean_brier", "mean_brier_original")},
        "elements_per_puzzle": {"all": r["k"], "digit": 2, "geometric": 2},
        "deviation": {k: np.asarray(v).tolist() for k, v in r["deviation"].items()},
        "seed_noise": np.asarray(r["seed_noise"]).tolist(),
        "brier": {k: np.asarray(v).tolist() for k, v in r["brier"].items()},
        "brier_original": np.asarray(r["brier_original"]).tolist(),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    _dump(OUT / "equivariance.json", out)


def sample_size() -> None:
    diffs = json.loads((OUT / "h1_diffs.json").read_text(encoding="utf-8"))["diffs"]
    r = h1_sample_size(np.asarray(diffs, dtype=float))
    _dump(OUT / "sample_size_h1.json", {"note": NOTE, "code": code_state(), **r, "test_size": test_size(r["h1"]),
                                        "min_test": MIN_TEST})


def main() -> None:
    if "--power-only" not in sys.argv:
        guard(force="--force" in sys.argv)
        equivariance()
    sample_size()


if __name__ == "__main__":
    main()
