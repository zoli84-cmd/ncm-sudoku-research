"""WP2 E3 score-set extraction (plan v3.7 §8.1, §10, §12.2; D76; WP2 plan spec ambiguity 21).

Usage: uv run --locked python scripts/wp2_e3_extract.py --role test|dry [--force | --resume]

Generates and extracts, once, the per-level representations, logical labels and masks for the
role's E3 score set: TEST (600 puzzles, `wp2.verify_test_data`) or, in the dry role, PROBE-VAL
(the 500 puzzles already extracted to `runs/e3prep/probe_val/` for the non-confirmatory E3
preparation; its ids must equal `experiments/e3prep/probes.json` `val_ids`).

Order: score-set data (TEST verified first) -> labels.py SHA-256 (§12.2) -> checkpoint hashes ->
`wp2.guard_start` -> discard `e3data/score.tmp/` and `e3data/score/` -> `load_model` ->
`e3data.labels` -> `e3data.extract_streamed(batch=50)` straight into `score.tmp/` ->
`e3data.save_subset` into `score.tmp/` (adds ids/puzzles/solutions/solve/mask/empty/depth;
L*/T* already written) -> `score.tmp/ids.json` rewritten with `wp2.atomic_write` (LF; `save_subset`
writes it without `newline="\\n"`) -> the 22-file manifest is computed from `score.tmp/` -> the
directory is renamed to `score/` only once every file is written -> (dry only) `compare_dirs`
against the reference `runs/e3prep/probe_val/` -> `finish_run` -> `status_line`.

`score.tmp/` and `score/` are restart-from-scratch state (spec ambiguity 21), like `wp2_e1.py`:
on a fresh start they are cleared through `wp2.clear_outputs` (refuses if either already exists
in the TEST role: single-look), and the record is then marked with `wp2.mark_outputs_started`,
before any output is written. On `--resume`, `rec = wp2.prepare_resume_outputs(...)` checks that
marker first: `guard_start` writes the (incomplete) run record before a fresh start's
`clear_outputs` call, so a refused fresh TEST start over unrecorded leftovers (e.g. a complete
prior run whose record was separately lost, say to `git clean`) still leaves an incomplete,
markerless record behind, and `--resume` must not read that leftover as this run's own partial
state. Without the marker but also without `score.tmp/`/`score/` existing yet (a crash between
`clear_outputs` succeeding and `mark_outputs_started` running, in this very run's own earlier
attempt), the gate marks the record itself before returning, so a further crash after that resume
has written `score/` does not wedge every later `--resume`. Once the marker is confirmed, both
directories are discarded unconditionally (even in the TEST role, bypassing `clear_outputs`'s
"never deletes" rule) and the whole extraction restarts and republishes atomically — neither a
leftover `score.tmp/` nor a `score/` left by a crash between the rename and `finish_run` is ever
read as valid on its own.

Outputs (raw, git-ignored) under `runs/wp2/<role>/e3data/score/`: the PROBE layout (`ids.json`,
`puzzles.npy`, `solutions.npy`, `solve.npy`, `mask.npy`, `empty.npy`, `depth.npy`, `L01.npy` ..
`L12.npy`, `T02/T06/T12.npy`). Run record: `experiments/wp2/<role>/runs/e3_extract.json`
(technical fields only, plus `labels_sha256`, `n`, `score_manifest` (name -> SHA-256 of all 22
files; Task 9 checks it) and, dry only, `matches_e3prep` ({array: {equal, max_abs_diff}} from
`compare_dirs` against the reference PROBE-VAL extraction). No outcome metric (e.g. generated
solve share) is printed or written to the run record (D76(5)).
"""

import gc
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from ncm_sudoku import wp2
from ncm_sudoku.e3data import TEACHER_LEVELS, extract_streamed, labels, save_subset
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.subsets import sha256_array, sha256_ids

RUNNER = "e3_extract"
BATCH = 50
CKPT_DIR = ROOT / "checkpoints" / "sudoku" / "hard"
LABELS_PATH = ROOT / "src" / "ncm_sudoku" / "labels.py"
LABELS_SHA256 = "495f9d8b28bbd22dbdf1b4991935fa2ce23db607497bf9253eaf11abb8d517e6"  # plan §12.2
FILE_NAMES = (
    ["ids.json", "puzzles.npy", "solutions.npy", "solve.npy", "mask.npy", "empty.npy", "depth.npy"]
    + [f"L{lv:02d}.npy" for lv in range(1, 13)]
    + [f"T{lv:02d}.npy" for lv in TEACHER_LEVELS]
)  # 22 files
ARRAY_NAMES = [n for n in FILE_NAMES if n != "ids.json"]


def _layout(role: str) -> dict:
    raw = wp2.paths(role)[1]
    d = raw / "e3data"
    return {"raw": raw, "dir": d, "score": d / "score", "score_tmp": d / "score.tmp"}


def _probe_val_dir():
    return wp2.ROOT / "runs" / "e3prep" / "probe_val"


def _probes_json_path():
    return wp2.ROOT / "experiments" / "e3prep" / "probes.json"


