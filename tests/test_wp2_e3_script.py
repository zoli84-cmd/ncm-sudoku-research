import importlib.util
import json
import re
import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from ncm_sudoku import e3controls, wp2, wp2e3
from ncm_sudoku.e3controls import random_features
from ncm_sudoku.subsets import sha256_array, sha256_ids
from test_e3_scripts import FAST, _toy_runs
from test_wp2e3 import _toy_score

ROOT = Path(__file__).resolve().parents[1]
TAG = "a" * 40
CODE = {"commit": TAG, "dirty": False, "diff_sha256": None}
ENV = {"python": "3.12.0", "torch": "2.x", "deterministic": True, "torch_threads": 1}
FROZEN = {"tag": "wp2-code", "tag_commit": TAG, "head": TAG, "code_clean": True,
          "upstream_commit": wp2.UPSTREAM_COMMIT, "upstream_ok": True, "upstream_clean": True, "frozen": True}
NAMES = [n for n, _ in wp2e3.STAGES]
ORIG = dict(wp2e3.STAGES)


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


def _patch(root: Path, mp):
    mod = _load("wp2_e3")
    mp.setattr(wp2, "ROOT", root)
    mp.setattr(wp2, "DRY_CHECK", root / "experiments" / "wp2" / "dry" / "check.json")
    mp.setattr(wp2, "freeze_state", lambda root=None: dict(FROZEN))
    mp.setattr(wp2, "code_state", lambda: dict(CODE))
    mp.setattr(wp2, "environment_record", lambda: dict(ENV))
    mp.setattr(wp2e3, "K", 8)
    mp.setattr(wp2e3, "SIZES", (4, 8))
    mp.setattr(wp2e3, "STAGES", list(ORIG.items()))
    mp.setattr(mod, "KW", FAST)
    mp.setattr(mod, "N_TRAIN", 8)
    exp, raw = root / "experiments" / "wp2", root / "runs" / "wp2"
    return SimpleNamespace(mod=mod, mp=mp, root=root, exp=exp, raw=raw, active=list(NAMES))


def _extract_record(env, role: str, valid=True, complete=True) -> None:
    score = env.raw / role / "e3data" / "score"
    files = {p.name: p for p in sorted(score.iterdir())}
    wp2.atomic_json(env.exp / role / "runs" / "e3_extract.json",
                    {"runner": "e3_extract", "role": role, "complete": complete, "valid": valid,
                     "score_manifest": wp2.manifest(files)})


def _make_score(env, role: str, score_n: int | None = None) -> None:
    d = env.raw / role / "e3data"
    if (d / "score").exists():
        shutil.rmtree(d / "score")
    if score_n is None:  # dry shape: score = PROBE-VAL
        shutil.copytree(env.root / "runs" / "e3prep" / "probe_val", d / "score")
    else:
        _toy_score(d, score_n, 5)
    _extract_record(env, role)


def _setup(root: Path, mp, score_n: int | None = None, stages: list[str] | None = None):
    env = _patch(root, mp)
    if stages is not None:  # a short stage list keeps the crash/resume tests fast
        env.active = list(stages)
        _set_stages(env)
    runs = root / "runs" / "e3prep"
    _toy_runs(runs)
    val_ids = json.loads((runs / "probe_val" / "ids.json").read_text(encoding="utf-8"))
    for name in ("probes.json", "wholelayer.json"):
        wp2.atomic_json(root / "experiments" / "e3prep" / name, {"val_ids": val_ids})
    _make_score(env, "dry", score_n)
    return env


def _out(env, role="dry") -> Path:
    return env.raw / role / "e3"


def _rec(env, role="dry") -> dict:
    return json.loads((env.exp / role / "runs" / "e3.json").read_text(encoding="utf-8"))


def _fits(env, role="dry") -> dict:
    return json.loads((env.exp / role / "e3_fits.json").read_text(encoding="utf-8"))


def _set_stages(env, **fns) -> None:
    env.mp.setattr(wp2e3, "STAGES", [(n, fns.get(n, ORIG[n])) for n in env.active])


