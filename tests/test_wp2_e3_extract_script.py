import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from ncm_sudoku import wp2
from ncm_sudoku.e3data import TEACHER_LEVELS
from ncm_sudoku.e3data import labels as real_labels
from sudoku_cases import P, S

ROOT = Path(__file__).resolve().parents[1]
TAG = "a" * 40
CODE = {"commit": TAG, "dirty": False, "diff_sha256": None}
ENV = {"python": "3.12.0", "torch": "2.x", "deterministic": True}
FROZEN = {"tag": "wp2-code", "tag_commit": TAG, "head": TAG, "code_clean": True,
          "upstream_commit": wp2.UPSTREAM_COMMIT, "upstream_ok": True, "upstream_clean": True, "frozen": True}
N = 3
IDS = [f"pv-{i}" for i in range(N)]
PUZZLES = np.stack([np.asarray(P, dtype=np.uint8)] * N)
SOLUTIONS = np.stack([np.asarray(S, dtype=np.uint8)] * N)


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


def _fake_extract_streamed_factory(fill=None):
    """Writes deterministic toy L*/T* arrays (L<lv>/T<lv> filled with lv, or a fill override)
    into out_dir, mirroring extract_streamed's side effect, and returns an all-True solve array."""
    fill = fill or {}

    def fake(m, out_dir, puzzles, solutions, batch=50):
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        n = len(puzzles)
        for lv in range(1, 13):
            key = f"L{lv:02d}"
            np.save(out_dir / f"{key}.npy", np.full((n, 81, 256), fill.get(key, lv), dtype=np.float32))
        for lv in TEACHER_LEVELS:
            key = f"T{lv:02d}"
            np.save(out_dir / f"{key}.npy", np.full((n, 81, 256), fill.get(key, lv), dtype=np.float32))
        return np.ones(n, dtype=bool)
    return fake


def _write_probe_val(root: Path, ids, puzzles, solutions, fill=None):
    """Reference PROBE-VAL fixture: runs/e3prep/probe_val (PROBE layout) + experiments/e3prep/probes.json
    (val_ids), matching what the script itself would produce with the default toy extractor."""
    d = root / "runs" / "e3prep" / "probe_val"
    d.mkdir(parents=True, exist_ok=True)
    lab = real_labels(puzzles)
    (d / "ids.json").write_text(json.dumps(list(ids)) + "\n", encoding="utf-8")
    np.save(d / "puzzles.npy", puzzles)
    np.save(d / "solutions.npy", solutions)
    np.save(d / "solve.npy", np.ones(len(ids), dtype=bool))
    np.save(d / "mask.npy", lab["mask"])
    np.save(d / "empty.npy", lab["empty"])
    np.save(d / "depth.npy", lab["depth"])
    _fake_extract_streamed_factory(fill)(None, d, puzzles, solutions)
    probes = root / "experiments" / "e3prep" / "probes.json"
    probes.parent.mkdir(parents=True, exist_ok=True)
    probes.write_text(json.dumps({"val_ids": list(ids)}) + "\n", encoding="utf-8")


def _setup(root: Path, monkeypatch, extract_fn=None):
    mod = _load("wp2_e3_extract")
    monkeypatch.setattr(wp2, "ROOT", root)
    monkeypatch.setattr(wp2, "DRY_CHECK", root / "experiments" / "wp2" / "dry" / "check.json")
    monkeypatch.setattr(wp2, "freeze_state", lambda root=None: dict(FROZEN))
    monkeypatch.setattr(wp2, "code_state", lambda: dict(CODE))
    monkeypatch.setattr(wp2, "environment_record", lambda: dict(ENV))
    monkeypatch.setattr(wp2, "verify_checkpoints", lambda d: None)
    monkeypatch.setattr(mod, "load_model", lambda d: None)
    monkeypatch.setattr(mod, "extract_streamed", extract_fn or _fake_extract_streamed_factory())
    exp, raw = root / "experiments" / "wp2", root / "runs" / "wp2"
    return SimpleNamespace(mod=mod, mp=monkeypatch, exp=exp, raw=raw)


def _rec(env, role="dry"):
    return json.loads((env.exp / role / "runs" / "e3_extract.json").read_text(encoding="utf-8"))


def _score_dir(env, role="dry"):
    return env.raw / role / "e3data" / "score"


def _freeze_for_test(env, root: Path):
    """Valid dry record of this runner plus a passing dry check, so the TEST guard passes."""
    _write_probe_val(root, IDS, PUZZLES, SOLUTIONS)
    env.mod.main(["--role", "dry"])
    dry_record = env.exp / "dry" / "runs" / "e3_extract.json"
    compared = root / "experiments" / "wp2" / "dry" / "compare.json"
    compared.write_text("{}\n", encoding="utf-8")
    probe = root / "runs" / "e3prep" / "probe_val" / "ids.json"
    rel = lambda p: p.relative_to(root).as_posix()  # noqa: E731
    snap = {"dry_records": {rel(dry_record): wp2.file_sha256(dry_record)},
            "compared": {rel(compared): wp2.file_sha256(compared)},
            "probe_inputs": {rel(probe): wp2.file_sha256(probe)}}
    wp2.atomic_json(wp2.DRY_CHECK, {"technical_success": True, "code": {"commit": TAG}, "snapshot": snap})


