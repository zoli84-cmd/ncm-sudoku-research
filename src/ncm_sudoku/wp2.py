"""Shared WP2 infrastructure (plan v3.7 §10, §12.2; D76): roles, TEST data and checkpoint verification,
the fail-closed code-freeze guard, run records (complete vs. valid), resume rules, dry approval,
manifests and atomic writes. Every WP2 runner starts with `guard_start` and ends with `finish_run`.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import numpy as np
import torch

from ncm_sudoku import subsets
from ncm_sudoku.g0 import CODE_PATHS, code_state, environment_record
from ncm_sudoku.model import ROOT
from ncm_sudoku.subsets import sha256_array, sha256_ids

ROLES = ("test", "dry")
FREEZE_TAG = "wp2-code"
CKPT_SHA256 = {  # plan §12.2
    "generator.pt": "9e0bfe44abc1ca3930b7a63cd56cd0b9564b95e29edfe12dd0903207b89df8b8",
    "tokenizer.pt": "3bc6aecad8e15820f9d9bb09750e3c59bdf91ca953f1f11dbd109aaed1d80c0b",
    "config.yaml": "8d58c49e6fe52e60191e06df4061937d5bb84f97c5ffbcd93ed9830c32f8df2f",
}
UPSTREAM_COMMIT = "c70274273f489abc73832b2b98584a8483b6b203"
TEST_DIR = ROOT / "runs" / "lock" / "test"
TEST_LOCK = ROOT / "experiments" / "lock" / "test_set.json"
TEST_COUNT = 600
TEST_SHA256 = {  # plan §12.2; checked when the default lock file is used
    "ids": "6e019563448e73408cd24a7ae207f5fd2549f0c881e70a37348d06f21ad6f09e",
    "puzzles": "e9e714c83f333922e55ba36998343e1e0ffa73a75c52e8531f0bf5bed943c886",
    "solutions": "08b333165f081f8c74d6d558372dc02cbb8d4dc35aac40b5da0ac699031fe471",
}
DRY_NOTE = "DRY RUN (CAL / PROBE-VAL in the TEST role); not TEST"
DRY_CHECK = ROOT / "experiments" / "wp2" / "dry" / "check.json"
SNAPSHOT_GROUPS = ("dry_records", "compared", "probe_inputs")
N_DRY = 50
TECHNICAL_KEYS = ("runner", "role", "stage", "seconds", "complete", "valid", "status", "n", "n_records",
                  "level1_noop_mismatch", "sham_mismatch", "code_mismatch")
RESERVED_KEYS = frozenset({
    "runner", "role", "note", "started", "environment", "code", "freeze", "inputs", "resumes", "finished",
    "seconds", "environment_end", "code_end", "freeze_end", "code_changed_during_run", "complete", "valid",
    "invalid_reasons", "status", "outputs_started"})


class DataIntegrityError(RuntimeError):
    pass


@dataclass(frozen=True)
class RoleData:
    ids: list[str]
    puzzles: np.ndarray
    solutions: np.ndarray
    source: str


# --- atomic writes ---------------------------------------------------------------------------

_sleep = time.sleep  # monkeypatched by tests


def replace_with_retry(src: Path, dst: Path, *, timeout_s: float = 120.0, first_delay_s: float = 0.1,
                       max_delay_s: float = 5.0, sleep=None) -> None:
    """`os.replace(src, dst)`, retried on `PermissionError` only (on Windows a virus scanner or the
    search indexer can briefly hold a freshly written file). Sleeps first_delay_s, doubling, each
    sleep capped at max_delay_s; once the next sleep would push the total past timeout_s, the last
    `PermissionError` is re-raised. Any other exception is raised at once. Same result as one
    successful `os.replace`; nothing else is written."""
    sleep = _sleep if sleep is None else sleep
    delay, slept = first_delay_s, 0.0
    while True:
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            delay = min(delay, max_delay_s)
            if slept + delay > timeout_s:
                raise
            sleep(delay)
            slept += delay
            delay *= 2


def _replace(tmp: Path, path: Path, write) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        write(tmp)
        replace_with_retry(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def atomic_write(path: Path, text: str) -> None:
    path = Path(path)
    _replace(path.with_name(path.name + ".tmp"), path,
             lambda t: t.write_text(text, encoding="utf-8", newline="\n"))


def atomic_json(path: Path, obj, indent: int | None = 2) -> None:
    atomic_write(path, json.dumps(obj, indent=indent) + "\n")


def atomic_npy(path: Path, a: np.ndarray) -> None:
    path = Path(path)
    _replace(path.with_name(path.stem + ".tmp.npy"), path, lambda t: np.save(t, a))


def atomic_npz(path: Path, **arrays) -> None:
    path = Path(path)
    _replace(path.with_name(path.stem + ".tmp.npz"), path, lambda t: np.savez(t, **arrays))


# --- hashes, manifests, data -----------------------------------------------------------------

def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def manifest(files: dict[str, Path]) -> dict[str, str]:
    return {name: file_sha256(p) for name, p in files.items()}


def check_manifest(files: dict[str, Path], expected: dict[str, str]) -> None:
    for name in [*expected, *(n for n in files if n not in expected)]:
        if name not in expected:
            raise DataIntegrityError(f"manifest: {name} is not in the manifest")
        if name not in files or not Path(files[name]).is_file():
            raise DataIntegrityError(f"manifest: {name} is missing")
        if file_sha256(files[name]) != expected[name]:
            raise DataIntegrityError(f"manifest: {name} ({files[name]}) differs from its recorded SHA-256")


def verify_test_data(data_dir: Path = TEST_DIR, lock_json: Path = TEST_LOCK) -> RoleData:
    """Checks the TEST arrays against the lock file before anything else uses them."""
    lock = json.loads(Path(lock_json).read_text(encoding="utf-8"))
    count = lock["count"]
    if Path(lock_json) == TEST_LOCK and (count != TEST_COUNT or lock["sha256"] != TEST_SHA256):
        raise DataIntegrityError(f"lock: {lock_json} differs from the §12.2 TEST count or hashes")
    try:
        ids = json.loads((Path(data_dir) / "ids.json").read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise DataIntegrityError(f"ids: {e.filename} missing") from None
    if not isinstance(ids, list) or len(ids) != count:
        raise DataIntegrityError(f"ids: count {len(ids) if isinstance(ids, list) else None} != {count}")
    arrays = {}
    for name in ("puzzles", "solutions"):
        p = Path(data_dir) / f"{name}.npy"
        if not p.is_file():
            raise DataIntegrityError(f"{name}: {p} missing")
        a = np.load(p, allow_pickle=False)
        if a.dtype != np.uint8:
            raise DataIntegrityError(f"{name}: dtype {a.dtype} != uint8")
        if a.shape != (count, 81):
            raise DataIntegrityError(f"{name}: shape {a.shape} != ({count}, 81)")
        if sha256_array(a) != lock["sha256"][name]:
            raise DataIntegrityError(f"{name}: SHA-256 differs from the lock")
        arrays[name] = a
    if sha256_ids(ids) != lock["sha256"]["ids"]:
        raise DataIntegrityError("ids: SHA-256 differs from the lock")
    if ids != lock["ids"]:
        raise DataIntegrityError("ids: differ from the lock's ids list")
    return RoleData(ids=ids, puzzles=arrays["puzzles"], solutions=arrays["solutions"], source="test")


def load_role(role: str, n_dry: int = N_DRY) -> RoleData:
    if role == "test":
        return verify_test_data()
    if role == "dry":
        ps = subsets.generate_subset("cal", n_dry)
        return RoleData(ids=[p.puzzle_id for p in ps], puzzles=np.stack([p.puzzle for p in ps]).astype(np.uint8),
                        solutions=np.stack([p.solution for p in ps]).astype(np.uint8), source=f"cal[:{n_dry}]")
    raise ValueError(f"unknown role {role!r}; expected one of {ROLES}")


def verify_checkpoints(ckpt_dir: Path) -> None:
    for name, expected in CKPT_SHA256.items():
        p = Path(ckpt_dir) / name
        if not p.is_file():
            raise DataIntegrityError(f"checkpoint {name}: {p} missing")
        if file_sha256(p) != expected:
            raise DataIntegrityError(f"checkpoint {name}: SHA-256 differs from §12.2")


def paths(role: str) -> tuple[Path, Path]:
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}; expected one of {ROLES}")
    return ROOT / "experiments" / "wp2" / role, ROOT / "runs" / "wp2" / role


def _record_path(runner: str, role: str) -> Path:
    return paths(role)[0] / "runs" / f"{runner}.json"


# --- freeze and dry approval -----------------------------------------------------------------

def _git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(cwd), *args], text=True, encoding="utf-8",
                                   stderr=subprocess.DEVNULL).strip()


def freeze_state(root: Path | None = None) -> dict:
    """Code-freeze state (D76(2)); a missing tag or upstream worktree means "not frozen", never an error."""
    root = ROOT if root is None else Path(root)
    try:
        tag_commit = _git(root, "rev-parse", "--verify", "--quiet", f"refs/tags/{FREEZE_TAG}^{{commit}}") or None
    except subprocess.CalledProcessError:
        tag_commit = None
    head = _git(root, "rev-parse", "HEAD")
    code_clean = not _git(root, "status", "--porcelain", "--untracked-files=all", "--", *CODE_PATHS)
    up = root / "third_party" / "ncm"
    try:
        upstream_commit = _git(up, "rev-parse", "HEAD")
        upstream_clean = not _git(up, "status", "--porcelain", "--untracked-files=all")
    except (subprocess.CalledProcessError, FileNotFoundError, NotADirectoryError):
        upstream_commit, upstream_clean = None, False
    upstream_ok = upstream_commit == UPSTREAM_COMMIT
    frozen = tag_commit is not None and head == tag_commit and code_clean and upstream_ok and upstream_clean
    return {"tag": FREEZE_TAG, "tag_commit": tag_commit, "head": head, "code_clean": code_clean,
            "upstream_commit": upstream_commit, "upstream_ok": upstream_ok, "upstream_clean": upstream_clean,
            "frozen": frozen}


def verify_dry_approval(check: dict) -> None:
    """Recomputes every snapshot hash of the dry approval; raises naming the first missing or changed file."""
    snap = check.get("snapshot")
    if not isinstance(snap, dict):
        raise DataIntegrityError("dry approval: snapshot missing")
    for group in SNAPSHOT_GROUPS:
        if not isinstance(snap.get(group), dict):
            raise DataIntegrityError(f"dry approval: snapshot group {group} missing")
    for group, files in snap.items():
        if group not in SNAPSHOT_GROUPS:
            raise DataIntegrityError(f"dry approval: unknown snapshot group {group}")
        for rel, expected in files.items():
            rp = PurePosixPath(rel)
            if rp.is_absolute() or ".." in rp.parts:
                raise DataIntegrityError(f"dry approval {group}: {rel} is not a ROOT-relative path")
            p = ROOT / rp
            if not p.is_file():
                raise DataIntegrityError(f"dry approval {group}: {rel} missing")
            if file_sha256(p) != expected:
                raise DataIntegrityError(f"dry approval {group}: {rel} differs from the approved snapshot")


def valid_record(rec: dict, tag_commit: str | None) -> tuple[bool, list[str]]:
    """Spec ambiguity 24: complete, frozen at start, at every resume and at finish, code unchanged and
    clean, at the tag commit, plus the stored reasons (e.g. identity-failure)."""
    frozen = lambda f: isinstance(f, dict) and f.get("frozen") is True  # noqa: E731
    code, code_end = rec.get("code") or {}, rec.get("code_end") or {}
    reasons = []
    if rec.get("complete") is not True:
        reasons.append("incomplete")
    if not frozen(rec.get("freeze")):
        reasons.append("freeze_start")
    if not frozen(rec.get("freeze_end")):
        reasons.append("freeze_end")
    if any(not frozen(r.get("freeze")) for r in rec.get("resumes", [])):
        reasons.append("freeze_resume")
    if rec.get("code_changed_during_run") is not False or code_end != code:
        reasons.append("code_changed_during_run")
    if code.get("dirty") is not False or code_end.get("dirty") is not False:
        reasons.append("code_dirty")
    if tag_commit is None or code.get("commit") != tag_commit:
        reasons.append("not_tag_commit")
    reasons += list(rec.get("invalid_reasons", []))
    reasons = list(dict.fromkeys(reasons))
    return not reasons, reasons


# --- guard and run records -------------------------------------------------------------------

def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", choices=ROLES, required=True)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--force", action="store_true")
    g.add_argument("--resume", action="store_true")
    return ap.parse_args(argv)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _plain(obj):
    return json.loads(json.dumps(obj))


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _test_gate(runner: str, force: bool, freeze: dict) -> None:
    """TEST-role preconditions, in the order of the plan (D76(2))."""
    if not freeze["frozen"]:
        sys.exit(f"{runner}: TEST role requires the code freeze (tag {FREEZE_TAG}); state: {freeze}")
    if force:
        sys.exit(f"{runner}: the TEST role never accepts --force (single look)")
    tag_commit = freeze["tag_commit"]
    dry = _record_path(runner, "dry")
    if not dry.is_file():
        sys.exit(f"{runner}: no dry record at {dry}; run the dry role first")
    ok, reasons = valid_record(_read(dry), tag_commit)
    if not ok or _read(dry).get("valid") is not True:
        sys.exit(f"{runner}: dry record is not valid at the tag commit: {reasons}")
    if not DRY_CHECK.is_file():
        sys.exit(f"{runner}: dry check {DRY_CHECK} missing")
    check = _read(DRY_CHECK)
    if check.get("technical_success") is not True:
        sys.exit(f"{runner}: dry check has no technical_success: true")
    if (check.get("code") or {}).get("commit") != tag_commit:
        sys.exit(f"{runner}: dry check code.commit differs from the tag commit {tag_commit}")
    rel = dry.relative_to(ROOT).as_posix()
    if rel not in ((check.get("snapshot") or {}).get("dry_records") or {}):
        sys.exit(f"{runner}: dry check snapshot does not cover {rel}")
    try:
        verify_dry_approval(check)
    except DataIntegrityError as e:
        sys.exit(f"{runner}: {e}")


def guard_start(runner: str, role: str, force: bool, resume: bool, inputs: dict) -> dict:
    """Checks the start conditions, writes the incomplete run record and returns it (exits on refusal)."""
    rec_path = _record_path(runner, role)
    if force and resume:
        sys.exit("--force and --resume are mutually exclusive")
    torch.use_deterministic_algorithms(True)
    freeze = freeze_state(ROOT)
    if role == "test":
        _test_gate(runner, force, freeze)
    stored = _read(rec_path) if rec_path.exists() else None
    environment, code, inputs = _plain(environment_record()), _plain(code_state()), _plain(inputs)
    if stored is not None and stored.get("complete") is True:
        if role == "test":
            sys.exit(f"{runner}: a complete TEST record exists at {rec_path}; TEST runs are single-look")
        if not force:
            sys.exit(f"{runner}: a complete record exists at {rec_path}; use --force to rerun the dry role")
    if resume:
        if stored is None:
            sys.exit(f"{runner}: --resume given but there is no stored record at {rec_path}")
        for key, current in (("runner", runner), ("role", role), ("code", code), ("inputs", inputs),
                             ("environment", environment)):
            if stored.get(key) != current:
                sys.exit(f"{runner}: --resume refused: {key} differs from the stored run")
        if role == "dry":
            DRY_CHECK.unlink(missing_ok=True)
        rec = {**stored, "resumes": [*stored.get("resumes", []),
                                     {"started": _now(), "environment": environment, "code": code, "freeze": freeze}]}
    else:
        if stored is not None and stored.get("complete") is not True and not force:
            sys.exit(f"{runner}: an incomplete record exists at {rec_path}; use --resume")
        if role == "dry":
            DRY_CHECK.unlink(missing_ok=True)
        rec = {"runner": runner, "role": role, "note": DRY_NOTE if role == "dry" else None, "started": _now(),
               "environment": environment, "code": code, "freeze": freeze, "inputs": inputs,
               "complete": False, "valid": False}
    atomic_json(rec_path, rec)
    return rec


def update_run(runner: str, role: str, fields: dict) -> dict:
    if RESERVED_KEYS & set(fields):
        raise ValueError(f"reserved run-record keys: {sorted(RESERVED_KEYS & set(fields))}")
    rec_path = _record_path(runner, role)
    if not rec_path.is_file():
        raise DataIntegrityError(f"{runner}: no run record at {rec_path}")
    rec = _read(rec_path)
    if rec.get("complete") is not False:
        raise DataIntegrityError(f"{runner}: run record at {rec_path} is not incomplete")
    rec.update(_plain(fields))
    atomic_json(rec_path, rec)
    return rec


def finish_run(runner: str, role: str, record: dict, seconds: float, extra: dict,
               invalid: tuple[str, ...] = ()) -> dict:
    """Completes the run record; the stored record's fields win over the passed one (update_run checkpoints)."""
    if RESERVED_KEYS & set(extra):
        raise ValueError(f"reserved run-record keys: {sorted(RESERVED_KEYS & set(extra))}")
    rec_path = _record_path(runner, role)
    stored = _read(rec_path) if rec_path.exists() else {}
    if stored.get("complete") is True:
        raise DataIntegrityError(f"{runner}: run record at {rec_path} is already complete")
    rec = {**_plain(record), **stored}
    torch.use_deterministic_algorithms(True)
    environment_end, code_end, freeze_end = _plain(environment_record()), _plain(code_state()), freeze_state(ROOT)
    rec.update(finished=_now(), seconds=seconds, environment_end=environment_end, code_end=code_end,
               freeze_end=freeze_end, code_changed_during_run=code_end != rec.get("code"))
    rec.update(_plain(extra))
    rec["complete"] = True
    rec.pop("invalid_reasons", None)
    reasons = list(dict.fromkeys([*valid_record(rec, freeze_end["tag_commit"])[1], *invalid]))
    rec["invalid_reasons"] = reasons
    rec["valid"] = not reasons
    rec["status"] = "valid" if not reasons else ("identity-failure" if "identity-failure" in reasons
                                                 else "freeze-violation")
    atomic_json(rec_path, rec)
    return rec


