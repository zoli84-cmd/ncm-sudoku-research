"""WP2 E3 confirmatory runner (plan v3.7 §8.1-§8.3, §10, §12.2; D63, D64, D67, D76; WP2 plan spec
ambiguities 17, 21, 24).

Usage: uv run --locked python scripts/wp2_e3.py --role test|dry [--force | --resume]

Runs every stage of `wp2e3.STAGES` once: trained on PROBE-TRAIN, selected on PROBE-VAL (both from
`runs/e3prep/`, reused unchanged) and scored on the role's score set `runs/wp2/<role>/e3data/score/`
(TEST, or PROBE-VAL in the dry role), written by `scripts/wp2_e3_extract.py`. `KW` holds budget
overrides for tests only; the real run uses the D63 defaults (full budgets).

Order: preconditions (PROBE-TRAIN has `N_TRAIN` ids; PROBE-VAL ids equal `probes.json` and
`wholelayer.json` `val_ids`; a complete and valid `e3_extract` record whose `score_manifest` matches
the score directory; TEST: score ids and puzzles SHA-256 equal §12.2; the `INPUT_FILES` manifest,
and in the TEST role its PROBE entries equal the approved dry run's `probe_inputs` in `DRY_CHECK`;
`--resume`: stored inputs and environment equal the current ones, naming the first difference) ->
`wp2.guard_start` (inputs: the manifest) -> fresh start: `clear_outputs` then `mark_outputs_started`;
`--resume`: `rec = prepare_resume_outputs(...)` then the stage check below -> remaining stages, one at
a time -> `e3_fits.json` and `e3_budget.json` assembled from the re-verified checkpoints -> `finish_run`.

Per-stage publication, each step atomic: (1) artifacts (`wp2e3.save_stage`: `preds/`, `models/`);
(2) checkpoint `stages/<stage>.json` (`stage`, `summary`, `budget`, `files` = `save_stage`'s return
value, `in_dims`, `seconds`, `stage_environment`); (3) marker `stages/<stage>.done.json`
(`{"stage", "checkpoint_sha256"}`). A stage is done only if its marker exists, the checkpoint's
SHA-256 equals the marker's digest and every artifact in `files` matches. No marker: the stage's
checkpoint and artifacts (`<stage>__*`) are deleted and it reruns. Marker present but the checkpoint
digest or an artifact SHA-256 differs: `SystemExit` naming the file. A missing artifact removes the
marker and checkpoint and reruns the stage. Once a stage is discarded on resume, every later stage
in `STAGES` order is discarded and rerun too (later stages may read its artifacts, e.g.
`wl_L06_controls` the saved wl_L06 PCA). Dry-role checkpoints carry `note` = `wp2.DRY_NOTE`. `stored` (passed to later stages) is built only from
verified checkpoints (JSON round trip).

Outputs: `experiments/wp2/<role>/e3_fits.json` (note, role, date, n_train, n_val, n_score,
score_ids, inputs, environment, budget_overrides, stages (per-stage summary), files, stage_digests,
seconds, stage_environment) and `e3_budget.json` (per stage and trained fit the 30-entry
`budget_table`), both written only at the end; raw under `runs/wp2/<role>/e3/{preds,models,stages}/`.
Run record `experiments/wp2/<role>/runs/e3.json`: technical fields only (`n_stages`, `fits_sha256`,
`budget_sha256`, `stage_digests`, `outputs`, `n`); stdout is `wp2.status_line` only (D76(5)).
"""

import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

from ncm_sudoku import wp2, wp2e3
from ncm_sudoku.subsets import sha256_array, sha256_ids

RUNNER = "e3"
EXTRACT_RUNNER = "e3_extract"
N_TRAIN = 2000
INPUT_FILES = ("ids.json", "puzzles.npy", "mask.npy", "empty.npy", "depth.npy", "L02.npy", "L06.npy", "L12.npy",
               "T02.npy", "T06.npy", "T12.npy")
SUBSETS = ("probe_train", "probe_val", "score")
KW: dict = {}
TEST_NOTE = "WP2 E3 confirmatory fits on TEST (plan v3.7 §8); read only after all TEST runs are complete"


def _probe_runs() -> Path:
    return wp2.ROOT / "runs" / "e3prep"