def _boom(*a, **k):
    raise RuntimeError("simulated crash")


def _never(*a, **k):
    pytest.fail("stage function called")


def _crash_at(env, stage: str, role="dry", argv=()) -> None:
    _set_stages(env, **{stage: _boom})
    with pytest.raises(RuntimeError, match="simulated crash"):
        env.mod.main(["--role", role, *argv])
    _set_stages(env)


def _counter(name):
    calls = []

    def fn(*a, **k):
        calls.append(1)
        return ORIG[name](*a, **k)
    return fn, calls


def _all_fail(env) -> None:
    _set_stages(env, **{n: _never for n in env.active})

SHORT = ["wl_L06", "wl_L12", "wl_teacher_L12"]


@pytest.fixture(scope="module")
def dry_done(tmp_path_factory):
    """A complete dry run on the toy runs (score = PROBE-VAL), with its stdout lines."""
    root = tmp_path_factory.mktemp("dry_done")
    with pytest.MonkeyPatch.context() as mp:
        prev = torch.are_deterministic_algorithms_enabled()
        env = _setup(root, mp)
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            env.mod.main(["--role", "dry"])
        torch.use_deterministic_algorithms(prev)
    return root, buf.getvalue()


def _copy(dry_done, tmp_path, mp):
    root = tmp_path / "root"
    shutil.copytree(dry_done[0], root)
    return _patch(root, mp)


# --- dry role, complete runs --------------------------------------------------------------------

def test_wp2_e3_end_to_end_toy(dry_done, tmp_path, monkeypatch):
    env = _copy(dry_done, tmp_path, monkeypatch)
    fits = _fits(env)
    assert list(fits["stages"]) == NAMES
    assert (_out(env) / "models" / "wl_L12__generated_seed0.pt").exists() and _rec(env)["complete"]
    rec = _rec(env)
    assert rec["valid"] is True and rec["n_stages"] == len(NAMES)
    assert rec["outputs"] == {"e3_fits.json": rec["fits_sha256"], "e3_budget.json": rec["budget_sha256"]}
    assert rec["fits_sha256"] == wp2.file_sha256(env.exp / "dry" / "e3_fits.json")
    assert rec["inputs"] == fits["inputs"]
    assert set(rec["inputs"]["files"]) == {f"{s}/{f}" for s in ("probe_train", "probe_val", "score")
                                           for f in env.mod.INPUT_FILES}
    assert rec["inputs"]["arrays"]["score/L06.npy"] == {"shape": [4, 81, 4], "dtype": "float32"}
    assert fits["note"] == wp2.DRY_NOTE and fits["n_train"] == 8 and fits["n_val"] == 4 and fits["n_score"] == 4
    assert fits["budget_overrides"] == FAST and set(fits["seconds"]) == set(fits["stage_environment"]) == set(NAMES)
    assert not list(_out(env).rglob("*.tmp*"))


def test_wp2_e3_writes_budget_json(dry_done, tmp_path, monkeypatch):
    env = _copy(dry_done, tmp_path, monkeypatch)
    b = json.loads((env.exp / "dry" / "e3_budget.json").read_text())
    assert len(b["wl_L06"]["generated"]) == 30
    assert b["note"] == wp2.DRY_NOTE and set(b) - {"note", "role"} == set(NAMES)


def test_wp2_e3_stdout_is_technical_only(dry_done):
    lines = dry_done[1].strip().splitlines()
    assert len(lines) == len(NAMES) + 1
    for line in lines:
        assert set(json.loads(line)) <= set(wp2.TECHNICAL_KEYS)
    assert [json.loads(x)["stage"] for x in lines[:-1]] == NAMES


