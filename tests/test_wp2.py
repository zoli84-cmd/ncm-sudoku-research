import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
import torch

from ncm_sudoku import subsets, wp2

ROOT = Path(__file__).resolve().parents[1]
IDS = ["gen-v1-6-0", "gen-v1-6-1", "gen-v1-6-2"]
TAG = "a" * 40
CODE = {"commit": TAG, "dirty": False, "diff_sha256": None}
ENV = {"python": "3.12.0", "torch": "2.x", "deterministic": True}
FROZEN = {"tag": "wp2-code", "tag_commit": TAG, "head": TAG, "code_clean": True,
          "upstream_commit": wp2.UPSTREAM_COMMIT, "upstream_ok": True, "upstream_clean": True, "frozen": True}


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _restore_determinism():
    prev = torch.are_deterministic_algorithms_enabled()
    yield
    torch.use_deterministic_algorithms(prev)


# --- hash helpers and TEST data -------------------------------------------------------------

def test_sha256_helpers_moved_unchanged():
    assert subsets.sha256_ids(["a", "b"]) == hashlib.sha256(json.dumps(["a", "b"]).encode("utf-8")).hexdigest()
    a = np.arange(81).reshape(1, 81) % 10
    assert subsets.sha256_array(a) == hashlib.sha256(a.astype(np.uint8).tobytes(order="C")).hexdigest()
    mod = _load("lock_test_set")
    assert mod.sha256_ids is subsets.sha256_ids and mod.sha256_array is subsets.sha256_array


def _toy_test_set(tmp_path, ids=IDS, puzzles=None, solutions=None):
    rng = np.random.default_rng(0)
    p = rng.integers(0, 10, size=(3, 81)).astype(np.uint8) if puzzles is None else puzzles
    s = rng.integers(1, 10, size=(3, 81)).astype(np.uint8) if solutions is None else solutions
    d = tmp_path / "test"
    d.mkdir()
    (d / "ids.json").write_text(json.dumps(ids) + "\n", encoding="utf-8")
    np.save(d / "puzzles.npy", p)
    np.save(d / "solutions.npy", s)
    lock = {"count": 3, "ids": list(IDS), "sha256": {
        "ids": subsets.sha256_ids(IDS), "puzzles": subsets.sha256_array(p), "solutions": subsets.sha256_array(s)}}
    (tmp_path / "lock.json").write_text(json.dumps(lock), encoding="utf-8")
    return d, p, s


def test_verify_test_data_accepts_matching_hashes(tmp_path):
    _toy_test_set(tmp_path)
    d = wp2.verify_test_data(tmp_path / "test", tmp_path / "lock.json")
    assert d.ids == IDS and d.puzzles.dtype == np.uint8 and d.puzzles.shape == (3, 81)
    assert d.solutions.shape == (3, 81) and d.source == "test"


@pytest.mark.parametrize("field", ["ids", "puzzles", "solutions"])
def test_verify_test_data_rejects_tampered_field(tmp_path, field):
    d, p, s = _toy_test_set(tmp_path)
    if field == "ids":
        (d / "ids.json").write_text(json.dumps([IDS[1], IDS[0], IDS[2]]), encoding="utf-8")
    else:
        a = (p if field == "puzzles" else s).copy()
        a[1, 5] = (int(a[1, 5]) + 1) % 10
        np.save(d / f"{field}.npy", a)
    with pytest.raises(wp2.DataIntegrityError, match=field):
        wp2.verify_test_data(d, tmp_path / "lock.json")


def test_verify_test_data_rejects_ids_differing_from_lock_list(tmp_path):
    d, _, _ = _toy_test_set(tmp_path)
    lock = json.loads((tmp_path / "lock.json").read_text(encoding="utf-8"))
    lock["ids"] = ["x", "y", "z"]
    (tmp_path / "lock.json").write_text(json.dumps(lock), encoding="utf-8")
    with pytest.raises(wp2.DataIntegrityError, match="ids"):
        wp2.verify_test_data(d, tmp_path / "lock.json")


