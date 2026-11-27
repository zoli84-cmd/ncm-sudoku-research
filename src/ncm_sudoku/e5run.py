"""E5 TEST runner infrastructure: run directory, input hashes, lock gate and resume
(`e5_protocol_v1.md` §6 "Restartability", §9.3-§9.4, §10).

Three modes share the same run-record machinery: `dry` (PROBE-VAL, never reaches the TEST
generator), `dry_perm` (the same dry run with the fixed reordering permutation of §9.4(e)) and
`test` (the single-look confirmatory run, gated by `require_lock`).

A run record (`RUN_DIR[mode]/run.json`) is `{"status", "inputs", "threads", "started", "stages"}`;
`status` is `"running"`, `"finished"` or `"invalid"`. `start_run` is the only way to begin or
resume a run: a finished or invalid record is never rerun (single look); a single-writer lock file
`RUN_DIR[mode]/.lock` (exclusive create) refuses a second concurrent writer; `--resume` requires
the stored `inputs` and thread count to match exactly and re-hashes every partial output already
listed in `stages`, so a changed input or a tampered output stops the resume rather than silently
continuing from a different state. `record_output` stores a completed stage's file hash in the
record (the caller has already written the file atomically, e.g. through `wp2.atomic_*`).
`finish_run` writes the terminal status and removes the lock file.

`lock_state`/`require_lock` gate the TEST mode on the preregistration lock: the tag `e5-prereg-v1`
at HEAD, the code paths listed in `LOCK_CODE_PATHS` clean (ruling R1: this checks the cleanliness
of the project's own code and the frozen E5 lock/dry artifacts, not the whole working tree, so
unrelated uncommitted files elsewhere never block the gate), the `third_party/ncm` submodule at
`wp2.UPSTREAM_COMMIT` and clean, every hash in the manifest (`verify_manifest`, ruling R4) equal to
its recorded value, and the approved dry-run record's own hashes equal and `passed` true.
"""

import json
import os
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

import numpy as np
import torch

from ncm_sudoku import subsets, wp2
from ncm_sudoku.model import ROOT

LOCK_TAG = "e5-prereg-v1"

RUN_DIR = {
    "dry": ROOT / "runs" / "e5" / "dry",
    "dry_perm": ROOT / "runs" / "e5" / "dry_perm",
    "test": ROOT / "runs" / "e5" / "test",
}
OUT_DIR = {
    "dry": ROOT / "experiments" / "e5" / "dry",
    "dry_perm": ROOT / "experiments" / "e5" / "dry_perm",
    "test": ROOT / "experiments" / "e5" / "test",
}

# Ruling R1: cleanliness checked on the project's own code and the frozen E5 lock/dry artifacts
# only, as wp2.CODE_PATHS does for the WP2 freeze - never the whole working tree.
LOCK_CODE_PATHS = ("src", "scripts", "tests", "pyproject.toml", "uv.lock", "e5_protocol_v1.md",
                   "experiments/e5/lock", "experiments/e5/dry")


class DataIntegrityError(RuntimeError):
    """A recorded hash (manifest entry or approved dry-run record) no longer matches its file."""


class LockError(RuntimeError):
    """The repository is not at the `e5-prereg-v1` preregistration lock."""


class RunStateError(RuntimeError):
    """`start_run`/`record_output`/`finish_run` refused: single-look, single-writer or resume rules."""


def _git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(cwd), *args], text=True, encoding="utf-8",
                                   stderr=subprocess.DEVNULL).strip()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _run_json(mode: str) -> Path:
    if mode not in RUN_DIR:
        raise ValueError(f"unknown mode {mode!r}; expected one of {tuple(RUN_DIR)}")
    return RUN_DIR[mode] / "run.json"


def _lock_file(mode: str) -> Path:
    return RUN_DIR[mode] / ".lock"