def test_wp2_e3_final_files_assembled_from_checkpoints(tmp_path, monkeypatch):
    env = _setup(tmp_path, monkeypatch, stages=SHORT)
    _crash_at(env, "wl_teacher_L12")
    assert not (env.exp / "dry" / "e3_fits.json").exists() and not (env.exp / "dry" / "e3_budget.json").exists()
    env.mod.main(["--role", "dry", "--resume"])
    fits = _fits(env)
    budget = json.loads((env.exp / "dry" / "e3_budget.json").read_text(encoding="utf-8"))
    stages = _out(env) / "stages"
    for name in SHORT:
        ck = json.loads((stages / f"{name}.json").read_text(encoding="utf-8"))
        done = json.loads((stages / f"{name}.done.json").read_text(encoding="utf-8"))
        assert fits["stages"][name] == ck["summary"] and budget[name] == ck["budget"]
        assert fits["files"][name] == ck["files"] and fits["stage_digests"][name] == done["checkpoint_sha256"]
        assert done == {"stage": name, "checkpoint_sha256": wp2.file_sha256(stages / f"{name}.json")}
        assert set(ck) == {"stage", "note", "summary", "budget", "files", "in_dims", "seconds", "stage_environment"}
        assert ck["note"] == wp2.DRY_NOTE
    assert _rec(env)["stage_digests"] == fits["stage_digests"]


def test_wp2_e3_dry_force_clears_stale_artifacts(dry_done, tmp_path, monkeypatch):
    env = _copy(dry_done, tmp_path, monkeypatch)
    stale = _out(env) / "preds" / "stale.npz"
    stale.write_bytes(b"x")
    env.active = SHORT
    counters = {n: _counter(n) for n in SHORT}
    _set_stages(env, **{n: c[0] for n, c in counters.items()})
    env.mod.main(["--role", "dry", "--force"])
    assert not stale.exists()
    assert all(len(c[1]) == 1 for c in counters.values())
    assert _rec(env)["complete"] is True


# --- resume -------------------------------------------------------------------------------------

def test_wp2_e3_resume_skips_finished_stages(tmp_path, monkeypatch):
    env = _setup(tmp_path, monkeypatch, stages=SHORT)
    _crash_at(env, "wl_teacher_L12")
    stages = _out(env) / "stages"
    assert (stages / "wl_L12.done.json").exists() and not (stages / "wl_teacher_L12.json").exists()
    _set_stages(env, wl_L06=_never, wl_L12=_never)
    env.mod.main(["--role", "dry", "--resume"])
    assert _rec(env)["complete"] is True and list(_fits(env)["stages"]) == SHORT


def test_wp2_e3_stage_without_artifacts_is_rerun(tmp_path, monkeypatch):
    env = _setup(tmp_path, monkeypatch, stages=SHORT)
    _crash_at(env, "wl_teacher_L12")
    (_out(env) / "preds" / "wl_L06__generated.npz").unlink()
    fn, calls = _counter("wl_L06")
    fn12, calls12 = _counter("wl_L12")
    _set_stages(env, wl_L06=fn, wl_L12=fn12)
    env.mod.main(["--role", "dry", "--resume"])
    assert calls == [1] and (_out(env) / "preds" / "wl_L06__generated.npz").exists()
    assert calls12 == [1]  # every stage after a recomputed one reruns too (cascade)
    assert _rec(env)["complete"] is True


def test_wp2_e3_recomputed_stage_cascades_to_later_stages(tmp_path, monkeypatch):
    """wl_L06_controls depends on the saved wl_L06 PCA and in_dims: once wl_L06 is recomputed on
    resume, it and every later stage rerun; earlier done stages are kept."""
    env = _setup(tmp_path, monkeypatch, stages=["wl_L12", "wl_L06", "wl_L06_controls", "wl_teacher_L12"])
    _crash_at(env, "wl_teacher_L12")
    assert (_out(env) / "stages" / "wl_L06_controls.done.json").exists()
    (_out(env) / "models" / "wl_L06__generated_seed1.pt").unlink()
    counters = {n: _counter(n) for n in ("wl_L06", "wl_L06_controls", "wl_teacher_L12")}
    _set_stages(env, wl_L12=_never, **{n: c[0] for n, c in counters.items()})
    env.mod.main(["--role", "dry", "--resume"])
    assert all(len(c[1]) == 1 for c in counters.values())
    assert _rec(env)["complete"] is True


def _rewrite(path: Path) -> None:
    a = np.load(path)
    np.save(path, ~a if a.dtype == bool else a + 1)