def test_verify_test_data_rejects_dtype_and_count(tmp_path):
    d, p, _ = _toy_test_set(tmp_path)
    np.save(d / "puzzles.npy", p.astype(np.int64))  # same values, so sha256_array alone would pass
    with pytest.raises(wp2.DataIntegrityError, match="puzzles.*dtype"):
        wp2.verify_test_data(d, tmp_path / "lock.json")
    np.save(d / "puzzles.npy", p[:2])
    with pytest.raises(wp2.DataIntegrityError, match="puzzles.*shape"):
        wp2.verify_test_data(d, tmp_path / "lock.json")
    np.save(d / "puzzles.npy", p)
    (d / "ids.json").write_text(json.dumps(IDS[:2]), encoding="utf-8")
    with pytest.raises(wp2.DataIntegrityError, match="ids.*count"):
        wp2.verify_test_data(d, tmp_path / "lock.json")


@pytest.mark.slow
def test_real_test_set_verifies():  # reads TEST data only, never runs a model
    if not (wp2.TEST_DIR / "puzzles.npy").exists():
        pytest.skip("runs/lock/test/ not present")
    assert len(wp2.verify_test_data().ids) == 600


def test_constants():
    assert wp2.ROLES == ("test", "dry") and wp2.FREEZE_TAG == "wp2-code" and wp2.N_DRY == 50
    assert wp2.UPSTREAM_COMMIT == "c70274273f489abc73832b2b98584a8483b6b203"
    assert wp2.CKPT_SHA256 == {
        "generator.pt": "9e0bfe44abc1ca3930b7a63cd56cd0b9564b95e29edfe12dd0903207b89df8b8",
        "tokenizer.pt": "3bc6aecad8e15820f9d9bb09750e3c59bdf91ca953f1f11dbd109aaed1d80c0b",
        "config.yaml": "8d58c49e6fe52e60191e06df4061937d5bb84f97c5ffbcd93ed9830c32f8df2f",
    }
    prov = json.loads((ROOT / "experiments" / "provenance" / "checkpoints.json").read_text(encoding="utf-8"))
    assert {k.split("/")[-1]: v["sha256"] for k, v in prov["files"].items()} == wp2.CKPT_SHA256
    assert wp2.TEST_DIR == wp2.ROOT / "runs" / "lock" / "test"
    assert wp2.TEST_LOCK == wp2.ROOT / "experiments" / "lock" / "test_set.json"
    assert wp2.DRY_CHECK == wp2.ROOT / "experiments" / "wp2" / "dry" / "check.json"
    assert wp2.DRY_NOTE == "DRY RUN (CAL / PROBE-VAL in the TEST role); not TEST"


def test_verify_checkpoints_detects_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(wp2, "CKPT_SHA256", {"generator.pt": hashlib.sha256(b"gen").hexdigest(),
                                             "config.yaml": hashlib.sha256(b"cfg").hexdigest()})
    (tmp_path / "generator.pt").write_bytes(b"gen")
    (tmp_path / "config.yaml").write_bytes(b"cfg")
    wp2.verify_checkpoints(tmp_path)
    (tmp_path / "config.yaml").write_bytes(b"cfX")
    with pytest.raises(wp2.DataIntegrityError, match="config.yaml"):
        wp2.verify_checkpoints(tmp_path)
    (tmp_path / "config.yaml").unlink()
    with pytest.raises(wp2.DataIntegrityError, match="config.yaml"):
        wp2.verify_checkpoints(tmp_path)


def test_load_role_dry_and_test(monkeypatch):
    real = subsets.generate_subset
    calls = []

    def gen(name, n):
        calls.append((name, n))
        return real(name, n)
    monkeypatch.setattr(wp2.subsets, "generate_subset", gen)
    d = wp2.load_role("dry", 3)
    assert calls == [("cal", 3)]
    assert d.ids == [p.puzzle_id for p in real("cal", 3)] and d.source == "cal[:3]"
    assert d.puzzles.dtype == np.uint8 and d.puzzles.shape == (3, 81) and d.solutions.shape == (3, 81)
    sentinel = wp2.RoleData(ids=["t"], puzzles=np.zeros((1, 81), np.uint8), solutions=np.zeros((1, 81), np.uint8),
                            source="test")
    monkeypatch.setattr(wp2, "verify_test_data", lambda: sentinel)
    assert wp2.load_role("test") is sentinel
    with pytest.raises(ValueError):
        wp2.load_role("val")


