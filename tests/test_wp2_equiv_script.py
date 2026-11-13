import importlib.util
import json
import re
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from ncm_sudoku import e3equiv, wp2, wp2e3
from ncm_sudoku.subsets import sha256_array, sha256_ids
from test_e3_scripts import FAST, _toy_runs
from test_wp2e3 import _toy_score

ROOT = Path(__file__).resolve().parents[1]
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


def _toy_states(m, puzzles, level, batch=50):
    """Toy 'model': fixed-shape states, independent of the puzzles or the (unused) model."""
    assert level == 12
    rng = np.random.default_rng(0)
    return rng.standard_normal((len(np.asarray(puzzles)), 81, 4)).astype(np.float32)


def _build(tmp_path, monkeypatch, role: str = "dry", n_score: int = 4, seed: int = 5) -> SimpleNamespace:
    """A toy e3_fits.json/e3 run record/e3_extract run record/score set for one role, with a
    real saved wl_L12__generated probe (`wp2e3._wl(12)` + `save_stage`, K=4, dim=4)."""
    monkeypatch.setattr(wp2, "ROOT", tmp_path)
    monkeypatch.setattr(wp2, "DRY_CHECK", tmp_path / "experiments" / "wp2" / "dry" / "check.json")
    monkeypatch.setattr(wp2, "freeze_state", lambda root=None: dict(FROZEN))
    monkeypatch.setattr(wp2, "code_state", lambda: dict(CODE))
    monkeypatch.setattr(wp2, "environment_record", lambda: dict(ENV))
    monkeypatch.setattr(wp2, "verify_checkpoints", lambda d: None)
    monkeypatch.setattr(wp2e3, "K", 4)

    mod = _load("wp2_equiv")
    monkeypatch.setattr(mod, "load_model", lambda d: None)
    monkeypatch.setattr(e3equiv, "cell_level_states", _toy_states)

    runs = tmp_path / "runs" / "e3prep"
    _toy_runs(runs, dim=4)
    exp, raw = tmp_path / "experiments" / "wp2" / role, tmp_path / "runs" / "wp2" / role
    score_root = raw / "e3data"
    _toy_score(score_root, n_score, seed)
    out_dir = raw / "e3"
    sets = wp2e3.load_sets(runs, score_root, out_dir)
    fn = dict(wp2e3.STAGES)["wl_L12"]
    res = fn(sets, FAST, {})
    files = wp2e3.save_stage(out_dir, "wl_L12", res)

    fits_path = exp / "e3_fits.json"
    wp2.atomic_json(fits_path, {"files": {"wl_L12": files}})
    e3_rec_path = exp / "runs" / "e3.json"
    wp2.atomic_json(e3_rec_path, {"runner": "e3", "role": role, "complete": True, "valid": True,
                                   "fits_sha256": wp2.file_sha256(fits_path)})
    score_dir = score_root / "score"
    extract_rec_path = exp / "runs" / "e3_extract.json"
    wp2.atomic_json(extract_rec_path, {"runner": "e3_extract", "role": role, "complete": True, "valid": True,
                                        "score_manifest": wp2.manifest(
                                            {p.name: p for p in sorted(score_dir.iterdir())})})
    ids = json.loads((score_dir / "ids.json").read_text(encoding="utf-8"))
    return SimpleNamespace(mod=mod, root=tmp_path, exp=exp, raw=raw, score_dir=score_dir, ids=ids,
                           fits_path=fits_path, e3_rec_path=e3_rec_path, extract_rec_path=extract_rec_path,
                           equiv_path=exp / "equivariance.json", record_path=exp / "runs" / "equiv.json")


def _rec(env, role="dry") -> dict:
    path = env.root / "experiments" / "wp2" / role / "runs" / "equiv.json"
    return json.loads(path.read_text(encoding="utf-8"))


# --- dry role ---------------------------------------------------------------------------------