@pytest.mark.parametrize("target", ["probe_train/L06.npy", "probe_val/empty.npy", "score/mask.npy", "score/T06.npy"])
def test_wp2_e3_resume_rejects_altered_input_same_ids(tmp_path, monkeypatch, target):
    env = _setup(tmp_path, monkeypatch, stages=SHORT)
    _crash_at(env, "wl_teacher_L12")
    subset, name = target.split("/")
    d = env.raw / "dry" / "e3data" / "score" if subset == "score" else tmp_path / "runs" / "e3prep" / subset
    _rewrite(d / name)
    _all_fail(env)
    with pytest.raises(SystemExit, match=re.escape(target)):
        env.mod.main(["--role", "dry", "--resume"])


def test_wp2_e3_resume_rejects_altered_artifact(tmp_path, monkeypatch):
    env = _setup(tmp_path, monkeypatch, stages=SHORT)
    _crash_at(env, "wl_teacher_L12")
    p = _out(env) / "models" / "wl_L06__generated_seed0.pt"
    b = bytearray(p.read_bytes())
    b[-1] ^= 1
    p.write_bytes(bytes(b))
    _all_fail(env)
    with pytest.raises(SystemExit, match=re.escape("models/wl_L06__generated_seed0.pt")):
        env.mod.main(["--role", "dry", "--resume"])


def _mutate_checkpoint(env, edit) -> None:
    p = _out(env) / "stages" / "wl_L06.json"
    ck = json.loads(p.read_text(encoding="utf-8"))
    edit(ck)
    p.write_text(json.dumps(ck, indent=2) + "\n", encoding="utf-8")


def test_wp2_e3_resume_rejects_mutated_summary(tmp_path, monkeypatch):
    env = _setup(tmp_path, monkeypatch, stages=SHORT)
    _crash_at(env, "wl_teacher_L12")

    def edit(ck):
        ck["summary"]["generated"]["per_puzzle"][0] += 0.01
    _mutate_checkpoint(env, edit)
    _all_fail(env)
    with pytest.raises(SystemExit, match=re.escape("stages/wl_L06.json")):
        env.mod.main(["--role", "dry", "--resume"])


def test_wp2_e3_resume_rejects_mutated_budget(tmp_path, monkeypatch):
    env = _setup(tmp_path, monkeypatch, stages=SHORT)
    _crash_at(env, "wl_teacher_L12")

    def edit(ck):
        ck["budget"]["generated"][5]["n_steps"] += 1
    _mutate_checkpoint(env, edit)
    _all_fail(env)
    with pytest.raises(SystemExit, match=re.escape("stages/wl_L06.json")):
        env.mod.main(["--role", "dry", "--resume"])


@pytest.mark.parametrize("fail_at", ["before_checkpoint", "before_marker"])
def test_wp2_e3_crash_between_publication_steps(tmp_path, monkeypatch, fail_at):
    env = _setup(tmp_path, monkeypatch, stages=SHORT)
    real = wp2.atomic_json
    target = "wl_L12.json" if fail_at == "before_checkpoint" else "wl_L12.done.json"

    def failing(path, obj, indent=2):
        if Path(path).name == target:
            raise RuntimeError("simulated crash")
        return real(path, obj, indent)
    monkeypatch.setattr(wp2, "atomic_json", failing)
    with pytest.raises(RuntimeError, match="simulated crash"):
        env.mod.main(["--role", "dry"])
    monkeypatch.setattr(wp2, "atomic_json", real)
    stages = _out(env) / "stages"
    assert (stages / "wl_L06.done.json").exists() and not (stages / "wl_L12.done.json").exists()
    assert (stages / "wl_L12.json").exists() is (fail_at == "before_marker")
    fn, calls = _counter("wl_L12")
    _set_stages(env, wl_L06=_never, wl_L12=fn)
    env.mod.main(["--role", "dry", "--resume"])
    assert calls == [1] and _rec(env)["complete"] is True