def _read(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# --- input hashes and run records -------------------------------------------------------------

def input_hashes(paths: dict[str, Path]) -> dict[str, str]:
    """SHA-256 of the file bytes of every named input (reused for `inputs` and for resume checks)."""
    return {name: wp2.file_sha256(Path(p)) for name, p in paths.items()}


def _lock_info() -> dict:
    return {"pid": os.getpid(), "host": socket.gethostname(), "started": _now()}


def start_run(mode: str, inputs: dict[str, str], resume: bool) -> dict:
    """Begins or resumes a run; never reruns a finished or invalid run (single look).

    Fresh start (`resume=False`): refuses if a `run.json` already exists (any status; use
    `resume=True` to continue a `"running"` one). Creates `RUN_DIR[mode]/run.json` with
    `status="running"`, the given `inputs`, the current `torch.get_num_threads()`, the start time
    and empty `stages`, and the single-writer lock file `RUN_DIR[mode]/.lock` (exclusive create,
    holding the writer's PID, host name and UTC start time as diagnostics; the required thread
    count, if any, is enforced by the caller, e.g. the runner script's `torch.set_num_threads(4)`
    before calling this).

    `inputs` is an opaque dict of name -> hash (typically from `input_hashes`, plus any other
    hash the caller wants checked): identical `inputs` on resume is the *only* thing that checks
    an input or its processing order did not change. In particular, order is not tracked
    separately - a caller whose stages depend on an ordered sequence (e.g. the TEST pair ids) must
    put an order-sensitive hash of that sequence among `inputs`, such as `subsets.sha256_ids` of
    the ordered id list, so that a reordering (a different hash) is refused on resume exactly like
    any other changed input.

    Resume (`resume=True`): requires a stored record with `status="running"` and `inputs` and
    `threads` identical to the ones given here (a changed checkpoint hash, pair-set hash, thread
    count, etc. refuses the resume rather than continuing from a different state); re-hashes every
    partial output already listed in `stages` and refuses if any is missing or has changed since it
    was recorded (a tampered or half-written output is never resumed from). Returns the stored
    record unchanged.

    Either way, a lock file created by this call is removed again if any later check in this same
    call fails, so a refused resume can be retried once the problem is fixed. A pre-existing lock
    file is never broken automatically: its content (pid, host, start time) is reported in the
    refusal so a human can confirm that process is no longer running before removing the file by
    hand; only after that manual removal do the usual resume rules apply again."""
    run_path = _run_json(mode)
    lock_path = _lock_file(mode)
    threads = torch.get_num_threads()
    inputs = json.loads(json.dumps(inputs))
    stored = _read(run_path) if run_path.is_file() else None

    if stored is not None and stored.get("status") in ("finished", "invalid"):
        raise RunStateError(f"{mode}: run.json at {run_path} has status {stored['status']!r}; "
                            "a finished or invalid run is never rerun")

    run_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, json.dumps(_lock_info()).encode("utf-8"))
        finally:
            os.close(fd)
    except FileExistsError:
        try:
            held_by = lock_path.read_text(encoding="utf-8")
        except OSError as e:
            held_by = f"<unreadable: {e}>"
        raise RunStateError(
            f"{mode}: lock file {lock_path} exists (held by {held_by}); refusing a second writer. "
            "This lock is never broken automatically: remove the file by hand only after confirming "
            "that the process named in it is no longer running, then retry (the usual --resume "
            "rules apply once the lock is gone).") from None

    try:
        if resume:
            if stored is None:
                raise RunStateError(f"{mode}: --resume given but there is no run.json at {run_path}")
            if stored.get("status") != "running":
                raise RunStateError(f"{mode}: resume refused: stored status is "
                                    f"{stored.get('status')!r}, not 'running'")
            if stored.get("inputs") != inputs:
                raise RunStateError(f"{mode}: resume refused: inputs differ from the stored run")
            if stored.get("threads") != threads:
                raise RunStateError(f"{mode}: resume refused: threads differ from the stored run "
                                    f"({threads} != {stored.get('threads')})")
            for stage, info in (stored.get("stages") or {}).items():
                p = Path(info["path"])
                if not p.is_file():
                    raise RunStateError(f"{mode}: resume refused: stage {stage!r} output {p} is missing")
                if wp2.file_sha256(p) != info["sha256"]:
                    raise RunStateError(f"{mode}: resume refused: stage {stage!r} output {p} "
                                        "changed since it was recorded")
            rec = stored
        else:
            if stored is not None:
                raise RunStateError(f"{mode}: run.json already exists at {run_path} "
                                    f"(status {stored.get('status')!r}); use resume=True to continue it")
            rec = {"status": "running", "inputs": inputs, "threads": threads, "started": _now(), "stages": {}}
            wp2.atomic_json(run_path, rec)
    except Exception:
        lock_path.unlink(missing_ok=True)
        raise
    return rec


