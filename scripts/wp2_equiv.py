"""WP2 exploratory level-12 whole-layer equivariance runner (plan v3.7 §8.4, §12.2, §13; D59,
D76; WP2 plan spec ambiguities 6, 7, 21, 24).

Usage: uv run --locked python scripts/wp2_equiv.py --role test|dry [--force | --resume]

Runs `e3equiv.equivariance_pilot` once on the role's score set (TEST, or the PROBE-VAL score set
in the dry role; `scripts/wp2_e3_extract.py`), on the first `N_EQUIV` score ids in generation
order, with the fixed tolerance `ACCEPTABLE` = 0.0116 (spec ambiguity 6: the value measured before
the lock is 0.011644554557515473; the TEST `seed_noise_p95` is reported alongside, never used as
the tolerance). The predictor is the level-12 whole-layer probe `wl_L12__generated` saved by
`scripts/wp2_e3.py` (`wp2e3.load_probe`), one seed model per predictor, sharing one cache and one
`features` object (`wholelayer.whole_layer_features` with the saved PCA), exactly as
`scripts/lock_equiv_l12.py`'s `main` does.

Spec ambiguity 7: the reading is descriptive only (mean deviation, share within the fixed
tolerance, transformed vs. untransformed Brier per kind); this runner selects no §13 row. Spec
ambiguity 21: this runner is short and keeps no partial stage state, so `--resume` restarts
cleanly after the guard's input, code and environment checks pass, like `scripts/wp2_e1.py`.

Preconditions, checked before `wp2.guard_start` (so a failed precondition never leaves a
half-written run record): a complete and valid `e3` run record for the role whose `fits_sha256`
equals the current `e3_fits.json`; the `wl_L12__generated` model, PCA and json files on disk match
the `e3_fits.json` `files` manifest; the score set's `L12.npy`, `puzzles.npy`, `mask.npy` and
`empty.npy` match the `e3_extract` run record's `score_manifest` (TEST role: the score ids and
puzzles SHA-256 are also re-verified against §12.2).

A fresh start marks the record with `wp2.mark_outputs_started` right after `clear_outputs`
succeeds, before `equivariance.json` is written; `--resume` reassigns
`rec = wp2.prepare_resume_outputs(...)` first, for the reasons `wp2_e1.py` documents (a fresh TEST
start refused over an unrecorded leftover `equivariance.json` must not let a later `--resume`
treat that leftover as this run's own partial state); the atomic write then simply replaces
`equivariance.json` in place, recomputed from scratch, on both a fresh start and a resume.

Outputs: `experiments/wp2/<role>/equivariance.json` (the fields of
`experiments/lock/equivariance_l12.json`, plus `acceptable_source`, `seed_noise_p95`, `role`,
`probe` (config and files of `wl_L12__generated`) and `ids`, the first `N_EQUIV` score ids). Run
record `experiments/wp2/<role>/runs/equiv.json`: technical fields only (`n`,
`probe_files_sha256`, `outputs` = SHA-256 of `equivariance.json`); no outcome metric (deviation,
share within tolerance, Brier) is printed or written to the run record (D76(5)); that is read only
from `equivariance.json`, after all TEST runs are complete.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np

from ncm_sudoku import wp2, wp2e3
from ncm_sudoku.e3equiv import N_SUBSET, equivariance_pilot, model_predict_fn
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.subsets import sha256_array, sha256_ids
from ncm_sudoku.wholelayer import whole_layer_features

RUNNER = "equiv"
CKPT_DIR = ROOT / "checkpoints" / "sudoku" / "hard"
LEVEL = 12
N_EQUIV = 200
K_ELEMENTS = 4
SEED = 0
ACCEPTABLE = 0.0116  # spec ambiguity 6: fixed, not the measured pre-lock value
SCORE_FILES = ("L12.npy", "puzzles.npy", "mask.npy", "empty.npy")
TEST_NOTE = ("exploratory, non-confirmatory (plan v3.7 §8.4, §13; D59, spec ambiguities 6, 7): "
             "level-12 whole-layer equivariance on TEST, read only after all TEST runs are complete")


def _layout(role: str) -> dict:
    exp, raw = wp2.paths(role)
    return {"out": raw / "e3", "score": raw / "e3data" / "score", "equiv": exp / "equivariance.json",
            "e3_fits": exp / "e3_fits.json", "e3_record": exp / "runs" / "e3.json",
            "extract_record": exp / "runs" / "e3_extract.json"}


def _read(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _check_e3_record(L: dict) -> dict:
    if not L["e3_record"].is_file():
        sys.exit(f"{RUNNER}: no e3 run record at {L['e3_record']}; run scripts/wp2_e3.py first")
    rec = _read(L["e3_record"])
    if rec.get("complete") is not True or rec.get("valid") is not True:
        sys.exit(f"{RUNNER}: the e3 run record is not complete and valid")
    if not L["e3_fits"].is_file():
        sys.exit(f"{RUNNER}: {L['e3_fits']} missing")
    if rec.get("fits_sha256") != wp2.file_sha256(L["e3_fits"]):
        sys.exit(f"{RUNNER}: the e3 run record's fits_sha256 differs from the current e3_fits.json")
    return rec


def _check_probe_files(L: dict, fits: dict) -> dict:
    manifest = (fits.get("files") or {}).get("wl_L12", {}).get("generated")
    if not isinstance(manifest, dict):
        sys.exit(f"{RUNNER}: e3_fits.json has no files for wl_L12/generated")
    try:
        wp2.check_manifest({name: L["out"] / name for name in manifest}, manifest)
    except wp2.DataIntegrityError as e:
        sys.exit(f"{RUNNER}: {e}")
    return manifest


def _check_score(role: str, L: dict) -> None:
    if not L["extract_record"].is_file():
        sys.exit(f"{RUNNER}: no e3_extract run record at {L['extract_record']}; "
                 "run scripts/wp2_e3_extract.py first")
    rec = _read(L["extract_record"])
    if rec.get("complete") is not True or rec.get("valid") is not True:
        sys.exit(f"{RUNNER}: the e3_extract run record is not complete and valid")
    expected = rec.get("score_manifest")
    if not isinstance(expected, dict):
        sys.exit(f"{RUNNER}: the e3_extract run record has no score_manifest")
    missing = [n for n in SCORE_FILES if n not in expected]
    if missing:
        sys.exit(f"{RUNNER}: score/{missing[0]} is not in the e3_extract score_manifest")
    try:
        wp2.check_manifest({n: L["score"] / n for n in SCORE_FILES}, {n: expected[n] for n in SCORE_FILES})
    except wp2.DataIntegrityError as e:
        sys.exit(f"{RUNNER}: {e}")
    if role == "test":
        ids = _read(L["score"] / "ids.json")
        puzzles = np.load(L["score"] / "puzzles.npy", allow_pickle=False)
        if sha256_ids(ids) != wp2.TEST_SHA256["ids"] or sha256_array(puzzles) != wp2.TEST_SHA256["puzzles"]:
            sys.exit(f"{RUNNER}: the score set's ids or puzzles SHA-256 differ from the §12.2 TEST values")


def run(argv: list[str] | None = None) -> int:
    args = wp2.parse_args(sys.argv[1:] if argv is None else argv)
    role = args.role
    t_start = time.perf_counter()
    L = _layout(role)
    e3_rec = _check_e3_record(L)
    fits = _read(L["e3_fits"])
    probe_manifest = _check_probe_files(L, fits)
    _check_score(role, L)
    wp2.verify_checkpoints(CKPT_DIR)

    inputs = {"n_equiv": N_EQUIV, "k_elements": K_ELEMENTS, "seed": SEED, "acceptable": ACCEPTABLE,
              "fits_sha256": e3_rec["fits_sha256"], "probe_files_sha256": probe_manifest,
              "score_sha256": {n: wp2.file_sha256(L["score"] / n) for n in SCORE_FILES}}
    rec = wp2.guard_start(RUNNER, role, args.force, args.resume, inputs)
    if args.resume:
        rec = wp2.prepare_resume_outputs(RUNNER, role, rec, [L["equiv"]])
    else:
        wp2.clear_outputs(RUNNER, role, [L["equiv"]])
        rec = wp2.mark_outputs_started(RUNNER, role)

    probes, pca, meta = wp2e3.load_probe(L["out"], "wl_L12", "generated")
    m = load_model(CKPT_DIR)
    ids = _read(L["score"] / "ids.json")
    puzzles = np.load(L["score"] / "puzzles.npy", allow_pickle=False)

    feats = lambda s: whole_layer_features(s, pca)  # noqa: E731  one object: the shared cache keys on it
    cache: dict = {}
    predict_fns = [model_predict_fn(m, p, cache, level=LEVEL, features=feats) for p in probes]
    t0 = time.perf_counter()
    r = equivariance_pilot(puzzles, predict_fns, n=N_EQUIV, k=K_ELEMENTS, seed=SEED, acceptable=ACCEPTABLE)
    seconds_equiv = round(time.perf_counter() - t0, 1)

    out = {
        "note": wp2.DRY_NOTE if role == "dry" else TEST_NOTE, "non_confirmatory": True,
        "date": time.strftime("%Y-%m-%d"), "role": role, "environment": rec["environment"], "code": rec["code"],
        "level": LEVEL, "probe": {"config": meta.get("config"), "files": probe_manifest}, "ids": ids[: r["n"]],
        **{k: r[k] for k in ("n", "k", "seed", "n_predictors", "acceptable", "acceptable_source",
                             "seed_noise_p95", "share_within", "mean_deviation", "mean_brier",
                             "mean_brier_original")},
        "elements_per_puzzle": {"all": r["k"], "digit": N_SUBSET, "geometric": N_SUBSET},
        "deviation": {k: np.asarray(v).tolist() for k, v in r["deviation"].items()},
        "seed_noise": np.asarray(r["seed_noise"]).tolist(),
        "brier": {k: np.asarray(v).tolist() for k, v in r["brier"].items()},
        "brier_original": np.asarray(r["brier_original"]).tolist(),
        "seconds": {"equivariance": seconds_equiv},
    }
    wp2.atomic_json(L["equiv"], out)

    seconds = time.perf_counter() - t_start
    extra = {"n": r["n"], "probe_files_sha256": probe_manifest,
             "outputs": wp2.manifest({"equivariance.json": L["equiv"]})}
    final = wp2.finish_run(RUNNER, role, rec, seconds, extra)
    wp2.status_line(runner=RUNNER, role=role, complete=final["complete"], valid=final["valid"],
                    status=final["status"], seconds=round(seconds, 1), n=extra["n"])
    return 0


def main(argv: list[str] | None = None) -> None:
    try:
        code = run(argv)
    except wp2.DataIntegrityError as e:
        sys.exit(f"{RUNNER}: {e}")
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