def test_wp2_e3_resume_rejects_changed_environment(tmp_path, monkeypatch):
    env = _setup(tmp_path, monkeypatch, stages=SHORT)
    _crash_at(env, "wl_teacher_L12")
    monkeypatch.setattr(wp2, "environment_record", lambda: {**ENV, "torch_threads": 4})
    _all_fail(env)
    with pytest.raises(SystemExit, match="torch_threads"):
        env.mod.main(["--role", "dry", "--resume"])


def test_wp2_e3_resume_reuses_stored_pc_L06_for_training_size(tmp_path, monkeypatch):
    env = _setup(tmp_path, monkeypatch, stages=["pc_L06", "training_size"])
    _crash_at(env, "training_size")
    _set_stages(env, pc_L06=_never)
    env.mod.main(["--role", "dry", "--resume"])
    st = _fits(env)["stages"]
    assert st["training_size"]["n8"]["reused"] is True
    assert st["training_size"]["n8"]["per_puzzle"] == st["pc_L06"]["linear"]["per_puzzle"]


# --- preconditions ------------------------------------------------------------------------------

@pytest.mark.parametrize("case", ["missing", "incomplete", "invalid"])
def test_wp2_e3_requires_complete_extract_record(tmp_path, monkeypatch, case):
    env = _setup(tmp_path, monkeypatch)
    rec = env.exp / "dry" / "runs" / "e3_extract.json"
    if case == "missing":
        rec.unlink()
    else:
        _extract_record(env, "dry", complete=case != "incomplete", valid=case != "invalid")
    _all_fail(env)
    with pytest.raises(SystemExit, match="e3_extract"):
        env.mod.main(["--role", "dry"])
    assert not (env.exp / "dry" / "runs" / "e3.json").exists()


def test_wp2_e3_rejects_score_dir_not_matching_extract_manifest(tmp_path, monkeypatch):
    env = _setup(tmp_path, monkeypatch)
    _rewrite(env.raw / "dry" / "e3data" / "score" / "depth.npy")
    _all_fail(env)
    with pytest.raises(SystemExit, match=re.escape("score/depth.npy")):
        env.mod.main(["--role", "dry"])


@pytest.mark.parametrize("which", ["n_train", "probes", "wholelayer"])
def test_wp2_e3_checks_probe_ids(tmp_path, monkeypatch, which):
    env = _setup(tmp_path, monkeypatch)
    if which == "n_train":
        monkeypatch.setattr(env.mod, "N_TRAIN", 2000)
    else:
        wp2.atomic_json(tmp_path / "experiments" / "e3prep" / f"{which}.json", {"val_ids": ["x"]})
    _all_fail(env)
    with pytest.raises(SystemExit, match="PROBE"):
        env.mod.main(["--role", "dry"])


# --- distinct score set -------------------------------------------------------------------------