# --- dry role ---------------------------------------------------------------------------------

def test_wp2_e3_extract_dry_writes_score_subset(tmp_path, monkeypatch):
    env = _setup(tmp_path, monkeypatch)
    _write_probe_val(tmp_path, IDS, PUZZLES, SOLUTIONS)
    env.mod.main(["--role", "dry"])
    assert (_score_dir(env) / "L06.npy").exists()
    rec = _rec(env)
    assert rec["complete"] is True and rec["valid"] is True
    assert rec["n"] == N


def test_wp2_e3_extract_labels_hash_mismatch_exits_before_model(tmp_path, monkeypatch):
    env = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(env.mod, "load_model", lambda d: pytest.fail("model loaded despite a labels hash mismatch"))
    monkeypatch.setattr(env.mod, "LABELS_SHA256", "0" * 64)
    _write_probe_val(tmp_path, IDS, PUZZLES, SOLUTIONS)
    with pytest.raises(SystemExit, match="labels"):
        env.mod.main(["--role", "dry"])
    assert not _score_dir(env).exists()


def test_wp2_e3_extract_dry_compares_with_e3prep(tmp_path, monkeypatch):
    for case, fill, expect_t12_equal in (("ok", None, True), ("bad", {"T12": 999.0}, False)):
        root = tmp_path / case
        root.mkdir()
        env = _setup(root, monkeypatch)
        _write_probe_val(root, IDS, PUZZLES, SOLUTIONS, fill=fill)
        env.mod.main(["--role", "dry"])
        matches = _rec(env)["matches_e3prep"]
        assert matches["T12"]["equal"] is expect_t12_equal
        assert matches["L06"]["equal"] is True


def test_wp2_e3_extract_crash_leaves_no_score_dir(tmp_path, monkeypatch):
    def boom(m, out_dir, puzzles, solutions, batch=50):
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        raise RuntimeError("simulated crash")
    env = _setup(tmp_path, monkeypatch, extract_fn=boom)
    _write_probe_val(tmp_path, IDS, PUZZLES, SOLUTIONS)
    with pytest.raises(RuntimeError, match="simulated crash"):
        env.mod.main(["--role", "dry"])
    d = env.raw / "dry" / "e3data"
    assert not (d / "score").exists()
    assert (d / "score.tmp").exists()
    assert _rec(env)["complete"] is False

    monkeypatch.setattr(env.mod, "extract_streamed", _fake_extract_streamed_factory())
    env.mod.main(["--role", "dry", "--resume"])
    rec = _rec(env)
    assert rec["complete"] is True and rec["valid"] is True
    assert (d / "score" / "L06.npy").exists() and not (d / "score.tmp").exists()
    assert set(rec["score_manifest"]) >= {"L06.npy", "empty.npy", "mask.npy", "ids.json"}


def test_wp2_e3_extract_record_has_no_outcome(tmp_path, monkeypatch):
    env = _setup(tmp_path, monkeypatch)
    _write_probe_val(tmp_path, IDS, PUZZLES, SOLUTIONS)
    env.mod.main(["--role", "dry"])
    rec = _rec(env)
    assert "generated_solve_share" not in rec
    assert set(rec["score_manifest"]) >= {"L06.npy", "empty.npy", "mask.npy", "ids.json"}


def test_wp2_e3_extract_stdout_is_technical_only(tmp_path, monkeypatch, capsys):
    env = _setup(tmp_path, monkeypatch)
    _write_probe_val(tmp_path, IDS, PUZZLES, SOLUTIONS)
    env.mod.main(["--role", "dry"])
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines
    for line in lines:
        assert set(json.loads(line)) <= set(wp2.TECHNICAL_KEYS)


# --- compare_dirs ------------------------------------------------------------------------------

def test_compare_dirs_reports_max_abs_diff(tmp_path):
    mod = _load("wp2_e3_extract")
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    np.save(a / "x.npy", np.array([1.0, 2.0, 3.0], dtype=np.float32))
    np.save(b / "x.npy", np.array([1.0, 2.0, 5.5], dtype=np.float32))
    out = mod.compare_dirs(a, b, ["x.npy"])
    assert out["x"]["equal"] is False
    assert out["x"]["max_abs_diff"] == pytest.approx(2.5)


