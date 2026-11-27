import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
import torch

from ncm_sudoku import e5run, subsets, wp2

# --- helpers --------------------------------------------------------------------------------


def _run_dir(tmp_path, monkeypatch):
    run_dir = {"dry": tmp_path / "runs" / "dry", "dry_perm": tmp_path / "runs" / "dry_perm",
               "test": tmp_path / "runs" / "test"}
    monkeypatch.setattr(e5run, "RUN_DIR", run_dir)
    return run_dir


def _git(cwd, *args):
    return subprocess.check_output(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                                    "-c", "tag.gpgsign=false", "-c", "core.autocrlf=false", *args],
                                   cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()


def _repos(tmp_path, monkeypatch, tag=True, extra_dirty=False):
    """A throwaway repo matching e5run.LOCK_CODE_PATHS, with its own third_party/ncm submodule
    repo, as test_wp2._repos does for wp2.freeze_state. Returns the upstream repo path."""
    _git(tmp_path, "init", "-q")
    for d in ("src", "scripts", "tests", "experiments/e5/lock", "experiments/e5/dry"):
        (tmp_path / d).mkdir(parents=True)
        (tmp_path / d / "x.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("lock\n", encoding="utf-8")
    (tmp_path / "e5_protocol_v1.md").write_text("protocol\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("third_party/\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    if tag:
        _git(tmp_path, "tag", e5run.LOCK_TAG)
    if extra_dirty:
        (tmp_path / "src" / "y.py").write_text("y = 1\n", encoding="utf-8")
    up = tmp_path / "third_party" / "ncm"
    up.mkdir(parents=True)
    _git(up, "init", "-q")
    (up / "m.py").write_text("y = 1\n", encoding="utf-8")
    _git(up, "add", ".")
    _git(up, "commit", "-q", "-m", "up")
    monkeypatch.setattr(wp2, "UPSTREAM_COMMIT", _git(up, "rev-parse", "HEAD"))
    return up


def _manifest_and_dry_record(tmp_path):
    """A manifest and an approved dry-run record that verify cleanly against files under tmp_path."""
    (tmp_path / "data").mkdir()
    f = tmp_path / "data" / "a.txt"
    f.write_bytes(b"hello")
    manifest = {"entries": [{"name": "a", "path": "data/a.txt", "format": "file",
                             "sha256": wp2.file_sha256(f), "retrieval": "n/a"}]}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    hashed = tmp_path / "data" / "b.txt"
    hashed.write_bytes(b"world")
    record = {"passed": True, "hashes": {"data/b.txt": wp2.file_sha256(hashed)}}
    record_path = tmp_path / "check.json"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    (tmp_path / "check.sha256").write_text(wp2.file_sha256(record_path), encoding="utf-8")
    return manifest_path, record_path


@pytest.fixture(autouse=True)
def _restore_threads():
    prev = torch.get_num_threads()
    yield
    torch.set_num_threads(prev)


# --- input_hashes -----------------------------------------------------------------------------


def test_input_hashes(tmp_path):
    a = tmp_path / "a.bin"
    a.write_bytes(b"one")
    b = tmp_path / "b.bin"
    b.write_bytes(b"two")
    got = e5run.input_hashes({"a": a, "b": b})
    assert got == {"a": wp2.file_sha256(a), "b": wp2.file_sha256(b)}
    assert got["a"] != got["b"]


# --- start_run / record_output / finish_run ----------------------------------------------------


def test_finished_run_is_never_rerun(tmp_path, monkeypatch):
    _run_dir(tmp_path, monkeypatch)
    e5run.start_run("dry", {"head": "h1"}, resume=False)
    e5run.finish_run("dry", "finished", {"ok": True})

    with pytest.raises(e5run.RunStateError, match="finished"):
        e5run.start_run("dry", {"head": "h1"}, resume=False)
    with pytest.raises(e5run.RunStateError, match="finished"):
        e5run.start_run("dry", {"head": "h1"}, resume=True)

    rec = json.loads((e5run.RUN_DIR["dry"] / "run.json").read_text(encoding="utf-8"))
    assert rec["status"] == "finished" and rec["summary"] == {"ok": True}
    assert not e5run.RUN_DIR["dry"].joinpath(".lock").exists()


def test_invalid_run_is_never_rerun(tmp_path, monkeypatch):
    _run_dir(tmp_path, monkeypatch)
    e5run.start_run("dry", {"head": "h1"}, resume=False)
    e5run.finish_run("dry", "invalid", {"invalid_reasons": ["non_finite"]})
    with pytest.raises(e5run.RunStateError, match="invalid"):
        e5run.start_run("dry", {"head": "h1"}, resume=False)


def test_resume_refuses_changed_inputs(tmp_path, monkeypatch):
    _run_dir(tmp_path, monkeypatch)
    e5run.start_run("dry", {"head": "h1"}, resume=False)
    # lock file from the fresh start must be released before the next start_run call in this test
    (e5run.RUN_DIR["dry"] / ".lock").unlink()
    with pytest.raises(e5run.RunStateError, match="inputs"):
        e5run.start_run("dry", {"head": "h2"}, resume=True)


def test_resume_refuses_reordered_ids_via_sha256_ids(tmp_path, monkeypatch):
    """Order is only tracked because the caller puts an order-sensitive hash (here
    `subsets.sha256_ids` of the ordered pair-id list) among `inputs`; a reordering changes that
    hash, so it is refused by the same "inputs differ" check as any other changed input."""
    _run_dir(tmp_path, monkeypatch)
    ids = ["e5pair-v1-10-0", "e5pair-v1-10-1", "e5pair-v1-10-2"]
    e5run.start_run("dry", {"pairs": subsets.sha256_ids(ids)}, resume=False)
    (e5run.RUN_DIR["dry"] / ".lock").unlink()

    reordered = [ids[1], ids[0], ids[2]]
    assert subsets.sha256_ids(reordered) != subsets.sha256_ids(ids)
    with pytest.raises(e5run.RunStateError, match="inputs"):
        e5run.start_run("dry", {"pairs": subsets.sha256_ids(reordered)}, resume=True)

    # the unchanged order resumes cleanly
    rec = e5run.start_run("dry", {"pairs": subsets.sha256_ids(ids)}, resume=True)
    assert rec["status"] == "running"


def test_resume_refuses_changed_threads(tmp_path, monkeypatch):
    _run_dir(tmp_path, monkeypatch)
    e5run.start_run("dry", {"head": "h1"}, resume=False)
    (e5run.RUN_DIR["dry"] / ".lock").unlink()
    monkeypatch.setattr(e5run.torch, "get_num_threads", lambda: 999)
    with pytest.raises(e5run.RunStateError, match="threads"):
        e5run.start_run("dry", {"head": "h1"}, resume=True)


def test_resume_refuses_changed_partial_output(tmp_path, monkeypatch):
    _run_dir(tmp_path, monkeypatch)
    e5run.start_run("dry", {"head": "h1"}, resume=False)
    out = e5run.RUN_DIR["dry"] / "stage1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    wp2.atomic_json(out, {"a": 1})
    e5run.record_output("dry", "stage1", out)
    (e5run.RUN_DIR["dry"] / ".lock").unlink()

    wp2.atomic_json(out, {"a": 2})  # tamper the recorded partial output after the fact
    with pytest.raises(e5run.RunStateError, match="stage1"):
        e5run.start_run("dry", {"head": "h1"}, resume=True)


def test_resume_refuses_missing_partial_output(tmp_path, monkeypatch):
    _run_dir(tmp_path, monkeypatch)
    e5run.start_run("dry", {"head": "h1"}, resume=False)
    out = e5run.RUN_DIR["dry"] / "stage1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    wp2.atomic_json(out, {"a": 1})
    e5run.record_output("dry", "stage1", out)
    (e5run.RUN_DIR["dry"] / ".lock").unlink()

    out.unlink()
    with pytest.raises(e5run.RunStateError, match="stage1"):
        e5run.start_run("dry", {"head": "h1"}, resume=True)


def test_resume_succeeds_with_unchanged_inputs_and_outputs(tmp_path, monkeypatch):
    _run_dir(tmp_path, monkeypatch)
    e5run.start_run("dry", {"head": "h1"}, resume=False)
    out = e5run.RUN_DIR["dry"] / "stage1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    wp2.atomic_json(out, {"a": 1})
    e5run.record_output("dry", "stage1", out)
    (e5run.RUN_DIR["dry"] / ".lock").unlink()

    rec = e5run.start_run("dry", {"head": "h1"}, resume=True)
    assert rec["status"] == "running" and "stage1" in rec["stages"]
    assert (e5run.RUN_DIR["dry"] / ".lock").is_file()


def test_single_writer_lock(tmp_path, monkeypatch):
    _run_dir(tmp_path, monkeypatch)
    e5run.start_run("dry", {"head": "h1"}, resume=False)
    lock_path = e5run.RUN_DIR["dry"] / ".lock"
    assert lock_path.is_file()
    lock_info = json.loads(lock_path.read_text(encoding="utf-8"))
    assert set(lock_info) == {"pid", "host", "started"}

    with pytest.raises(e5run.RunStateError, match="lock") as exc1:
        e5run.start_run("dry", {"head": "h1"}, resume=True)
    with pytest.raises(e5run.RunStateError, match="lock") as exc2:
        e5run.start_run("dry", {"head": "h1"}, resume=False)
    # the refusal reports the lock holder's diagnostics and the manual-recovery rule
    for exc in (exc1, exc2):
        msg = str(exc.value)
        assert str(lock_info["pid"]) in msg and lock_info["host"] in msg
        assert "confirming" in msg and "no longer running" in msg


def test_fresh_start_refuses_existing_record_without_resume(tmp_path, monkeypatch):
    _run_dir(tmp_path, monkeypatch)
    e5run.start_run("dry", {"head": "h1"}, resume=False)
    (e5run.RUN_DIR["dry"] / ".lock").unlink()
    with pytest.raises(e5run.RunStateError, match="resume"):
        e5run.start_run("dry", {"head": "h1"}, resume=False)


def test_resume_without_prior_run_refuses(tmp_path, monkeypatch):
    _run_dir(tmp_path, monkeypatch)
    with pytest.raises(e5run.RunStateError, match="resume"):
        e5run.start_run("dry", {"head": "h1"}, resume=True)


def test_unknown_mode_rejected(tmp_path, monkeypatch):
    _run_dir(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        e5run.start_run("val", {}, resume=False)


def test_record_output_requires_running_record(tmp_path, monkeypatch):
    _run_dir(tmp_path, monkeypatch)
    out = tmp_path / "x.json"
    wp2.atomic_json(out, {})
    with pytest.raises(e5run.RunStateError):
        e5run.record_output("dry", "stage1", out)

    e5run.start_run("dry", {"head": "h1"}, resume=False)
    e5run.finish_run("dry", "finished", {})
    with pytest.raises(e5run.RunStateError):
        e5run.record_output("dry", "stage1", out)


def test_finish_run_requires_running_record(tmp_path, monkeypatch):
    _run_dir(tmp_path, monkeypatch)
    with pytest.raises(e5run.RunStateError):
        e5run.finish_run("dry", "finished", {})
    with pytest.raises(ValueError):
        e5run.start_run("dry", {"head": "h1"}, resume=False)
        e5run.finish_run("dry", "bogus", {})


# --- lock_state -------------------------------------------------------------------------------


def test_lock_state_tag_head_and_clean(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch)
    s = e5run.lock_state(tmp_path)
    assert s["locked"] is True and s["tag"] == e5run.LOCK_TAG
    assert s["tag_commit"] == s["head"] == _git(tmp_path, "rev-parse", "HEAD")
    assert s["code_clean"] and s["upstream_ok"] and s["upstream_clean"]


def test_lock_state_missing_tag_not_locked(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch, tag=False)
    s = e5run.lock_state(tmp_path)
    assert s["tag_commit"] is None and s["locked"] is False


def test_lock_state_dirty_code_path_not_locked(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch, extra_dirty=True)
    s = e5run.lock_state(tmp_path)
    assert s["code_clean"] is False and s["locked"] is False


def test_lock_state_ignores_dirt_outside_code_paths(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "note.md").write_text("n\n", encoding="utf-8")
    s = e5run.lock_state(tmp_path)
    assert s["code_clean"] is True and s["locked"] is True


def test_lock_state_wrong_upstream_commit_not_locked(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch)
    monkeypatch.setattr(wp2, "UPSTREAM_COMMIT", "0" * 40)
    s = e5run.lock_state(tmp_path)
    assert s["upstream_ok"] is False and s["locked"] is False


# --- verify_manifest --------------------------------------------------------------------------


def test_verify_manifest_accepts_matching_hashes(tmp_path, monkeypatch):
    monkeypatch.setattr(e5run, "ROOT", tmp_path)
    (tmp_path / "ids.json").write_text(json.dumps(["a", "b"]), encoding="utf-8")
    arr = np.arange(9, dtype=np.uint8).reshape(1, 9)
    np.save(tmp_path / "arr.npy", arr)
    f = tmp_path / "f.bin"
    f.write_bytes(b"xyz")
    manifest = {"entries": [
        {"name": "f", "path": "f.bin", "format": "file", "sha256": wp2.file_sha256(f)},
        {"name": "ids", "path": "ids.json", "format": "sha256_ids", "sha256": subsets.sha256_ids(["a", "b"])},
        {"name": "arr", "path": "arr.npy", "format": "sha256_array", "sha256": subsets.sha256_array(arr)},
    ]}
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    e5run.verify_manifest(p)  # does not raise


def test_verify_manifest_rejects_tampered_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(e5run, "ROOT", tmp_path)
    f = tmp_path / "f.bin"
    f.write_bytes(b"xyz")
    manifest = {"entries": [{"name": "f", "path": "f.bin", "format": "file", "sha256": wp2.file_sha256(f)}]}
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    f.write_bytes(b"changed")
    with pytest.raises(e5run.DataIntegrityError, match="'f'"):
        e5run.verify_manifest(p)


def test_verify_manifest_rejects_missing_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(e5run, "ROOT", tmp_path)
    manifest = {"entries": [{"name": "gone", "path": "gone.bin", "format": "file", "sha256": "0" * 64}]}
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(e5run.DataIntegrityError, match="gone"):
        e5run.verify_manifest(p)


@pytest.mark.parametrize("bad_path", [
    "/etc/passwd",
    "../outside.bin",
    "C:\\Windows\\System32\\config\\SAM",   # drive letter, Windows-absolute
    "..\\..\\outside.bin",                  # backslash traversal, not flagged by PurePosixPath
    "\\\\host\\share\\file.bin",            # UNC path
])
def test_verify_manifest_rejects_unsafe_paths(tmp_path, monkeypatch, bad_path):
    monkeypatch.setattr(e5run, "ROOT", tmp_path)
    manifest = {"entries": [{"name": "bad", "path": bad_path, "format": "file", "sha256": "0" * 64}]}
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(e5run.DataIntegrityError, match="bad"):
        e5run.verify_manifest(p)


# --- require_lock ------------------------------------------------------------------------------


def test_require_lock_passes_at_the_lock(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch)
    monkeypatch.setattr(e5run, "ROOT", tmp_path)
    manifest_path, record_path = _manifest_and_dry_record(tmp_path)
    e5run.require_lock(manifest_path, record_path)  # does not raise


def test_require_lock_refuses_missing_tag(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch, tag=False)
    monkeypatch.setattr(e5run, "ROOT", tmp_path)
    manifest_path, record_path = _manifest_and_dry_record(tmp_path)
    with pytest.raises(e5run.LockError):
        e5run.require_lock(manifest_path, record_path)


def test_require_lock_refuses_dirty_tree(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch, extra_dirty=True)
    monkeypatch.setattr(e5run, "ROOT", tmp_path)
    manifest_path, record_path = _manifest_and_dry_record(tmp_path)
    with pytest.raises(e5run.LockError):
        e5run.require_lock(manifest_path, record_path)


def test_require_lock_refuses_manifest_mismatch(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch)
    monkeypatch.setattr(e5run, "ROOT", tmp_path)
    manifest_path, record_path = _manifest_and_dry_record(tmp_path)
    (tmp_path / "data" / "a.txt").write_bytes(b"tampered")
    with pytest.raises(e5run.DataIntegrityError):
        e5run.require_lock(manifest_path, record_path)


def test_require_lock_refuses_dry_record_not_passed(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch)
    monkeypatch.setattr(e5run, "ROOT", tmp_path)
    manifest_path, record_path = _manifest_and_dry_record(tmp_path)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["passed"] = False
    record_path.write_text(json.dumps(record), encoding="utf-8")
    (record_path.with_name("check.sha256")).write_text(wp2.file_sha256(record_path), encoding="utf-8")
    with pytest.raises(e5run.DataIntegrityError):
        e5run.require_lock(manifest_path, record_path)


def test_require_lock_refuses_tampered_dry_record_hash(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch)
    monkeypatch.setattr(e5run, "ROOT", tmp_path)
    manifest_path, record_path = _manifest_and_dry_record(tmp_path)
    (tmp_path / "data" / "b.txt").write_bytes(b"tampered")
    with pytest.raises(e5run.DataIntegrityError):
        e5run.require_lock(manifest_path, record_path)


def test_require_lock_refuses_tampered_record_file_itself(tmp_path, monkeypatch):
    _repos(tmp_path, monkeypatch)
    monkeypatch.setattr(e5run, "ROOT", tmp_path)
    manifest_path, record_path = _manifest_and_dry_record(tmp_path)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["extra"] = "tampered"
    record_path.write_text(json.dumps(record), encoding="utf-8")  # check.sha256 no longer matches
    with pytest.raises(e5run.DataIntegrityError, match="check.sha256"):
        e5run.require_lock(manifest_path, record_path)


# --- test-mode requires the lock (combined scenarios, as the brief names it) -------------------


def test_test_mode_requires_lock(tmp_path, monkeypatch):
    # no tag
    _repos(tmp_path, monkeypatch, tag=False)
    monkeypatch.setattr(e5run, "ROOT", tmp_path)
    manifest_path, record_path = _manifest_and_dry_record(tmp_path)
    with pytest.raises(e5run.LockError):
        e5run.require_lock(manifest_path, record_path)

    # dirty tree
    _git(tmp_path, "tag", e5run.LOCK_TAG)
    (tmp_path / "src" / "dirty.py").write_text("z = 1\n", encoding="utf-8")
    with pytest.raises(e5run.LockError):
        e5run.require_lock(manifest_path, record_path)
    (tmp_path / "src" / "dirty.py").unlink()

    # manifest mismatch
    (tmp_path / "data" / "a.txt").write_bytes(b"not the recorded bytes")
    with pytest.raises(e5run.DataIntegrityError):
        e5run.require_lock(manifest_path, record_path)
    (tmp_path / "data" / "a.txt").write_bytes(b"hello")

    # dry record not passed
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["passed"] = False
    record_path.write_text(json.dumps(record), encoding="utf-8")
    (record_path.with_name("check.sha256")).write_text(wp2.file_sha256(record_path), encoding="utf-8")
    with pytest.raises(e5run.DataIntegrityError):
        e5run.require_lock(manifest_path, record_path)

    # now fully fixed -> passes
    record["passed"] = True
    record_path.write_text(json.dumps(record), encoding="utf-8")
    (record_path.with_name("check.sha256")).write_text(wp2.file_sha256(record_path), encoding="utf-8")
    e5run.require_lock(manifest_path, record_path)