def test_wp2_e3_distinct_score_set_all_stages(tmp_path, monkeypatch):
    env = _setup(tmp_path, monkeypatch, score_n=3)
    out, score = _out(env), env.raw / "dry" / "e3data" / "score"
    seen_cells, seen_x = [], []
    real_fc, real_fs = e3controls.fit_cells, e3controls.fit_selected

    def spy_fc(f_tr, f_va, *a, **k):
        seen_cells.append((np.array(f_tr), None if k.get("f_score") is None else np.array(k["f_score"])))
        return real_fc(f_tr, f_va, *a, **k)

    def spy_fs(*a, **k):
        seen_x.append(a[2].clone())
        return real_fs(*a, **k)
    monkeypatch.setattr(e3controls, "fit_cells", spy_fc)
    monkeypatch.setattr(wp2e3, "fit_cells", spy_fc)
    monkeypatch.setattr(e3controls, "fit_selected", spy_fs)
    env.mod.main(["--role", "dry"])
    first = _fits(env)
    models1 = out.parent / "models1"
    shutil.copytree(out / "models", models1)

    n_cells = int(np.load(score / "empty.npy").sum())
    for name in NAMES:
        for fit, s in first["stages"][name].items():
            if fit in wp2e3.STAGE_FITS[name] or fit in ("n4", "n8"):
                assert len(s["per_puzzle"]) == 3, (name, fit)
                assert s["n_score"] == 3
    for p in sorted((out / "preds").glob("*.npz")):
        meta = json.loads((out / "models" / f"{p.stem}.json").read_text(encoding="utf-8"))
        rows = n_cells if meta["rows"] == "cell" else 3 * 27
        with np.load(p) as z:
            assert all(len(z[k]) == rows for k in z.files), p.name

    # random features: train rows, then val rows, then the 3 new score puzzles (spec ambiguity 17)
    for dim in (4, 12):
        rnd = random_features(8 + 4 + 3, seed=0, dim=dim)
        assert any(f.shape == (8, 81, dim) and np.array_equal(f, rnd[:8]) and np.array_equal(sc, rnd[12:])
                   for f, sc in seen_cells if sc is not None), dim

    # every saved model reproduces its preds file through load_probe
    n_models = 0
    for meta_path in sorted((out / "models").glob("*.json")):
        stage, fit = meta_path.stem.split("__")
        probes, pca, meta = wp2e3.load_probe(out, stage, fit)
        if not probes:
            continue
        with np.load(out / "preds" / f"{meta_path.stem}.npz") as z:
            npz = {k: z[k] for k in z.files}
        ok = False
        for X in seen_x:
            if X.shape[1] != meta["in_dim"] or len(X) != len(npz["seed0"]):
                continue
            with torch.no_grad():
                per = [p(X).numpy() for p in probes]
            if all(np.allclose(per[i], npz[f"seed{i}"]) for i in range(3)):
                ok = np.allclose(np.mean(per, axis=0), npz["mean"])
                break
        assert ok, meta_path.stem
        n_models += 1
    assert n_models > 20

    # selection is independent of the score labels
    mask = np.load(score / "mask.npy")
    empty = np.load(score / "empty.npy")
    mask[empty] = ~mask[empty]
    np.save(score / "mask.npy", mask)
    _extract_record(env, "dry")
    env.mod.main(["--role", "dry", "--force"])
    second = _fits(env)
    for name in NAMES:
        for fit, s in first["stages"][name].items():
            if isinstance(s, dict) and s.get("config") is not None:
                t = second["stages"][name][fit]
                assert t["config"] == s["config"] and t["tune_brier_mean"] == s["tune_brier_mean"], (name, fit)
    assert second["stages"]["wl_L06"]["generated"]["per_puzzle"] != first["stages"]["wl_L06"]["generated"]["per_puzzle"]
    for p in sorted(models1.glob("*_seed*.pt")):
        a, b = torch.load(p, weights_only=True), torch.load(out / "models" / p.name, weights_only=True)
        assert a.keys() == b.keys() and all(torch.equal(a[k], b[k]) for k in a), p.name


# --- TEST role ----------------------------------------------------------------------------------

def _freeze_for_test(env, dry_done=None) -> None:
    """Valid dry record of this runner plus a passing dry check with probe_inputs, then a TEST score set
    (a copy of PROBE-VAL with the §12.2 hashes patched to it) and its extract record."""
    if not (env.exp / "dry" / "runs" / "e3.json").exists():
        env.mod.main(["--role", "dry"])
    dry_record = env.exp / "dry" / "runs" / "e3.json"
    compared = env.exp / "dry" / "compare.json"
    wp2.atomic_json(compared, {})
    rel = lambda p: p.relative_to(env.root).as_posix()  # noqa: E731
    probe = {f"runs/e3prep/{k}": v for k, v in _rec(env)["inputs"]["files"].items() if k.startswith("probe_")}
    wp2.atomic_json(wp2.DRY_CHECK, {"technical_success": True, "code": {"commit": TAG}, "snapshot": {
        "dry_records": {rel(dry_record): wp2.file_sha256(dry_record)},
        "compared": {rel(compared): wp2.file_sha256(compared)}, "probe_inputs": probe}})
    _make_score(env, "test")
    score = env.raw / "test" / "e3data" / "score"
    ids = json.loads((score / "ids.json").read_text(encoding="utf-8"))
    env.mp.setattr(wp2, "TEST_SHA256", {**wp2.TEST_SHA256, "ids": sha256_ids(ids),
                                        "puzzles": sha256_array(np.load(score / "puzzles.npy"))})