def test_compare_dirs_handles_bool_arrays(tmp_path):
    mod = _load("wp2_e3_extract")
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    x = np.array([True, False, True])
    y = np.array([True, False, False])
    np.save(a / "empty.npy", x)
    np.save(b / "empty.npy", y)
    np.save(a / "solve.npy", x)
    np.save(b / "solve.npy", x)
    out = mod.compare_dirs(a, b, ["empty.npy", "solve.npy"])
    assert out["empty"]["equal"] is False and out["empty"]["max_abs_diff"] == 1.0
    assert out["solve"]["equal"] is True and out["solve"]["max_abs_diff"] == 0.0


# --- TEST role -----------------------------------------------------------------------------

def test_wp2_e3_extract_test_role_resume_completes_after_crash(tmp_path, monkeypatch):
    """A crash during extraction must not block a TEST --resume: score.tmp/ and a possible stale
    score/ are discarded and never read as valid (controller ruling, Task 7)."""
    env = _setup(tmp_path, monkeypatch)
    _freeze_for_test(env, tmp_path)
    data = wp2.RoleData(ids=IDS, puzzles=PUZZLES, solutions=SOLUTIONS, source="test")
    monkeypatch.setattr(wp2, "verify_test_data", lambda *a, **k: data)

    def boom(m, out_dir, puzzles, solutions, batch=50):
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        raise RuntimeError("simulated crash")
    monkeypatch.setattr(env.mod, "extract_streamed", boom)
    with pytest.raises(RuntimeError, match="simulated crash"):
        env.mod.main(["--role", "test"])
    assert _rec(env, "test")["complete"] is False

    monkeypatch.setattr(env.mod, "extract_streamed", _fake_extract_streamed_factory())
    env.mod.main(["--role", "test", "--resume"])
    rec = _rec(env, "test")
    assert rec["complete"] is True and rec["valid"] is True and rec["status"] == "valid"
    assert (_score_dir(env, "test") / "L06.npy").exists()


def test_wp2_e3_extract_test_role_fresh_start_over_existing_outputs_refused(tmp_path, monkeypatch):
    env = _setup(tmp_path, monkeypatch)
    _freeze_for_test(env, tmp_path)
    data = wp2.RoleData(ids=IDS, puzzles=PUZZLES, solutions=SOLUTIONS, source="test")
    monkeypatch.setattr(wp2, "verify_test_data", lambda *a, **k: data)
    leftover = _score_dir(env, "test")
    leftover.mkdir(parents=True, exist_ok=True)
    (leftover / "marker.npy").write_bytes(b"x")
    monkeypatch.setattr(env.mod, "load_model", lambda d: pytest.fail("model loaded over existing TEST outputs"))
    with pytest.raises(SystemExit, match="single-look"):
        env.mod.main(["--role", "test"])
    assert (leftover / "marker.npy").exists()
    rec = _rec(env, "test")
    assert rec["complete"] is False
    assert "outputs_started" not in rec  # the refused attempt never earned the resume marker

    # A later --resume must not treat that leftover (possibly a complete, valid prior run whose
    # record was separately lost, e.g. to `git clean`) as this run's own partial state.
    monkeypatch.setattr(env.mod, "load_model", lambda d: pytest.fail("model loaded over an unmarked leftover"))
    with pytest.raises(SystemExit, match="outputs_started"):
        env.mod.main(["--role", "test", "--resume"])
    assert (leftover / "marker.npy").exists()
    assert _rec(env, "test")["complete"] is False


def test_wp2_e3_extract_test_role_resume_republishes_stale_score_dir(tmp_path, monkeypatch):
    """A crash between the rename to score/ and finish_run must not block a TEST --resume: the
    stale, fully-populated score/ is still this run's own (the marker was set at this run's own
    fresh start) and gets discarded and rewritten, not treated as already valid."""
    env = _setup(tmp_path, monkeypatch)
    _freeze_for_test(env, tmp_path)
    data = wp2.RoleData(ids=IDS, puzzles=PUZZLES, solutions=SOLUTIONS, source="test")
    monkeypatch.setattr(wp2, "verify_test_data", lambda *a, **k: data)
    real_finish_run = wp2.finish_run

    def boom(*a, **k):
        raise RuntimeError("simulated crash after rename")
    monkeypatch.setattr(wp2, "finish_run", boom)
    with pytest.raises(RuntimeError, match="simulated crash after rename"):
        env.mod.main(["--role", "test"])
    assert (_score_dir(env, "test") / "L06.npy").exists()  # the rename succeeded before the crash
    assert _rec(env, "test")["complete"] is False

    monkeypatch.setattr(wp2, "finish_run", real_finish_run)
    env.mod.main(["--role", "test", "--resume"])
    rec = _rec(env, "test")
    assert rec["complete"] is True and rec["valid"] is True and rec["status"] == "valid"
    assert (_score_dir(env, "test") / "L06.npy").exists()