def _probe_val_data() -> wp2.RoleData:
    """Dry-role score set: the 500 PROBE-VAL puzzles already extracted for E3 preparation, ids
    checked against `experiments/e3prep/probes.json` `val_ids`."""
    d = _probe_val_dir()
    try:
        probes = json.loads(_probes_json_path().read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise wp2.DataIntegrityError(f"probe_val: {e.filename} missing") from None
    try:
        ids = json.loads((d / "ids.json").read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise wp2.DataIntegrityError(f"probe_val: {e.filename} missing") from None
    if ids != probes.get("val_ids"):
        raise wp2.DataIntegrityError("probe_val: ids differ from experiments/e3prep/probes.json val_ids")
    puzzles = np.load(d / "puzzles.npy", allow_pickle=False)
    solutions = np.load(d / "solutions.npy", allow_pickle=False)
    return wp2.RoleData(ids=ids, puzzles=puzzles, solutions=solutions, source="probe_val")


def _score_data(role: str) -> wp2.RoleData:
    if role == "test":
        return wp2.verify_test_data()
    if role == "dry":
        return _probe_val_data()
    raise ValueError(f"unknown role {role!r}; expected one of {wp2.ROLES}")


def _check_labels_hash() -> str:
    actual = hashlib.sha256(LABELS_PATH.read_bytes()).hexdigest()
    if actual != LABELS_SHA256:
        sys.exit(f"{RUNNER}: labels.py SHA-256 {actual} differs from the locked §12.2 value {LABELS_SHA256}")
    return actual


def compare_dirs(a, b, names: list[str]) -> dict:
    """Compares named array files of two directories. Shapes must match; values are compared
    after casting both sides to float64 (so bool and uint8 arrays subtract without a TypeError);
    `max_abs_diff` is taken over the cast values. Keys are the file names without extension."""
    out = {}
    for name in names:
        x = np.load(Path(a) / name, allow_pickle=False)
        y = np.load(Path(b) / name, allow_pickle=False)
        if x.shape != y.shape:
            raise wp2.DataIntegrityError(f"compare_dirs: {name} shape {x.shape} != {y.shape}")
        xf, yf = x.astype(np.float64), y.astype(np.float64)
        diff = float(np.abs(xf - yf).max()) if xf.size else 0.0
        out[Path(name).stem] = {"equal": bool(np.array_equal(xf, yf)), "max_abs_diff": diff}
    return out


def run(argv: list[str] | None = None) -> int:
    args = wp2.parse_args(sys.argv[1:] if argv is None else argv)
    role = args.role
    t_start = time.perf_counter()
    data = _score_data(role)
    labels_sha256 = _check_labels_hash()
    wp2.verify_checkpoints(CKPT_DIR)
    inputs = {"n": len(data.ids), "ids_sha256": sha256_ids(data.ids), "puzzles_sha256": sha256_array(data.puzzles),
              "solutions_sha256": sha256_array(data.solutions), "labels_sha256": labels_sha256, "batch": BATCH}
    rec = wp2.guard_start(RUNNER, role, args.force, args.resume, inputs)
    L = _layout(role)
    if args.resume:
        # Neither a partial score.tmp/ nor a score/ left by a crash between the rename and
        # finish_run is ever read as valid (Task 7 controller ruling): discard both and restart.
        # `prepare_resume_outputs` gates this on the outputs_started marker first: `guard_start`
        # writes the (incomplete) run record before a fresh start's `clear_outputs` call, so a
        # refused fresh TEST start over unrecorded leftovers (e.g. a complete prior run whose
        # record was separately lost, say to `git clean`) still leaves an incomplete, markerless
        # record behind, and this --resume must not treat that leftover as this run's own partial
        # state and discard it.
        rec = wp2.prepare_resume_outputs(RUNNER, role, rec, [L["score_tmp"], L["score"]])
        for d in (L["score_tmp"], L["score"]):
            if d.exists():
                shutil.rmtree(d)
    else:
        wp2.clear_outputs(RUNNER, role, [L["score_tmp"], L["score"]])
        rec = wp2.mark_outputs_started(RUNNER, role)
    m = load_model(CKPT_DIR)

    lab = labels(data.puzzles)
    solve = extract_streamed(m, L["score_tmp"], data.puzzles, data.solutions, batch=BATCH)
    save_subset(L["dir"], "score.tmp", data.ids, data.puzzles, data.solutions, {"solve": solve}, lab)
    wp2.atomic_write(L["score_tmp"] / "ids.json", json.dumps(data.ids) + "\n")

    score_manifest = wp2.manifest({name: L["score_tmp"] / name for name in FILE_NAMES})
    gc.collect()  # release any surviving memmap: Windows refuses to rename a directory with a mapped file
    wp2.replace_with_retry(L["score_tmp"], L["score"])

    extra = {"n": len(data.ids), "labels_sha256": labels_sha256, "score_manifest": score_manifest}
    if role == "dry":
        extra["matches_e3prep"] = compare_dirs(L["score"], _probe_val_dir(), ARRAY_NAMES)

    seconds = time.perf_counter() - t_start
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
