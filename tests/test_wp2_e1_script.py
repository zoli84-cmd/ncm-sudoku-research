import functools
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from ncm_sudoku import subsets, wp2

ROOT = Path(__file__).resolve().parents[1]
TAG = "a" * 40
CODE = {"commit": TAG, "dirty": False, "diff_sha256": None}
ENV = {"python": "3.12.0", "torch": "2.x", "deterministic": True}
FROZEN = {"tag": "wp2-code", "tag_commit": TAG, "head": TAG, "code_clean": True,
          "upstream_commit": wp2.UPSTREAM_COMMIT, "upstream_ok": True, "upstream_clean": True, "frozen": True}
N_CAL = 5
N = 3  # dry-role size in these tests


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


def _fake_cal():
    rng = np.random.default_rng(1)
    return [SimpleNamespace(puzzle_id=f"cal-{i}", puzzle=rng.integers(0, 10, 81).astype(np.int8),
                            solution=rng.integers(1, 10, 81).astype(np.int8)) for i in range(N_CAL)]


def _fake_records(ids):
    return [{"puzzle_id": p, "official_exact": True, "well_formed": True, "solve": True} for p in ids]


def _setup(tmp_path, monkeypatch, record_fn=None):
    mod = _load("wp2_e1")
    monkeypatch.setattr(wp2, "ROOT", tmp_path)
    monkeypatch.setattr(wp2, "DRY_CHECK", tmp_path / "experiments" / "wp2" / "dry" / "check.json")
    monkeypatch.setattr(wp2, "freeze_state", lambda root=None: dict(FROZEN))
    monkeypatch.setattr(wp2, "code_state", lambda: dict(CODE))
    monkeypatch.setattr(wp2, "environment_record", lambda: dict(ENV))
    cal = _fake_cal()
    monkeypatch.setattr(wp2.subsets, "generate_subset", lambda name, n: cal[:n] if name == "cal" else pytest.fail())
    real_load_role = wp2.load_role
    monkeypatch.setattr(wp2, "load_role", lambda role: real_load_role(role, n_dry=N))
    monkeypatch.setattr(wp2, "verify_checkpoints", lambda d: None)
    monkeypatch.setattr(mod, "load_model", lambda d: SimpleNamespace(levels=(1, 2)))
    calls = []

    def default_records(m, puzzles, solutions, ids, batch_size=50):
        calls.append({"batch_size": batch_size, "ids": list(ids)})
        return _fake_records(ids)
    monkeypatch.setattr(mod, "e1_records", record_fn or default_records)
    exp, raw = tmp_path / "experiments" / "wp2" / "dry", tmp_path / "runs" / "wp2" / "dry"
    return SimpleNamespace(mod=mod, cal=cal, calls=calls, mp=monkeypatch,
                           record=exp / "runs" / "e1.json", raw=raw)


def _rec(env):
    return json.loads(env.record.read_text(encoding="utf-8"))


def _raw(env):
    return json.loads((env.raw / "e1.json").read_text(encoding="utf-8"))


def test_wp2_e1_dry_writes_records_and_guard(tmp_path, monkeypatch):
    env = _setup(tmp_path, monkeypatch)
    env.mod.main(["--role", "dry"])
    raw = _raw(env)
    assert raw["batch_size"] == 50 and len(raw["records"]) == len(raw["ids"])
    assert raw["role"] == "dry" and raw["note"] == wp2.DRY_NOTE
    assert raw["ids"] == [g.puzzle_id for g in env.cal[:N]]
    rec = _rec(env)
    assert rec["complete"] is True and rec["valid"] is True and rec["status"] == "valid"
    assert rec["n"] == N and rec["batch_size"] == 50
    assert rec["outputs"] == {"e1.json": wp2.file_sha256(env.raw / "e1.json")}
    with pytest.raises(SystemExit):
        env.mod.main(["--role", "dry"])  # second run: complete record refuses rerun


def test_wp2_e1_resume_restarts_cleanly(tmp_path, monkeypatch):
    def boom(m, puzzles, solutions, ids, batch_size=50):
        raise RuntimeError("simulated crash")
    env = _setup(tmp_path, monkeypatch, record_fn=boom)
    with pytest.raises(RuntimeError, match="simulated crash"):
        env.mod.main(["--role", "dry"])
    assert not (env.raw / "e1.json").exists()
    assert _rec(env)["complete"] is False

    def ok(m, puzzles, solutions, ids, batch_size=50):
        env.calls.append({"batch_size": batch_size, "ids": list(ids)})
        return _fake_records(ids)
    monkeypatch.setattr(env.mod, "e1_records", ok)
    with pytest.raises(SystemExit, match="resume"):
        env.mod.main(["--role", "dry"])  # incomplete record needs --resume
    env.mod.main(["--role", "dry", "--resume"])
    rec = _rec(env)
    assert rec["complete"] is True and rec["valid"] is True and len(rec["resumes"]) == 1
    raw = _raw(env)
    assert len(raw["records"]) == N and raw["batch_size"] == 50