def _layout(role: str) -> dict:
    exp, raw = wp2.paths(role)
    out = raw / "e3"
    return {"exp": exp, "score_root": raw / "e3data", "score": raw / "e3data" / "score", "out": out,
            "stages": out / "stages", "fits": exp / "e3_fits.json", "budget": exp / "e3_budget.json"}


def _read(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _subset_dir(L: dict, subset: str) -> Path:
    return L["score"] if subset == "score" else _probe_runs() / subset


# --- preconditions --------------------------------------------------------------------------------

def _check_probe_ids() -> None:
    runs = _probe_runs()
    train = _read(runs / "probe_train" / "ids.json")
    if len(train) != N_TRAIN:
        sys.exit(f"{RUNNER}: PROBE-TRAIN has {len(train)} ids, expected {N_TRAIN}")
    val = _read(runs / "probe_val" / "ids.json")
    for name in ("probes.json", "wholelayer.json"):
        p = wp2.ROOT / "experiments" / "e3prep" / name
        if not p.is_file() or _read(p).get("val_ids") != val:
            sys.exit(f"{RUNNER}: PROBE-VAL ids differ from experiments/e3prep/{name} val_ids (or it is missing)")


def _check_extract(role: str, L: dict) -> None:
    path = wp2.paths(role)[0] / "runs" / f"{EXTRACT_RUNNER}.json"
    if not path.is_file():
        sys.exit(f"{RUNNER}: no {EXTRACT_RUNNER} run record at {path}; run scripts/wp2_e3_extract.py first")
    rec = _read(path)
    if rec.get("complete") is not True or rec.get("valid") is not True:
        sys.exit(f"{RUNNER}: the {EXTRACT_RUNNER} run record is not complete and valid")
    expected = rec.get("score_manifest")
    if not isinstance(expected, dict):
        sys.exit(f"{RUNNER}: the {EXTRACT_RUNNER} run record has no score_manifest")
    missing = [f for f in INPUT_FILES if f not in expected]
    if missing:
        sys.exit(f"{RUNNER}: score/{missing[0]} is not in the {EXTRACT_RUNNER} score_manifest")
    try:
        wp2.check_manifest({f"score/{n}": L["score"] / n for n in expected},
                           {f"score/{n}": sha for n, sha in expected.items()})
    except wp2.DataIntegrityError as e:
        sys.exit(f"{RUNNER}: score set does not match the {EXTRACT_RUNNER} score_manifest: {e}")


def _check_test_score(L: dict) -> None:
    ids = _read(L["score"] / "ids.json")
    puzzles = np.load(L["score"] / "puzzles.npy", allow_pickle=False)
    if sha256_ids(ids) != wp2.TEST_SHA256["ids"] or sha256_array(puzzles) != wp2.TEST_SHA256["puzzles"]:
        sys.exit(f"{RUNNER}: the score set's ids or puzzles SHA-256 differ from the §12.2 TEST values")


def input_manifest(L: dict) -> dict:
    """`files`: SHA-256 per `<subset>/<file>`; `arrays`: shape and dtype per array file; plus the
    budget overrides, K and SIZES the stages use (a resume must see the same)."""
    files, arrays = {}, {}
    for subset in SUBSETS:
        d = _subset_dir(L, subset)
        for name in INPUT_FILES:
            key, p = f"{subset}/{name}", d / name
            if not p.is_file():
                sys.exit(f"{RUNNER}: input {key} ({p}) is missing")
            files[key] = wp2.file_sha256(p)
            if name.endswith(".npy"):
                a = np.load(p, mmap_mode="r", allow_pickle=False)
                arrays[key] = {"shape": list(a.shape), "dtype": str(a.dtype)}
                del a
    return {"files": files, "arrays": arrays, "budget_overrides": json.loads(json.dumps(KW)), "k": wp2e3.K,
            "sizes": list(wp2e3.SIZES)}


def _check_probe_snapshot(inputs: dict) -> None:
    """TEST role: the PROBE entries must equal the approved dry run's `probe_inputs` (ROOT-relative
    POSIX keys, SHA-256 only)."""
    if not wp2.DRY_CHECK.is_file():
        sys.exit(f"{RUNNER}: dry check {wp2.DRY_CHECK} missing")
    snap = ((_read(wp2.DRY_CHECK).get("snapshot") or {}).get("probe_inputs")) or {}
    base = _probe_runs().relative_to(wp2.ROOT).as_posix()
    for key, sha in inputs["files"].items():
        if key.split("/")[0] not in ("probe_train", "probe_val"):
            continue
        rel = f"{base}/{key}"
        if rel not in snap:
            sys.exit(f"{RUNNER}: {rel} is not in the approved dry run's probe_inputs")
        if snap[rel] != sha:
            sys.exit(f"{RUNNER}: {rel} differs from the approved dry run's probe_inputs")


def _check_resume_inputs(role: str, inputs: dict) -> None:
    """Names the first input file or environment field that differs from the stored run."""
    path = wp2.paths(role)[0] / "runs" / f"{RUNNER}.json"
    if not path.is_file():
        return  # guard_start refuses the resume
    stored = _read(path)
    old = stored.get("inputs") or {}
    for group in ("files", "arrays"):
        a, b = old.get(group) or {}, inputs[group]
        for key in [*b, *(k for k in a if k not in b)]:
            if a.get(key) != b.get(key):
                sys.exit(f"{RUNNER}: --resume refused: input {key} differs from the stored run ({group})")
    for key in inputs:
        if old.get(key) != inputs[key]:
            sys.exit(f"{RUNNER}: --resume refused: input field {key} differs from the stored run")
    env_old, env_new = stored.get("environment") or {}, json.loads(json.dumps(wp2.environment_record()))
    for key in [*env_new, *(k for k in env_old if k not in env_new)]:
        if env_old.get(key) != env_new.get(key):
            sys.exit(f"{RUNNER}: --resume refused: environment field {key} differs from the stored run")


# --- stage checkpoints ----------------------------------------------------------------------------

def _paths(L: dict, stage: str) -> tuple[Path, Path]:
    return L["stages"] / f"{stage}.json", L["stages"] / f"{stage}.done.json"


def _discard_stage(L: dict, stage: str) -> None:
    """A stage's own partial state (this run's; the outputs_started marker is confirmed)."""
    for p in _paths(L, stage):
        p.unlink(missing_ok=True)
    for sub in ("preds", "models"):
        d = L["out"] / sub
        if d.is_dir():
            for p in d.glob(f"{stage}__*"):
                p.unlink()


def _verify_stage(L: dict, stage: str) -> dict | None:
    """The stage's checkpoint if it is done; None if it must be (re)computed (missing marker or a
    missing artifact). Exits naming the file on a digest or artifact mismatch."""
    ck_path, done_path = _paths(L, stage)
    if not done_path.is_file():
        return None
    done = _read(done_path)
    rel = f"stages/{ck_path.name}"
    if done.get("stage") != stage:
        sys.exit(f"{RUNNER}: stages/{done_path.name} names stage {done.get('stage')!r}")
    if not ck_path.is_file() or wp2.file_sha256(ck_path) != done.get("checkpoint_sha256"):
        sys.exit(f"{RUNNER}: {rel} is missing or differs from its completion marker's digest")
    ck = _read(ck_path)
    if ck.get("stage") != stage:
        sys.exit(f"{RUNNER}: {rel} holds stage {ck.get('stage')!r}")
    for fit, files in ck["files"].items():
        for name, sha in files.items():
            p = L["out"] / name
            if not p.is_file():
                return None
            if wp2.file_sha256(p) != sha:
                sys.exit(f"{RUNNER}: {name} (stage {stage}, fit {fit}) differs from its recorded SHA-256")
    return ck


def _stored(ck: dict) -> dict:
    return {"summary": ck["summary"], "files": ck["files"], "in_dims": ck["in_dims"]}


def _publish(L: dict, role: str, stage: str, res: dict, seconds: float) -> dict:
    files = wp2e3.save_stage(L["out"], stage, res)
    ck_path, done_path = _paths(L, stage)
    ck = {"stage": stage, **({"note": wp2.DRY_NOTE} if role == "dry" else {}), "summary": res["summary"], "budget": res["budget"], "files": files,
          "in_dims": res["in_dims"], "seconds": seconds,
          "stage_environment": {"date": time.strftime("%Y-%m-%d"), "environment": wp2.environment_record(),
                                "code": wp2.code_state()}}
    wp2.atomic_json(ck_path, ck)
    wp2.atomic_json(done_path, {"stage": stage, "checkpoint_sha256": wp2.file_sha256(ck_path)})
    return _read(ck_path)


# --- run ------------------------------------------------------------------------------------------

def run(argv: list[str] | None = None) -> int:
    args = wp2.parse_args(sys.argv[1:] if argv is None else argv)
    role = args.role
    t_start = time.perf_counter()
    L = _layout(role)
    _check_probe_ids()
    _check_extract(role, L)
    if role == "test":
        _check_test_score(L)
    inputs = input_manifest(L)
    if role == "test":
        _check_probe_snapshot(inputs)
    if args.resume:
        torch.use_deterministic_algorithms(True)  # before environment_record()
        _check_resume_inputs(role, inputs)
    rec = wp2.guard_start(RUNNER, role, args.force, args.resume, inputs)
    targets = [L["fits"], L["budget"], L["out"]]
    if args.resume:
        rec = wp2.prepare_resume_outputs(RUNNER, role, rec, targets)
    else:
        wp2.clear_outputs(RUNNER, role, targets)
        rec = wp2.mark_outputs_started(RUNNER, role)

    stages = list(wp2e3.STAGES)
    checkpoints, cascade = {}, False
    for name, _ in stages:  # validate every stored stage before any fit
        ck = _verify_stage(L, name) if args.resume and not cascade else None
        if ck is None:  # this stage and every later one rerun (later stages may read its artifacts)
            cascade = True
            _discard_stage(L, name)
        else:
            checkpoints[name] = ck

    sets = wp2e3.load_sets(_probe_runs(), L["score_root"], L["out"])
    n_train, n_val, n_score = len(sets.train["ids"]), len(sets.val["ids"]), len(sets.score["ids"])
    score_ids = list(sets.score["ids"])
    stored = {name: _stored(ck) for name, ck in checkpoints.items()}
    for name, fn in stages:
        if name in checkpoints:
            continue
        t0 = time.perf_counter()
        res = fn(sets, KW, stored)
        seconds = time.perf_counter() - t0
        ck = _publish(L, role, name, res, seconds)
        stored[name] = _stored(ck)
        wp2.status_line(runner=RUNNER, role=role, stage=name, seconds=round(seconds, 1))
        del res, ck
        gc.collect()
    del sets
    gc.collect()

    final = {}
    for name, _ in stages:  # re-verify every checkpoint; the final files come only from them
        ck = _verify_stage(L, name)
        if ck is None:
            raise wp2.DataIntegrityError(f"{RUNNER}: stage {name} has no complete checkpoint at the end of the run")
        final[name] = (ck, _read(_paths(L, name)[1])["checkpoint_sha256"])
    digests = {n: d for n, (_, d) in final.items()}
    note = wp2.DRY_NOTE if role == "dry" else TEST_NOTE
    fits = {"note": note, "role": role, "date": time.strftime("%Y-%m-%d"), "n_train": n_train, "n_val": n_val,
            "n_score": n_score, "score_ids": score_ids, "inputs": rec["inputs"], "environment": rec["environment"],
            "budget_overrides": json.loads(json.dumps(KW)),
            "stages": {n: ck["summary"] for n, (ck, _) in final.items()},
            "files": {n: ck["files"] for n, (ck, _) in final.items()}, "stage_digests": digests,
            "seconds": {n: ck["seconds"] for n, (ck, _) in final.items()},
            "stage_environment": {n: ck["stage_environment"] for n, (ck, _) in final.items()}}
    budget = {"note": note, "role": role, **{n: ck["budget"] for n, (ck, _) in final.items()}}
    wp2.atomic_json(L["fits"], fits)
    wp2.atomic_json(L["budget"], budget)
    fits_sha, budget_sha = wp2.file_sha256(L["fits"]), wp2.file_sha256(L["budget"])

    seconds = time.perf_counter() - t_start
    extra = {"n": n_score, "n_stages": len(stages), "fits_sha256": fits_sha, "budget_sha256": budget_sha,
             "stage_digests": digests, "outputs": {"e3_fits.json": fits_sha, "e3_budget.json": budget_sha}}
    done = wp2.finish_run(RUNNER, role, rec, seconds, extra)
    wp2.status_line(runner=RUNNER, role=role, complete=done["complete"], valid=done["valid"],
                    status=done["status"], seconds=round(seconds, 1), n=n_score)
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