def test_wp2_equiv_fixed_tolerance_and_first_200(tmp_path, monkeypatch):
    env = _build(tmp_path, monkeypatch)
    monkeypatch.setattr(env.mod, "N_EQUIV", 2)
    env.mod.main(["--role", "dry"])
    out = json.loads(env.equiv_path.read_text(encoding="utf-8"))
    assert out["acceptable"] == 0.0116 and out["acceptable_source"] == "fixed"
    assert out["ids"] == env.ids[:2] and out["n_predictors"] == 3
    assert set(out["deviation"]) == {"all", "digit", "geometric"}
    assert out["role"] == "dry" and out["level"] == 12 and out["non_confirmatory"] is True
    assert out["note"] == wp2.DRY_NOTE and out["seed_noise_p95"] >= 0
    fits = json.loads(env.fits_path.read_text(encoding="utf-8"))
    assert isinstance(out["probe"]["config"], list) and len(out["probe"]["config"]) == 2
    assert out["probe"]["files"] == fits["files"]["wl_L12"]["generated"]
    rec = _rec(env)
    assert rec["complete"] is True and rec["valid"] is True and rec["status"] == "valid"
    assert rec["n"] == 2 and rec["outputs"] == {"equivariance.json": wp2.file_sha256(env.equiv_path)}
    assert rec["probe_files_sha256"] == out["probe"]["files"]


@pytest.mark.parametrize("case", ["missing", "incomplete", "invalid"])
def test_wp2_equiv_requires_complete_e3_record(tmp_path, monkeypatch, case):
    env = _build(tmp_path, monkeypatch)
    monkeypatch.setattr(env.mod, "N_EQUIV", 2)
    if case == "missing":
        env.e3_rec_path.unlink()
    else:
        wp2.atomic_json(env.e3_rec_path, {"runner": "e3", "role": "dry",
                                           "complete": case != "incomplete", "valid": case != "invalid",
                                           "fits_sha256": wp2.file_sha256(env.fits_path)})
    with pytest.raises(SystemExit):
        env.mod.main(["--role", "dry"])
    assert not env.record_path.exists()
    assert not env.equiv_path.exists()


def test_wp2_equiv_rejects_altered_probe_file(tmp_path, monkeypatch):
    env = _build(tmp_path, monkeypatch)
    monkeypatch.setattr(env.mod, "N_EQUIV", 2)
    p = env.raw / "e3" / "models" / "wl_L12__generated_seed1.pt"
    b = bytearray(p.read_bytes())
    b[-1] ^= 1
    p.write_bytes(bytes(b))
    with pytest.raises(SystemExit, match=re.escape("wl_L12__generated_seed1.pt")):
        env.mod.main(["--role", "dry"])
    assert not env.record_path.exists()


def test_wp2_equiv_guard(tmp_path, monkeypatch):
    env = _build(tmp_path, monkeypatch)
    monkeypatch.setattr(env.mod, "N_EQUIV", 2)
    env.mod.main(["--role", "dry"])
    with pytest.raises(SystemExit):
        env.mod.main(["--role", "dry"])  # complete record refuses rerun without --force


def test_wp2_equiv_stdout_is_technical_only(tmp_path, monkeypatch, capsys):
    env = _build(tmp_path, monkeypatch)
    monkeypatch.setattr(env.mod, "N_EQUIV", 2)
    env.mod.main(["--role", "dry"])
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines
    for line in lines:
        assert set(json.loads(line)) <= set(wp2.TECHNICAL_KEYS)
    rec = _rec(env)
    assert set(rec) & {"mean_deviation", "share_within", "deviation", "brier"} == set()


# --- TEST role ----------------------------------------------------------------------------------