def status_line(**fields) -> None:
    """The only stdout channel of a WP2 runner: one JSON line of technical fields (D76(5))."""
    bad = sorted(set(fields) - set(TECHNICAL_KEYS))
    if bad:
        raise ValueError(f"non-technical status keys: {bad}")
    print(json.dumps(fields), flush=True)


def clear_outputs(runner: str, role: str, targets: list[Path]) -> None:
    """Deletes listed outputs of a previous run; only inside this role's output dirs, never run records.
    In the TEST role it never deletes: any existing target raises DataIntegrityError.

    Fresh-start only: `guard_start` writes the (incomplete) run record *before* this is called, so
    a refusal here still leaves that record on disk, with no `outputs_started` marker. A later
    `--resume` must go through `prepare_resume_outputs`, not this function, or it could treat a
    genuine prior run's outputs (whose record was separately lost, e.g. to `git clean`) as this
    run's own partial state and destroy single-look TEST outputs."""
    roots = [p.resolve() for p in paths(role)]
    records = (paths(role)[0] / "runs").resolve()
    resolved = [Path(t).resolve() for t in targets]
    for t in resolved:
        if not any(t.is_relative_to(r) and t != r for r in roots) or t.is_relative_to(records):
            raise ValueError(f"{runner}: refusing to delete {t} (outside the {role} outputs or a run record)")
    if role == "test":
        present = [t for t in resolved if t.exists()]
        if present:
            raise DataIntegrityError(f"{runner}: TEST outputs already exist ({present[0]}); TEST runs are "
                                     "single-look and their outputs are never deleted")
        return
    for t in resolved:
        if t.is_dir():
            shutil.rmtree(t)
        elif t.exists():
            t.unlink()