def record_output(mode: str, stage: str, path: Path) -> None:
    """Records a completed stage's output hash in `run.json`. The file itself is already written
    atomically by the caller (e.g. `wp2.atomic_json`/`atomic_npy`/`atomic_npz`); this only stores
    its path and SHA-256, so a later `start_run(resume=True)` can verify it is unchanged."""
    run_path = _run_json(mode)
    if not run_path.is_file():
        raise RunStateError(f"{mode}: no run.json at {run_path}")
    rec = _read(run_path)
    if rec.get("status") != "running":
        raise RunStateError(f"{mode}: run.json at {run_path} has status {rec.get('status')!r}, not 'running'")
    p = Path(path).resolve()
    rec.setdefault("stages", {})[stage] = {"path": str(p), "sha256": wp2.file_sha256(p)}
    wp2.atomic_json(run_path, rec)


def finish_run(mode: str, status: str, summary: dict) -> None:
    """Writes the terminal status (`"finished"` or `"invalid"`) and the summary, then removes the
    single-writer lock file. A run record already `"finished"` or `"invalid"` is never finished
    again (that would make a single-look run runnable twice)."""
    if status not in ("finished", "invalid"):
        raise ValueError(f"unknown status {status!r}; expected 'finished' or 'invalid'")
    run_path = _run_json(mode)
    if not run_path.is_file():
        raise RunStateError(f"{mode}: no run.json at {run_path}")
    rec = _read(run_path)
    if rec.get("status") != "running":
        raise RunStateError(f"{mode}: run.json at {run_path} has status {rec.get('status')!r}, not 'running'")
    rec["status"] = status
    rec["finished"] = _now()
    rec["summary"] = json.loads(json.dumps(summary))
    wp2.atomic_json(run_path, rec)
    _lock_file(mode).unlink(missing_ok=True)


# --- lock gate and manifest ----------------------------------------------------------------------

def lock_state(root: Path | None = None) -> dict:
    """Preregistration-lock state (mirrors `wp2.freeze_state`'s shape); a missing tag or a dirty or
    missing upstream submodule means `"locked": False`, never an error."""
    root = ROOT if root is None else Path(root)
    try:
        tag_commit = _git(root, "rev-parse", "--verify", "--quiet", f"refs/tags/{LOCK_TAG}^{{commit}}") or None
    except subprocess.CalledProcessError:
        tag_commit = None
    head = _git(root, "rev-parse", "HEAD")
    code_clean = not _git(root, "status", "--porcelain", "--untracked-files=all", "--", *LOCK_CODE_PATHS)
    up = root / "third_party" / "ncm"
    try:
        upstream_commit = _git(up, "rev-parse", "HEAD")
        upstream_clean = not _git(up, "status", "--porcelain", "--untracked-files=all")
    except (subprocess.CalledProcessError, FileNotFoundError, NotADirectoryError):
        upstream_commit, upstream_clean = None, False
    upstream_ok = upstream_commit == wp2.UPSTREAM_COMMIT
    locked = tag_commit is not None and head == tag_commit and code_clean and upstream_ok and upstream_clean
    return {"tag": LOCK_TAG, "tag_commit": tag_commit, "head": head, "code_clean": code_clean,
            "upstream_commit": upstream_commit, "upstream_ok": upstream_ok, "upstream_clean": upstream_clean,
            "locked": locked}