def _freeze_for_test(tmp_path, monkeypatch) -> SimpleNamespace:
    """A valid dry `equiv` record plus a passing dry check, then an independent TEST e3/score
    tree with its own saved wl_L12__generated probe, so the TEST guard passes."""
    dry_env = _build(tmp_path, monkeypatch, role="dry", n_score=4, seed=5)
    monkeypatch.setattr(dry_env.mod, "N_EQUIV", 2)
    dry_env.mod.main(["--role", "dry"])
    compared = tmp_path / "experiments" / "wp2" / "dry" / "compare.json"
    wp2.atomic_json(compared, {})
    rel = lambda p: p.relative_to(tmp_path).as_posix()  # noqa: E731
    snap = {"dry_records": {rel(dry_env.record_path): wp2.file_sha256(dry_env.record_path)},
            "compared": {rel(compared): wp2.file_sha256(compared)}, "probe_inputs": {}}
    wp2.atomic_json(wp2.DRY_CHECK, {"technical_success": True, "code": {"commit": TAG}, "snapshot": snap})

    test_env = _build(tmp_path, monkeypatch, role="test", n_score=4, seed=7)
    monkeypatch.setattr(test_env.mod, "N_EQUIV", 2)
    puzzles = np.load(test_env.score_dir / "puzzles.npy", allow_pickle=False)
    monkeypatch.setattr(wp2, "TEST_SHA256", {**wp2.TEST_SHA256, "ids": sha256_ids(test_env.ids),
                                             "puzzles": sha256_array(puzzles)})
    return test_env


def test_wp2_equiv_test_interrupted_run_resumes(tmp_path, monkeypatch):
    env = _freeze_for_test(tmp_path, monkeypatch)
    real_finish_run = wp2.finish_run

    def boom(*a, **k):
        raise RuntimeError("simulated crash")
    monkeypatch.setattr(wp2, "finish_run", boom)
    with pytest.raises(RuntimeError, match="simulated crash"):
        env.mod.main(["--role", "test"])
    assert env.equiv_path.exists()
    assert _rec(env, "test")["complete"] is False

    monkeypatch.setattr(wp2, "finish_run", real_finish_run)
    env.mod.main(["--role", "test", "--resume"])
    rec = _rec(env, "test")
    assert rec["complete"] is True and rec["valid"] is True and rec["status"] == "valid"
    out = json.loads(env.equiv_path.read_text(encoding="utf-8"))
    assert out["role"] == "test" and out["note"] != wp2.DRY_NOTE


def test_wp2_equiv_test_refused_fresh_start_then_resume_keeps_outputs(tmp_path, monkeypatch):
    env = _freeze_for_test(tmp_path, monkeypatch)
    leftover = env.equiv_path
    leftover.parent.mkdir(parents=True, exist_ok=True)
    leftover.write_text("{}", encoding="utf-8")
    content = leftover.read_bytes()
    monkeypatch.setattr(env.mod, "load_model", lambda d: pytest.fail("model loaded over existing TEST outputs"))
    with pytest.raises(SystemExit, match="single-look"):
        env.mod.main(["--role", "test"])
    assert leftover.read_bytes() == content
    rec = _rec(env, "test")
    assert rec["complete"] is False and "outputs_started" not in rec

    with pytest.raises(SystemExit, match="outputs_started"):
        env.mod.main(["--role", "test", "--resume"])
    assert leftover.read_bytes() == content
    assert _rec(env, "test")["complete"] is False


def test_wp2_equiv_test_stdout_is_technical_only(tmp_path, monkeypatch, capsys):
    env = _freeze_for_test(tmp_path, monkeypatch)
    capsys.readouterr()
    env.mod.main(["--role", "test"])
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines
    for line in lines:
        assert set(json.loads(line)) <= set(wp2.TECHNICAL_KEYS)
    rec = _rec(env, "test")
    assert set(rec) & {"mean_deviation", "share_within", "deviation", "brier"} == set()
    assert rec["valid"] is True
    assert json.loads(env.equiv_path.read_text(encoding="utf-8"))["role"] == "test"
