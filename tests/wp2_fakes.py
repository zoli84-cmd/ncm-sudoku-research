"""Synthetic raw WP2 outputs for one role (tests of `scripts/wp2_evaluate.py`).

`write_role` writes every input the evaluation reads, with hand-set values, under `root`:
`runs/wp2/<role>/{e1.json, e2.json, e2/diag/*.npz, e3/preds/*.npz, e3data/score/*}`,
`experiments/wp2/<role>/{e3_fits.json, e3_budget.json, equivariance.json}`, the five run
records (complete and valid at `TAG`, with output manifests matching the files) and the
pre-lock `experiments/e3prep/{probes.json, wholelayer.json}` configurations.

Known values:
- E2 (n puzzles, ids `e2-<i>`): every puzzle solves under A, B1, B, C (configurations) and D
  (configurations), so theta2 = level-1 term only. Each of the first `m` puzzles fails under D
  (and C) for two of its 15 non-no-op level-1 values (weight 1/15 each), so
  theta2 = -2 m / (15 n) and theta_comp = theta2_prime = 0 for every puzzle.
- Configuration tv = dose * TV_PER_DOSE[level], so the 6 vs. 11 frozen range is covered.
- Diagnostics: configuration stages change cell 0 under D in every row and no cell under C;
  the primary level-11 stages have state_dist_D = 0.5 and state_dist_C = 0.25 at every level.
- E3 (n_score puzzles, ids `score-<i>`): per puzzle and seed the prediction deviates from the
  label by d in every bit, so the per-puzzle Brier is d^2 = base + jitter (jitter shared by every
  fit); `wl_L06.permuted` has base + theta1_shift, so theta1 = theta1_shift up to float32.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from ncm_sudoku import wp2
from ncm_sudoku.e3controls import unit_digit_labels
from ncm_sudoku.e3data import labels
from ncm_sudoku.probes import GRID, SEEDS, brier_per_puzzle
from ncm_sudoku.symmetry import apply_symmetry, random_symmetry
from ncm_sudoku.wp2e3 import CONTROL_CONSTRUCTION, STAGE_FITS
from sudoku_cases import P

TAG = "a" * 40
CODE = {"commit": TAG, "dirty": False, "diff_sha256": None}
ENV = {"python": "3.12.0", "torch": "2.x", "deterministic": True}
FROZEN = {"tag": "wp2-code", "tag_commit": TAG, "head": TAG, "code_clean": True,
          "upstream_commit": wp2.UPSTREAM_COMMIT, "upstream_ok": True, "upstream_clean": True, "frozen": True}
N_LEVELS = 12
DOSES = {2: (1, 2), 6: (1, 2, 4, 8, 13), 11: (1, 4, 11, 21, 41, 67)}
TV_PER_DOSE = {2: 3e-5, 6: 2e-5, 11: 1e-5}
POLICIES = ("frequency", "uniform")
PRIMARY_L11 = tuple(f"L11/frequency/d01/s{s}" for s in (0, 1, 2))
BASE_BRIER = 0.2
RAW_BRIER = 0.01


def _puzzles(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.stack([apply_symmetry(P, random_symmetry(rng)) for _ in range(n)]).astype(np.uint8)


def record(runner: str, role: str, **extra) -> dict:
    return {"runner": runner, "role": role, "note": wp2.DRY_NOTE if role == "dry" else None,
            "environment": dict(ENV), "code": dict(CODE), "freeze": dict(FROZEN), "inputs": {},
            "seconds": 1.5, "environment_end": dict(ENV), "code_end": dict(CODE), "freeze_end": dict(FROZEN),
            "code_changed_during_run": False, "complete": True, "valid": True, "invalid_reasons": [],
            "status": "valid", **extra}


# --- E1 ---------------------------------------------------------------------------------------

def _e1_records(ids: list[str]) -> list[dict]:
    out = []
    for i, pid in enumerate(ids):
        ok = i % 4 != 0
        out.append({
            "puzzle_id": pid, "official_exact": ok, "well_formed": True, "solve": ok, "valid_grid": ok,
            "all_clues_preserved": True, "clue_preservation": 1.0, "cell_acc_all": 1.0 if ok else 0.9,
            "cell_acc_empty": 1.0 if ok else 0.8, "constraint_violations": 0 if ok else 2, "reference_match": ok,
            "format_error": False, "token_hamming": 0.0 if ok else 0.05, "cell_hamming": 0.0 if ok else 0.1,
            "cell_hamming_empty": 0.0 if ok else 0.2, "teacher_exact": True, "teacher_cell_acc_all": 1.0,
            "teacher_solve": True,
            "per_level": [{"level": lv, "code_agreement": lv / N_LEVELS, "solve": ok and lv == N_LEVELS,
                           "cell_acc_all": 0.5, "cell_acc_empty": 0.4, "format_error": False}
                          for lv in range(1, N_LEVELS + 1)],
        })
    return out


# --- E2 ---------------------------------------------------------------------------------------

def _compare_fields(solve: int, tv: float, changes: int) -> dict:
    return {"solve_C": solve, "solve_D": solve, "well_formed_C": True, "well_formed_D": True, "tv": tv,
            "tv_empty": tv, "hamming_CA": 0.0, "hamming_CA_empty": 0.0, "latent": 0.1, "codebook_rms": 0.1,
            "requant_ratio": 0.5, "downstream_changes_D": changes}


def _diag(n: int, dose: int, full: bool, changed_cells_C, changed_cells_D, later_from: int, valid,
          state_C: float = 0.25, state_D: float = 0.5, new=None, orig=None) -> dict:
    valid = np.asarray(valid, bool)

    def cells(which):
        a = np.zeros((n, 81), bool)
        for i, c in enumerate(which):
            if c is not None and valid[i]:
                a[i, c] = True
        return a

    later = np.zeros((n, N_LEVELS), np.int16)
    later[valid, later_from:] = 2
    f = np.where(valid[:, None], 1.0, np.nan).astype(np.float32)
    d = {"changed_C": cells(changed_cells_C), "changed_D": cells(changed_cells_D), "later_changes_D": later,
         "positions": np.zeros((n, dose), np.int16),
         "orig": (np.zeros((n, dose)) if orig is None else np.asarray(orig).reshape(n, dose)).astype(np.int16),
         "new": (np.ones((n, dose)) if new is None else np.asarray(new).reshape(n, dose)).astype(np.int16),
         "p_new": np.broadcast_to(0.1 * f, (n, dose)).copy(), "p_orig": np.broadcast_to(0.6 * f, (n, dose)).copy(),
         "freq_new": np.broadcast_to(f / 16, (n, dose)).copy(), "replacement_norm": np.where(valid, 1.0, 0.0)
         .astype(np.float32)}
    if full:
        for b, v, cs in (("C", state_C, changed_cells_C), ("D", state_D, changed_cells_D)):
            d[f"state_dist_{b}"] = np.where(valid[:, None], v, 0.0).astype(np.float32) * np.ones((1, N_LEVELS),
                                                                                                 np.float32)
            lc = np.zeros((n, N_LEVELS, 81), bool)
            lc[:, :, :] = cells(cs)[:, None, :]
            d[f"level_changed_{b}"] = lc
    return d


def _e2(ids: list[str], theta2: float, identity_failure: bool) -> tuple[dict, dict]:
    n = len(ids)
    m = round(-theta2 * 15 * n / 2)
    if not (0 <= m <= n) or abs(-2 * m / (15 * n) - theta2) > 1e-12:
        raise ValueError(f"theta2={theta2} is not representable as -2 m / (15 n) with n={n}")
    a1 = [i % 16 for i in range(n)]
    fail = {i: {(a1[i] + 1) % 16, (a1[i] + 2) % 16} for i in range(m)}
    base = [{"puzzle_id": pid, "solve_A": 1, "solve_B1": 1} for pid in ids]
    level1, diags = [], {}
    for v in range(16):
        noop = [a1[i] == v for i in range(n)]
        for i, pid in enumerate(ids):
            solve = 0 if v in fail.get(i, ()) else 1
            w = 0.0 if noop[i] else 1 / 15
            level1.append({"puzzle_id": pid, "value": v, "noop": noop[i], "w_frequency": w, "w_uniform": w,
                           **_compare_fields(solve, 0.0 if noop[i] else 1e-3, 0 if noop[i] else 3)})
        diags[f"level1/v{v:02d}"] = _diag(n, 1, True, [v] * n, [v] * n, 1, [not x for x in noop],
                                          new=[v] * n, orig=a1)
    records = []
    for level in (2, 6, 11):
        for policy in POLICIES:
            for dose in DOSES[level]:
                for seed in (0, 1, 2):
                    key = f"L{level:02d}/{policy}/d{dose:02d}/s{seed}"
                    records += [{"puzzle_id": pid, "level": level, "policy": policy, "dose": dose, "seed": seed,
                                 "eligible": True, "solve_A": 1, "solve_B": 1,
                                 **_compare_fields(1, dose * TV_PER_DOSE[level], 2)} for pid in ids]
                    diags[key] = _diag(n, dose, key in PRIMARY_L11, [None] * n, [0] * n, level, [True] * n)
    code_mismatch = {"level1_B1": 1 if identity_failure else 0, "levels_B": {"2": 0, "6": 0, "11": 0},
                     "level1_noop_D": 0}
    out = {"freqs_level1": [1 / 16] * 16, "freq_source": "frozen", "base": base, "level1": level1,
           "level1_noop_mismatch": 0, "level1_noop_max_tv": {"tv": 0.0, "tv_empty": 0.0}, "records": records,
           "code_mismatch": code_mismatch}
    return out, diags


# --- E3 ---------------------------------------------------------------------------------------

def _construction(stage: str, fit: str) -> str:
    if stage == "controls":
        return CONTROL_CONSTRUCTION[fit]
    if stage.startswith("raw_") or (stage == "unit_digit" and fit == "raw"):
        return "input"
    if stage.startswith("wl_"):
        return "whole_layer"
    return "per_cell"


def _base_brier(stage: str, fit: str, theta1_shift: float) -> float:
    if (stage, fit) in (("wl_L06", "permuted"),):
        return BASE_BRIER + theta1_shift
    if stage.startswith("raw_") or fit.startswith("raw") or fit == "peer_counts_linear":
        return RAW_BRIER
    return BASE_BRIER


def _seed_preds(y: np.ndarray, d_rows: np.ndarray) -> np.ndarray:
    """Every bit deviates from its label by d (row's puzzle, seed): Brier per cell = d^2."""
    return np.where(y >= 0.5, 1.0 - d_rows[:, None], d_rows[:, None]).astype(np.float32)


def _budget(n_params: int) -> list[dict]:
    return [{"wd": wd, "lr": lr, "seed": s, "best_epoch": 5, "epochs_run": 80, "n_steps": 2000, "hit_cap": False,
             "n_params": n_params, "selected": (wd, lr) == (0.1, 0.001)} for wd, lr in GRID for s in SEEDS]


def _e3(out: Path, score: dict, theta1_shift: float, role: str) -> tuple[dict, dict]:
    n = len(score["ids"])
    empty = score["empty"]
    pz, _ = np.nonzero(empty)
    y = score["mask"][empty].astype(np.float64)
    y_unit = unit_digit_labels(score["puzzles"]).reshape(-1, 9).astype(np.float64)
    pz_unit = np.repeat(np.arange(n), 27)
    jitter = np.random.default_rng(3).uniform(0.0, 0.01, (len(SEEDS), n))
    stages, files, budget = {}, {}, {}
    for stage, fits in STAGE_FITS.items():
        stages[stage], files[stage], budget[stage] = {}, {}, {}
        for fit in fits:
            if fit == "n2000":
                src = "pc_L06.linear" if stage == "training_size" else "wl_L06.generated"
                s_stage, s_fit = src.split(".")
                stages[stage][fit] = {**stages[s_stage][s_fit], "n_puzzles": 2000, "reused": True,
                                      "reused_from": src, "rows": "reused"}
                files[stage][fit] = dict(files[s_stage][s_fit])
                continue
            unit = stage == "unit_digit"
            yy, pp = (y_unit, pz_unit) if unit else (y, pz)
            path = out / "preds" / f"{stage}__{fit}.npz"
            if fit in ("rule", "marginal"):
                mean = (yy if fit == "rule" else np.full_like(yy, 0.3)).astype(np.float32)
                wp2.atomic_npz(path, mean=mean)
                per = brier_per_puzzle(mean, yy, pp, n)
                summary = {"config": None, "val_brier_mean": float(np.nanmean(per)), "per_puzzle": per.tolist(),
                           "budget": None}
            else:
                b = _base_brier(stage, fit, theta1_shift)
                seeds = [_seed_preds(yy, np.sqrt(b + jitter[s])[pp]) for s in range(len(SEEDS))]
                wp2.atomic_npz(path, **{f"seed{s}": p for s, p in zip(SEEDS, seeds)},
                               mean=np.mean(seeds, axis=0).astype(np.float32))
                per = np.mean([brier_per_puzzle(p, yy, pp, n) for p in seeds], axis=0)
                n_params = 22217 if fit.endswith("mlp") else 3042
                summary = {"config": [0.1, 0.001], "val_brier_mean": float(np.nanmean(per)),
                           "tune_brier_mean": float(np.nanmean(per)), "per_puzzle": per.tolist(),
                           "budget": {"n_params": n_params, "selected": [], "any_hit_cap": False}}
                budget[stage][fit] = _budget(n_params)
            if stage in ("training_size", "wl_training_size"):
                summary.update(n_puzzles=int(fit[1:]), reused=False)
            stages[stage][fit] = {**summary, "n_score": n, "rows": "unit" if unit else "cell",
                                  "construction": _construction(stage, fit)}
            files[stage][fit] = {f"preds/{path.name}": wp2.file_sha256(path)}
    note = wp2.DRY_NOTE if role == "dry" else "TEST"
    fits_json = {"note": note, "role": role, "n_score": n, "score_ids": score["ids"], "stages": stages,
                 "files": files}
    return fits_json, {"note": note, "role": role, **budget}


def _prelock(root: Path) -> None:
    d = root / "experiments" / "e3prep"
    cfg = {"config": [0.1, 0.001]}
    probes = {"stages": {"L02_linear": cfg, "L02_mlp": cfg, "L02_permuted_linear": cfg, "L06_linear": cfg,
                         "L06_mlp": {"config": [0.1, 0.003]}, "L12_linear": {"config": [0, 0.003]}, "L12_mlp": cfg,
                         "L12_permuted_linear": cfg,
                         "controls": {f: (dict(cfg) if f not in ("rule", "marginal") else {"config": None})
                                      for f in CONTROL_CONSTRUCTION},
                         "unit_digit": {"generated": cfg, "raw": cfg},
                         "training_size": {str(k): cfg for k in (125, 250, 500, 1000, 2000)}}}
    wholelayer = {"stages": {"L06": {"generated_linear": cfg, "permuted_linear": cfg},
                             "L12": {"generated_linear": cfg, "permuted_linear": cfg},
                             "teacher_L12": {"teacher_linear": cfg}, "raw_projected": {"linear": cfg},
                             "raw_unprojected": {"linear": cfg}}}
    wp2.atomic_json(d / "probes.json", probes)
    wp2.atomic_json(d / "wholelayer.json", wholelayer)


# --- role -------------------------------------------------------------------------------------

def write_role(root: Path, role: str, n: int = 40, theta2: float = -0.10, theta1_shift: float = 0.003,
               n_score: int | None = None, identity_failure: bool = False) -> SimpleNamespace:
    """Writes every raw input of `scripts/wp2_evaluate.py` for `role` under `root` (see module doc)."""
    root = Path(root)
    exp, raw = root / "experiments" / "wp2" / role, root / "runs" / "wp2" / role
    recs = exp / "runs"
    n_score = n + 7 if n_score is None else n_score
    note = wp2.DRY_NOTE if role == "dry" else None

    e2_ids = [f"e2-{i}" for i in range(n)]
    e2_puzzles = _puzzles(n, 11)
    wp2.atomic_json(raw / "e1.json", {"role": role, "ids": e2_ids, "note": note, "records": _e1_records(e2_ids),
                                      "batch_size": 50}, indent=None)
    wp2.atomic_json(recs / "e1.json", record("e1", role, n=n, outputs=wp2.manifest({"e1.json": raw / "e1.json"})))

    out, diags = _e2(e2_ids, theta2, identity_failure)
    diag_files = {}
    for key, arrays in diags.items():
        p = raw / "e2" / "diag" / f"{key.replace('/', '__')}.npz"
        wp2.atomic_npz(p, **arrays)
        diag_files[key] = {"file": p.name, "sha256": wp2.file_sha256(p)}
    wp2.atomic_json(raw / "e2.json", {**out, "role": role, "ids": e2_ids, "note": note, "diag_files": diag_files},
                    indent=None)
    e2_extra = {"outputs": wp2.manifest({"e2.json": raw / "e2.json"}), "code_mismatch": out["code_mismatch"]}
    if identity_failure:
        e2_extra.update(valid=False, invalid_reasons=["identity-failure"], status="identity-failure")
    wp2.atomic_json(recs / "e2.json", record("e2", role, **e2_extra))

    score_dir = raw / "e3data" / "score"
    score_ids = [f"score-{i}" for i in range(n_score)]
    score_puzzles = _puzzles(n_score, 5)
    lab = labels(score_puzzles)
    wp2.atomic_write(score_dir / "ids.json", json.dumps(score_ids))
    arrays = {"puzzles": score_puzzles, "mask": lab["mask"], "empty": lab["empty"], "depth": lab["depth"]}
    for name, a in arrays.items():
        wp2.atomic_npy(score_dir / f"{name}.npy", a)
    score_manifest = wp2.manifest({p.name: p for p in sorted(score_dir.iterdir())})
    wp2.atomic_json(recs / "e3_extract.json", record("e3_extract", role, n=n_score, score_manifest=score_manifest))

    fits, budget = _e3(raw / "e3", {"ids": score_ids, **arrays}, theta1_shift, role)
    wp2.atomic_json(exp / "e3_fits.json", fits)
    wp2.atomic_json(exp / "e3_budget.json", budget)
    wp2.atomic_json(recs / "e3.json", record("e3", role, n=n_score, outputs=wp2.manifest(
        {"e3_fits.json": exp / "e3_fits.json", "e3_budget.json": exp / "e3_budget.json"})))

    kinds = ("all", "digit", "geometric")
    equiv = {"note": note, "non_confirmatory": True, "role": role, "level": 12, "n": 20, "k": 4,
             "acceptable": 0.0116, "acceptable_source": "fixed", "seed_noise_p95": 0.012,
             "share_within": {k: 0.0 for k in kinds}, "mean_deviation": {"all": 0.079, "digit": 0.066,
                                                                         "geometric": 0.077},
             "mean_brier": {k: 0.1828 for k in kinds}, "mean_brier_original": 0.1828}
    wp2.atomic_json(exp / "equivariance.json", equiv)
    wp2.atomic_json(recs / "equiv.json", record("equiv", role, n=20, outputs=wp2.manifest(
        {"equivariance.json": exp / "equivariance.json"})))

    _prelock(root)
    return SimpleNamespace(root=root, exp=exp, raw=raw, records=recs, e2_ids=e2_ids, e2_puzzles=e2_puzzles,
                           score_ids=score_ids, score_dir=score_dir, n=n, n_score=n_score)