def test_wp2_e3_test_fresh_start_rejects_probe_mutation_same_ids(dry_done, tmp_path, monkeypatch):
    env = _copy(dry_done, tmp_path, monkeypatch)
    _freeze_for_test(env)
    _rewrite(env.root / "runs" / "e3prep" / "probe_train" / "L06.npy")
    _all_fail(env)
    with pytest.raises(SystemExit, match=re.escape("probe_train/L06.npy")):
        env.mod.main(["--role", "test"])
    assert not (env.exp / "test" / "runs" / "e3.json").exists()


def test_wp2_e3_test_rejects_score_not_matching_lock_hashes(dry_done, tmp_path, monkeypatch):
    env = _copy(dry_done, tmp_path, monkeypatch)
    _freeze_for_test(env)
    monkeypatch.setattr(wp2, "TEST_SHA256", {**wp2.TEST_SHA256, "ids": "0" * 64})
    _all_fail(env)
    with pytest.raises(SystemExit, match="§12.2"):
        env.mod.main(["--role", "test"])


def test_wp2_e3_test_interrupted_run_resumes(dry_done, tmp_path, monkeypatch):
    env = _copy(dry_done, tmp_path, monkeypatch)
    _freeze_for_test(env)
    env.active = SHORT
    _crash_at(env, "wl_teacher_L12", role="test")
    assert _rec(env, "test")["outputs_started"] is True
    _set_stages(env, wl_L06=_never, wl_L12=_never)
    env.mod.main(["--role", "test", "--resume"])
    rec = _rec(env, "test")
    assert rec["complete"] is True and rec["valid"] is True and rec["status"] == "valid"
    assert list(_fits(env, "test")["stages"]) == SHORT and _fits(env, "test")["note"] != wp2.DRY_NOTE


def test_wp2_e3_test_resume_rejects_probe_mutation_same_ids(dry_done, tmp_path, monkeypatch):
    env = _copy(dry_done, tmp_path, monkeypatch)
    _freeze_for_test(env)
    env.active = SHORT
    _crash_at(env, "wl_teacher_L12", role="test")
    _rewrite(env.root / "runs" / "e3prep" / "probe_val" / "L12.npy")
    _all_fail(env)
    with pytest.raises(SystemExit, match=re.escape("probe_val/L12.npy")):
        env.mod.main(["--role", "test", "--resume"])
    assert _rec(env, "test")["complete"] is False


def test_wp2_e3_test_stdout_is_technical_only(dry_done, tmp_path, monkeypatch, capsys):
    env = _copy(dry_done, tmp_path, monkeypatch)
    _freeze_for_test(env)
    env.active = SHORT
    _set_stages(env)
    capsys.readouterr()
    env.mod.main(["--role", "test"])
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == len(SHORT) + 1
    for line in lines:
        assert set(json.loads(line)) <= set(wp2.TECHNICAL_KEYS)
    assert _rec(env, "test")["valid"] is True
    ck = json.loads((_out(env, "test") / "stages" / "wl_L06.json").read_text(encoding="utf-8"))
    assert "note" not in ck


def test_wp2_e3_test_refused_fresh_start_then_resume_keeps_outputs(dry_done, tmp_path, monkeypatch):
    env = _copy(dry_done, tmp_path, monkeypatch)
    _freeze_for_test(env)
    leftover = _out(env, "test") / "preds" / "x.npz"
    leftover.parent.mkdir(parents=True)
    leftover.write_bytes(b"x")
    _all_fail(env)
    with pytest.raises(SystemExit, match="single-look"):
        env.mod.main(["--role", "test"])
    assert leftover.read_bytes() == b"x" and "outputs_started" not in _rec(env, "test")
    with pytest.raises(SystemExit, match="outputs_started"):
        env.mod.main(["--role", "test", "--resume"])
    assert leftover.read_bytes() == b"x" and _rec(env, "test")["complete"] is False