def mark_outputs_started(runner: str, role: str) -> dict:
    """Records, right after a fresh start's `clear_outputs` succeeds and before any output is
    written, that this run's own attempt now owns its output targets. `prepare_resume_outputs`
    uses the marker to tell a genuine in-progress run's partial state (safe to discard or
    overwrite on `--resume`) from a stale, markerless incomplete record: `guard_start` writes the
    record before a fresh start calls `clear_outputs`, so a refused fresh TEST start over
    unrecorded leftover outputs (e.g. a prior complete run whose record was lost) still leaves an
    incomplete record behind, with no marker. Only this function sets the key; `outputs_started`
    is reserved so ordinary `update_run`/`finish_run` extras cannot set it."""
    rec_path = _record_path(runner, role)
    if not rec_path.is_file():
        raise DataIntegrityError(f"{runner}: no run record at {rec_path}")
    rec = _read(rec_path)
    if rec.get("complete") is not False:
        raise DataIntegrityError(f"{runner}: run record at {rec_path} is not incomplete")
    rec["outputs_started"] = True
    atomic_json(rec_path, rec)
    return rec


def prepare_resume_outputs(runner: str, role: str, record: dict, targets: list[Path]) -> dict:
    """Resume-time safety gate for output targets, path-confined exactly like `clear_outputs`
    (never a run record). Raises `DataIntegrityError` naming the first existing target unless
    `record` (as returned by `guard_start`) carries the `outputs_started` marker; with the marker,
    returns `record` unchanged, since every target is this run's own partial state and the runner
    is free to discard or atomically overwrite it with its usual resume logic.

    Without the marker and with no target present, this is a resume from a crash before this
    run's own fresh start ever reached `mark_outputs_started` (between `clear_outputs` succeeding
    and the marker being written, or earlier still): nothing exists yet to confuse with a lost
    prior run's outputs, so the gate marks the record itself, before the runner writes anything,
    and returns the updated record. Skipping this would wedge the run: a later crash after this
    resume has written its own (still markerless) outputs would make every further `--resume`
    refuse permanently, with TEST's `clear_outputs` never able to delete them either."""
    roots = [p.resolve() for p in paths(role)]
    records = (paths(role)[0] / "runs").resolve()
    resolved = [Path(t).resolve() for t in targets]
    for t in resolved:
        if not any(t.is_relative_to(r) and t != r for r in roots) or t.is_relative_to(records):
            raise ValueError(f"{runner}: refusing to touch {t} (outside the {role} outputs or a run record)")
    if record.get("outputs_started") is True:
        return record
    present = [t for t in resolved if t.exists()]
    if present:
        raise DataIntegrityError(
            f"{runner}: {present[0]} exists but this run's record has no outputs_started marker; "
            "refusing to resume over outputs that may belong to a run whose record was lost")
    return mark_outputs_started(runner, role)