def test_wp2_e1_stdout_is_technical_only(tmp_path, monkeypatch, capsys):
    env = _setup(tmp_path, monkeypatch)
    env.mod.main(["--role", "dry"])
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines
    for line in lines:
        assert set(json.loads(line)) <= set(wp2.TECHNICAL_KEYS)
    rec = _rec(env)
    assert set(rec) & {"solve", "generated", "official_exact_share"} == set()


# --- TEST role ------------------------------------------------------------------------------

def _freeze_for_test(env, tmp_path):
    """Valid dry record of the runner plus a passing dry check, so the TEST guard passes; toy TEST data."""
    env.mod.main(["--role", "dry"])
    compared = tmp_path / "experiments" / "wp2" / "dry" / "compare.json"
    compared.write_text("{}\n", encoding="utf-8")
    probe = tmp_path / "runs" / "e3prep" / "probe_val" / "ids.json"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("[]\n", encoding="utf-8")
    rel = lambda p: p.relative_to(tmp_path).as_posix()  # noqa: E731
    snap = {"dry_records": {rel(env.record): wp2.file_sha256(env.record)},
            "compared": {rel(compared): wp2.file_sha256(compared)},
            "probe_inputs": {rel(probe): wp2.file_sha256(probe)}}
    wp2.atomic_json(wp2.DRY_CHECK, {"technical_success": True, "code": {"commit": TAG}, "snapshot": snap})
    d = tmp_path / "test"
    d.mkdir()
    ids = [f"t{i}" for i in range(N)]
    rng = np.random.default_rng(2)
    p, s = rng.integers(0, 10, (N, 81)).astype(np.uint8), rng.integers(1, 10, (N, 81)).astype(np.uint8)
    (d / "ids.json").write_text(json.dumps(ids), encoding="utf-8")
    np.save(d / "puzzles.npy", p)
    np.save(d / "solutions.npy", s)
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"count": N, "ids": ids, "sha256": {
        "ids": subsets.sha256_ids(ids), "puzzles": subsets.sha256_array(p),
        "solutions": subsets.sha256_array(s)}}), encoding="utf-8")
    env.mp.setattr(wp2, "verify_test_data", functools.partial(wp2.verify_test_data, d, lock))
    exp, raw = tmp_path / "experiments" / "wp2" / "test", tmp_path / "runs" / "wp2" / "test"
    env.record, env.raw = exp / "runs" / "e1.json", raw
    return ids, p, s


def test_wp2_e1_test_role_resume_rewrites_existing_e1_json(tmp_path, monkeypatch):
    """A crash after `e1.json` is written but before `finish_run` completes must not make a
    TEST `--resume` fail: `clear_outputs` never deletes in the TEST role, so clearing on resume
    would otherwise refuse permanently over the already-written `e1.json`."""
    env = _setup(tmp_path, monkeypatch)
    ids, p, s = _freeze_for_test(env, tmp_path)
    real_finish_run = wp2.finish_run

    def boom(*a, **k):
        raise RuntimeError("simulated crash")
    monkeypatch.setattr(wp2, "finish_run", boom)
    with pytest.raises(RuntimeError, match="simulated crash"):
        env.mod.main(["--role", "test"])
    assert (env.raw / "e1.json").exists()
    assert _rec(env)["complete"] is False

    monkeypatch.setattr(wp2, "finish_run", real_finish_run)
    env.mod.main(["--role", "test", "--resume"])
    rec = _rec(env)
    assert rec["complete"] is True and rec["valid"] is True and rec["status"] == "valid"
    raw = _raw(env)
    assert raw["ids"] == ids and len(raw["records"]) == N and raw["note"] is None


def test_wp2_e1_test_role_fresh_start_over_existing_outputs_refused(tmp_path, monkeypatch):
    env = _setup(tmp_path, monkeypatch)
    _freeze_for_test(env, tmp_path)
    leftover = env.raw / "e1.json"
    leftover.parent.mkdir(parents=True, exist_ok=True)
    leftover.write_text("{}", encoding="utf-8")
    content = leftover.read_bytes()
    monkeypatch.setattr(env.mod, "load_model", lambda d: pytest.fail("model loaded over existing TEST outputs"))
    with pytest.raises(SystemExit, match="single-look"):
        env.mod.main(["--role", "test"])
    assert leftover.read_bytes() == content
    rec = _rec(env)
    assert rec["complete"] is False
    assert "outputs_started" not in rec  # the refused attempt never earned the resume marker

    # A later --resume must not treat that leftover (possibly a complete, valid prior run whose
    # record was separately lost, e.g. to `git clean`) as this run's own partial state.
    monkeypatch.setattr(env.mod, "load_model", lambda d: pytest.fail("model loaded over an unmarked leftover"))
    with pytest.raises(SystemExit, match="outputs_started"):
        env.mod.main(["--role", "test", "--resume"])
    assert leftover.read_bytes() == content
    assert _rec(env)["complete"] is False