def test_paths_and_unknown_role():
    assert wp2.paths("dry")[0].parts[-3:] == ("experiments", "wp2", "dry")
    assert wp2.paths("test")[1].parts[-3:] == ("runs", "wp2", "test")
    with pytest.raises(ValueError):
        wp2.paths("val")


def test_parse_args():
    a = wp2.parse_args(["--role", "dry", "--resume"])
    assert a.role == "dry" and a.resume and not a.force
    with pytest.raises(SystemExit):
        wp2.parse_args(["--role", "test", "--force", "--resume"])
    with pytest.raises(SystemExit):
        wp2.parse_args([])
    with pytest.raises(SystemExit):
        wp2.parse_args(["--role", "val"])


# --- freeze_state on temporary git repositories ---------------------------------------------

def _git(cwd, *args):
    return subprocess.check_output(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                                    "-c", "tag.gpgsign=false", "-c", "core.autocrlf=false", *args],
                                   cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()


def _repos(tmp_path, monkeypatch, tag=True):
    _git(tmp_path, "init", "-q")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "x.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("third_party/\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    if tag:
        _git(tmp_path, "tag", "wp2-code")
    up = tmp_path / "third_party" / "ncm"
    up.mkdir(parents=True)
    _git(up, "init", "-q")
    (up / "m.py").write_text("y = 1\n", encoding="utf-8")
    (up / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    _git(up, "add", ".")
    _git(up, "commit", "-q", "-m", "up")
    monkeypatch.setattr(wp2, "UPSTREAM_COMMIT", _git(up, "rev-parse", "HEAD"))
    return up


def test_freeze_state_tag_head_and_clean(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch)
    s = wp2.freeze_state(tmp_path)
    assert s["frozen"] is True and s["tag"] == "wp2-code"
    assert s["tag_commit"] == s["head"] == _git(tmp_path, "rev-parse", "HEAD")
    assert s["code_clean"] and s["upstream_ok"] and s["upstream_clean"]
    assert set(s) == {"tag", "tag_commit", "head", "code_clean", "upstream_commit", "upstream_ok",
                      "upstream_clean", "frozen"}


def test_freeze_state_missing_tag_not_frozen(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch, tag=False)
    s = wp2.freeze_state(tmp_path)
    assert s["tag_commit"] is None and s["frozen"] is False


def test_freeze_state_untracked_file_is_dirty(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch)
    (tmp_path / "src" / "AGENTS.md").write_text("new\n", encoding="utf-8")
    s = wp2.freeze_state(tmp_path)
    assert s["code_clean"] is False and s["frozen"] is False


def test_freeze_state_upstream_dirty_unfreezes(tmp_path, monkeypatch):
    up = _repos(tmp_path, monkeypatch)
    (up / "__pycache__").mkdir()
    (up / "__pycache__" / "x.pyc").write_bytes(b"\0")
    s = wp2.freeze_state(tmp_path)
    assert s["upstream_clean"] is True and s["frozen"] is True  # ignored files do not count
    (up / "m.py").write_text("y = 2\n", encoding="utf-8")
    s = wp2.freeze_state(tmp_path)
    assert s["upstream_ok"] is True and s["upstream_clean"] is False and s["frozen"] is False


def test_freeze_state_wrong_upstream_commit_unfreezes(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch)
    monkeypatch.setattr(wp2, "UPSTREAM_COMMIT", "0" * 40)
    s = wp2.freeze_state(tmp_path)
    assert s["upstream_ok"] is False and s["frozen"] is False


def test_freeze_state_new_commit_unfreezes(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "x.md").write_text("d\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "docs")
    s = wp2.freeze_state(tmp_path)
    assert s["head"] != s["tag_commit"] and s["frozen"] is False


# --- guard, run records, approval -----------------------------------------------------------

@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setattr(wp2, "ROOT", tmp_path)
    monkeypatch.setattr(wp2, "DRY_CHECK", tmp_path / "experiments" / "wp2" / "dry" / "check.json")
    st = {"freeze": dict(FROZEN), "code": dict(CODE), "env": dict(ENV)}
    monkeypatch.setattr(wp2, "freeze_state", lambda root=None: json.loads(json.dumps(st["freeze"])))
    monkeypatch.setattr(wp2, "code_state", lambda: dict(st["code"]))
    monkeypatch.setattr(wp2, "environment_record", lambda: dict(st["env"]))
    return st


def _record_path(tmp_path, role, runner="e2"):
    return tmp_path / "experiments" / "wp2" / role / "runs" / f"{runner}.json"


def _dry_run(runner="e2", force=False, inputs=None):
    rec = wp2.guard_start(runner, "dry", force, False, inputs or {"n": 50})
    return wp2.finish_run(runner, "dry", rec, 1.0, {"outputs": {}})


def _snapshot(tmp_path, runner="e2"):
    compared = tmp_path / "experiments" / "wp2" / "dry" / "compare.json"
    compared.parent.mkdir(parents=True, exist_ok=True)
    if not compared.exists():
        compared.write_text("{}\n", encoding="utf-8")
    probe = tmp_path / "runs" / "e3prep" / "probe_val" / "ids.json"
    probe.parent.mkdir(parents=True, exist_ok=True)
    if not probe.exists():
        probe.write_text("[]\n", encoding="utf-8")
    h = lambda p: wp2.file_sha256(p)  # noqa: E731
    rel = lambda p: p.relative_to(tmp_path).as_posix()  # noqa: E731
    rp = _record_path(tmp_path, "dry", runner)
    return {"dry_records": {rel(rp): h(rp)}, "compared": {rel(compared): h(compared)},
            "probe_inputs": {rel(probe): h(probe)}}


def _approve(tmp_path, runner="e2"):
    check = {"technical_success": True, "code": {"commit": TAG}, "snapshot": _snapshot(tmp_path, runner)}
    wp2.atomic_json(wp2.DRY_CHECK, check)
    return check


def test_guard_dry_fresh_writes_incomplete_record(tmp_path, state):
    torch.use_deterministic_algorithms(False)
    rec = wp2.guard_start("e2", "dry", False, False, {"n": 50})
    assert torch.are_deterministic_algorithms_enabled()
    stored = json.loads(_record_path(tmp_path, "dry").read_text(encoding="utf-8"))
    assert stored == rec
    assert rec["complete"] is False and rec["valid"] is False and rec["note"] == wp2.DRY_NOTE
    assert rec["runner"] == "e2" and rec["role"] == "dry" and rec["inputs"] == {"n": 50}
    assert rec["environment"] == ENV and rec["code"] == CODE and rec["freeze"]["frozen"] is True


def test_guard_test_role_requires_frozen(tmp_path, state):
    _dry_run()
    _approve(tmp_path)
    state["freeze"]["frozen"] = False
    with pytest.raises(SystemExit, match="frozen"):
        wp2.guard_start("e2", "test", False, False, {})
    assert not _record_path(tmp_path, "test").exists()


def test_guard_test_role_rejects_force(tmp_path, state):
    _dry_run()
    _approve(tmp_path)
    with pytest.raises(SystemExit, match="force"):
        wp2.guard_start("e2", "test", True, False, {})


def test_guard_test_role_requires_valid_dry_record_at_tag_commit(tmp_path, state):
    with pytest.raises(SystemExit, match="dry record"):
        wp2.guard_start("e2", "test", False, False, {})
    rp = _record_path(tmp_path, "dry")
    rec = _dry_run()
    wp2.atomic_json(rp, {**rec, "valid": False, "invalid_reasons": ["freeze_end"]})
    with pytest.raises(SystemExit, match="dry record"):
        wp2.guard_start("e2", "test", False, False, {})
    wp2.atomic_json(rp, {**rec, "code": {**CODE, "commit": "b" * 40}, "code_end": {**CODE, "commit": "b" * 40}})
    with pytest.raises(SystemExit, match="not_tag_commit"):
        wp2.guard_start("e2", "test", False, False, {})
    wp2.atomic_json(rp, rec)
    _approve(tmp_path)
    out = wp2.guard_start("e2", "test", False, False, {})
    assert out["role"] == "test" and _record_path(tmp_path, "test").exists()


@pytest.mark.parametrize("check", [None, {"technical_success": False},
                                   {"technical_success": True, "code": {"commit": "other"}}])
def test_guard_test_role_requires_passing_dry_check(tmp_path, state, check):
    _dry_run()
    if check is not None:
        wp2.atomic_json(wp2.DRY_CHECK, {**check, "snapshot": _snapshot(tmp_path)})
    with pytest.raises(SystemExit, match="check"):
        wp2.guard_start("e2", "test", False, False, {})
    _approve(tmp_path)
    wp2.guard_start("e2", "test", False, False, {})
    assert _record_path(tmp_path, "test").exists()


def test_guard_requires_runner_record_in_snapshot(tmp_path, state):
    _dry_run("e2")
    _dry_run("e1")
    _approve(tmp_path, runner="e1")  # snapshot lists only e1's dry record
    with pytest.raises(SystemExit, match="e2.json"):
        wp2.guard_start("e2", "test", False, False, {})


def test_guard_rejects_stale_approval_after_dry_force(tmp_path, state):
    _dry_run()
    old = _approve(tmp_path)
    wp2.guard_start("e2", "dry", True, False, {"n": 50})
    assert not wp2.DRY_CHECK.exists()  # the dry start withdraws the approval
    wp2.finish_run("e2", "dry", json.loads(_record_path(tmp_path, "dry").read_text(encoding="utf-8")), 2.0,
                   {"outputs": {}})
    with pytest.raises(SystemExit, match="check"):
        wp2.guard_start("e2", "test", False, False, {})
    wp2.atomic_json(wp2.DRY_CHECK, old)
    with pytest.raises(SystemExit, match="experiments/wp2/dry/runs/e2.json"):
        wp2.guard_start("e2", "test", False, False, {})


def test_guard_rejects_snapshot_mismatch(tmp_path, state):
    _dry_run()
    _approve(tmp_path)
    p = tmp_path / "experiments" / "wp2" / "dry" / "compare.json"
    p.write_text("{ }\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="experiments/wp2/dry/compare.json"):
        wp2.guard_start("e2", "test", False, False, {})


def test_verify_dry_approval_requires_snapshot_groups(tmp_path, state):
    _dry_run()
    check = _approve(tmp_path)
    wp2.verify_dry_approval(check)
    for group in ("dry_records", "compared", "probe_inputs"):
        bad = {**check, "snapshot": {k: v for k, v in check["snapshot"].items() if k != group}}
        with pytest.raises(wp2.DataIntegrityError, match=group):
            wp2.verify_dry_approval(bad)
    with pytest.raises(wp2.DataIntegrityError, match="snapshot"):
        wp2.verify_dry_approval({"technical_success": True})
    (tmp_path / "runs" / "e3prep" / "probe_val" / "ids.json").unlink()
    with pytest.raises(wp2.DataIntegrityError, match="probe_val/ids.json"):
        wp2.verify_dry_approval(check)


def test_guard_complete_record_refuses_rerun(tmp_path, state):
    _dry_run()
    with pytest.raises(SystemExit):
        wp2.guard_start("e2", "dry", False, False, {"n": 50})
    with pytest.raises(SystemExit):
        wp2.guard_start("e2", "dry", False, True, {"n": 50})
    wp2.guard_start("e2", "dry", True, False, {"n": 50})  # dry --force restarts
    _dry_run(force=True)
    _approve(tmp_path)
    rec = wp2.guard_start("e2", "test", False, False, {})
    wp2.finish_run("e2", "test", rec, 1.0, {"outputs": {}})
    _approve(tmp_path)
    for force, resume in ((False, False), (False, True), (True, False)):
        with pytest.raises(SystemExit):
            wp2.guard_start("e2", "test", force, resume, {})


def test_guard_incomplete_record_requires_resume(tmp_path, state):
    wp2.guard_start("e2", "dry", False, False, {"n": 50})
    with pytest.raises(SystemExit, match="resume"):
        wp2.guard_start("e2", "dry", False, False, {"n": 50})
    with pytest.raises(SystemExit, match="resume"):
        wp2.guard_start("e1", "dry", False, True, {})  # nothing to resume


def test_guard_force_and_resume_exclusive(tmp_path, state):
    with pytest.raises(SystemExit):
        wp2.guard_start("e2", "dry", True, True, {})


@pytest.mark.parametrize("change", ["commit", "dirty", "inputs", "environment"])
def test_guard_resume_rejects_changed_code_inputs_or_environment(tmp_path, state, change):
    wp2.guard_start("e2", "dry", False, False, {"n": 50})
    inputs = {"n": 50}
    if change == "commit":
        state["code"]["commit"] = "c" * 40
    elif change == "dirty":
        state["code"]["dirty"] = True
    elif change == "inputs":
        inputs = {"n": 51}
    else:
        state["env"]["torch"] = "other"
    with pytest.raises(SystemExit):
        wp2.guard_start("e2", "dry", False, True, inputs)


def test_guard_resume_keeps_stored_fields(tmp_path, state):
    wp2.guard_start("e2", "dry", False, False, {"n": 50})
    wp2.update_run("e2", "dry", {"A_sha256": "f" * 64})
    rec = wp2.guard_start("e2", "dry", False, True, {"n": 50})
    assert rec["A_sha256"] == "f" * 64 and len(rec["resumes"]) == 1
    assert set(rec["resumes"][0]) == {"started", "environment", "code", "freeze"}
    assert json.loads(_record_path(tmp_path, "dry").read_text(encoding="utf-8")) == rec


def test_dry_start_deletes_check(tmp_path, state):
    _dry_run()
    _approve(tmp_path)
    wp2.guard_start("e3", "dry", False, False, {})
    assert not wp2.DRY_CHECK.exists()


def test_update_run_requires_incomplete_record(tmp_path, state):
    with pytest.raises(wp2.DataIntegrityError):
        wp2.update_run("e2", "dry", {"A_sha256": "x"})
    _dry_run()
    with pytest.raises(wp2.DataIntegrityError):
        wp2.update_run("e2", "dry", {"A_sha256": "x"})


def test_finish_run_valid(tmp_path, state):
    rec = _dry_run()
    assert rec["complete"] is True and rec["valid"] is True and rec["status"] == "valid"
    assert rec["invalid_reasons"] == [] and rec["seconds"] == 1.0 and rec["outputs"] == {}
    assert rec["code_end"] == CODE and rec["freeze_end"]["frozen"] is True and "finished" in rec
    assert json.loads(_record_path(tmp_path, "dry").read_text(encoding="utf-8")) == rec


def test_finish_run_invalid_when_code_changed(tmp_path, state):
    rec = wp2.guard_start("e2", "dry", False, False, {})
    state["code"]["diff_sha256"] = "d" * 64
    state["env"]["torch"] = "end"
    rec = wp2.finish_run("e2", "dry", rec, 1.0, {})
    assert rec["complete"] is True and rec["valid"] is False and "code_changed_during_run" in rec["invalid_reasons"]
    assert rec["environment_end"] == {**ENV, "torch": "end"} and rec["status"] == "freeze-violation"


def test_finish_run_invalid_when_freeze_end_not_frozen(tmp_path, state):
    rec = wp2.guard_start("e2", "dry", False, False, {})
    state["freeze"]["frozen"] = False
    rec = wp2.finish_run("e2", "dry", rec, 1.0, {})
    assert rec["valid"] is False and "freeze_end" in rec["invalid_reasons"]


def test_finish_run_identity_failure_status(tmp_path, state):
    rec = wp2.guard_start("e2", "dry", False, False, {})
    rec = wp2.finish_run("e2", "dry", rec, 1.0, {"sham_mismatch": 1}, invalid=("identity-failure",))
    assert rec["valid"] is False and rec["status"] == "identity-failure"
    assert wp2.valid_record(rec, TAG) == (False, ["identity-failure"])


def test_finish_run_rejects_reserved_extra_keys(tmp_path, state):
    rec = wp2.guard_start("e2", "dry", False, False, {})
    with pytest.raises(ValueError):
        wp2.finish_run("e2", "dry", rec, 1.0, {"valid": True})


def _complete_record():
    return {"complete": True, "freeze": dict(FROZEN), "freeze_end": dict(FROZEN), "code": dict(CODE),
            "code_end": dict(CODE), "code_changed_during_run": False, "invalid_reasons": []}


def test_valid_record_reasons():
    assert wp2.valid_record(_complete_record(), TAG) == (True, [])
    assert wp2.valid_record({**_complete_record(), "complete": False}, TAG) == (False, ["incomplete"])
    assert wp2.valid_record(_complete_record(), None) == (False, ["not_tag_commit"])
    assert wp2.valid_record({**_complete_record(), "freeze": {**FROZEN, "frozen": False}}, TAG) == (False, ["freeze_start"])
    dirty = {**CODE, "dirty": True}
    assert wp2.valid_record({**_complete_record(), "code": dirty, "code_end": dirty}, TAG) == (False, ["code_dirty"])
    assert wp2.valid_record({**_complete_record(), "code_end": dirty}, TAG) == (
        False, ["code_changed_during_run", "code_dirty"])
    r = {**_complete_record(), "resumes": [{"freeze": {**FROZEN, "frozen": False}}]}
    assert wp2.valid_record(r, TAG) == (False, ["freeze_resume"])


def test_valid_record_rejects_restored_worktree(tmp_path, state):
    rec = {**_complete_record(), "freeze_end": {**FROZEN, "frozen": False}}
    assert wp2.freeze_state()["frozen"] is True  # the worktree is frozen again now
    assert wp2.valid_record(rec, TAG) == (False, ["freeze_end"])


# --- status line, manifests, atomic writes, clearing ----------------------------------------

def test_status_line_rejects_non_technical_keys(capsys):
    with pytest.raises(ValueError):
        wp2.status_line(runner="e1", solve=0.8)
    assert capsys.readouterr().out == ""
    wp2.status_line(runner="e1", stage="gen", seconds=1.5)
    assert json.loads(capsys.readouterr().out) == {"runner": "e1", "stage": "gen", "seconds": 1.5}


def test_atomic_npy_and_npz_keep_names(tmp_path):
    wp2.atomic_npy(tmp_path / "A.npy", np.arange(3))
    wp2.atomic_npz(tmp_path / "p.npz", mean=np.ones(2))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["A.npy", "p.npz"]
    assert np.load(tmp_path / "A.npy").tolist() == [0, 1, 2]
    assert np.load(tmp_path / "p.npz")["mean"].tolist() == [1.0, 1.0]


def test_atomic_write_and_json_lf(tmp_path):
    wp2.atomic_json(tmp_path / "sub" / "x.json", {"a": 1})
    wp2.atomic_write(tmp_path / "t.md", "a\nb\n")
    assert (tmp_path / "sub" / "x.json").read_bytes() == b'{\n  "a": 1\n}\n'
    assert (tmp_path / "t.md").read_bytes() == b"a\nb\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["sub", "t.md"]


def test_manifest_and_check_manifest_detects_changed_content(tmp_path):
    a, b = tmp_path / "a.bin", tmp_path / "b.bin"
    a.write_bytes(b"aaa")
    b.write_bytes(b"bbb")
    files = {"a": a, "b": b}
    m = wp2.manifest(files)
    assert m == {"a": hashlib.sha256(b"aaa").hexdigest(), "b": hashlib.sha256(b"bbb").hexdigest()}
    wp2.check_manifest(files, m)
    b.write_bytes(b"bbc")
    with pytest.raises(wp2.DataIntegrityError, match="b"):
        wp2.check_manifest(files, m)
    b.unlink()
    with pytest.raises(wp2.DataIntegrityError, match="b"):
        wp2.check_manifest(files, m)
    with pytest.raises(wp2.DataIntegrityError, match="c"):
        wp2.check_manifest({"a": a}, {**{"a": m["a"]}, "c": m["a"]})


def test_clear_outputs_deletes_only_role_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(wp2, "ROOT", tmp_path)
    exp, raw = wp2.paths("dry")
    f = exp / "e2" / "summary.json"
    d = raw / "e2"
    f.parent.mkdir(parents=True)
    f.write_text("{}", encoding="utf-8")
    (d / "x").mkdir(parents=True)
    wp2.clear_outputs("e2", "dry", [f, d, raw / "missing.npy"])
    assert not f.exists() and not d.exists()
    outside = tmp_path / "runs" / "lock" / "test" / "ids.json"
    outside.parent.mkdir(parents=True)
    outside.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        wp2.clear_outputs("e2", "dry", [outside])
    with pytest.raises(ValueError):
        wp2.clear_outputs("e2", "dry", [exp / "runs" / "e2.json"])
    with pytest.raises(ValueError):
        wp2.clear_outputs("e2", "dry", [wp2.paths("test")[0] / "x.json"])
    assert outside.exists()