def _checked_root_relative_path(rel: object, what: str) -> Path:
    """Resolves `rel` as a ROOT-relative POSIX path, refusing anything that could point outside
    ROOT: a non-string; a backslash or a colon (a Windows-style absolute or drive-letter path, or a
    UNC path, none of which `PurePosixPath` flags as absolute or containing `..`); a POSIX-absolute
    path or a `..` segment; and, as defence in depth, a path that resolves outside `ROOT` (e.g.
    through a symlink) even after the checks above."""
    if not isinstance(rel, str):
        raise DataIntegrityError(f"{what}: path is missing or not a string")
    if "\\" in rel or ":" in rel:
        raise DataIntegrityError(f"{what}: {rel} is not a ROOT-relative POSIX path")
    rp = PurePosixPath(rel)
    if rp.is_absolute() or PureWindowsPath(rel).is_absolute() or ".." in rp.parts:
        raise DataIntegrityError(f"{what}: {rel} is not a ROOT-relative path")
    root_resolved = ROOT.resolve()
    p = (ROOT / rp).resolve()
    if not p.is_relative_to(root_resolved):
        raise DataIntegrityError(f"{what}: {rel} escapes ROOT")
    return p


def _manifest_hash(entry: dict) -> str:
    name = entry.get("name", "<unnamed>")
    fmt = entry.get("format")
    p = _checked_root_relative_path(entry.get("path"), f"manifest entry {name!r}")
    if not p.is_file():
        raise DataIntegrityError(f"manifest entry {name!r}: {p} missing")
    if fmt == "file":
        return wp2.file_sha256(p)
    if fmt == "sha256_ids":
        ids = json.loads(p.read_text(encoding="utf-8"))
        return subsets.sha256_ids(ids)
    if fmt == "sha256_array":
        return subsets.sha256_array(np.load(p, allow_pickle=False))
    raise DataIntegrityError(f"manifest entry {name!r}: unknown format {fmt!r}")


def verify_manifest(path: Path) -> None:
    """Recomputes every entry's SHA-256 against the §10 hash manifest at `path`; raises
    `DataIntegrityError` naming the first entry whose path is unsafe, missing or does not hash to
    its recorded value. Reused as-is by the manifest script's `--verify` (a later task)."""
    data = _read(path)
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise DataIntegrityError(f"manifest {path}: no entries list")
    for entry in entries:
        name = entry.get("name", "<unnamed>")
        if _manifest_hash(entry) != entry.get("sha256"):
            raise DataIntegrityError(f"manifest {path}: entry {name!r} differs from its recorded SHA-256")


def require_lock(manifest: Path, dry_record: Path) -> None:
    """TEST-mode start gate: raises `LockError` unless the repository is exactly at the
    `e5-prereg-v1` lock (tag at HEAD, the §9.3 code paths clean, `third_party/ncm` at the pinned
    commit and clean); raises `DataIntegrityError` unless every manifest entry (`verify_manifest`)
    and every hash named in the approved dry-run record (plus its own `check.sha256` sidecar)
    recomputes equal, and the record's `passed` is `True`."""
    state = lock_state()
    if not state["locked"]:
        raise LockError(f"not at the {LOCK_TAG} lock: {state}")
    verify_manifest(manifest)

    rec_path = Path(dry_record)
    check_path = rec_path.with_name("check.sha256")
    if not check_path.is_file():
        raise DataIntegrityError(f"dry record {rec_path}: sidecar {check_path} missing")
    if not rec_path.is_file():
        raise DataIntegrityError(f"dry record {rec_path}: missing")
    if wp2.file_sha256(rec_path) != check_path.read_text(encoding="utf-8").strip():
        raise DataIntegrityError(f"dry record {rec_path}: differs from its recorded check.sha256")

    rec = _read(rec_path)
    if rec.get("passed") is not True:
        raise DataIntegrityError(f"dry record {rec_path}: passed is not true")
    hashes = rec.get("hashes")
    if not isinstance(hashes, dict):
        raise DataIntegrityError(f"dry record {rec_path}: no hashes")
    for rel, expected in hashes.items():
        p = _checked_root_relative_path(rel, f"dry record {rec_path}")
        if not p.is_file():
            raise DataIntegrityError(f"dry record {rec_path}: {rel} missing")
        if wp2.file_sha256(p) != expected:
            raise DataIntegrityError(f"dry record {rec_path}: {rel} differs from its recorded hash")
