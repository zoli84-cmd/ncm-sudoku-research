import importlib.util
import json
from types import SimpleNamespace
from pathlib import Path

import numpy as np
import pytest
import torch

from ncm_sudoku import power
from ncm_sudoku.e3data import labels, save_subset
from ncm_sudoku.labels import candidate_mask
from ncm_sudoku.symmetry import apply_symmetry, random_symmetry
from sudoku_cases import P, S

ROOT = Path(__file__).resolve().parents[1]
FAST = dict(epochs=1, min_steps=1)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _toy_runs(runs: Path, n_tr: int = 8, n_va: int = 4, dim: int = 4) -> None:
    """Tiny runs/e3prep layout: symmetric images of P (all 30 clues), random level arrays."""
    rng = np.random.default_rng(0)
    for name, n in (("probe_train", n_tr), ("probe_val", n_va)):
        syms = [random_symmetry(rng) for _ in range(n)]
        pz = np.stack([apply_symmetry(P, s) for s in syms])
        sol = np.stack([apply_symmetry(S, s) for s in syms])
        save_subset(runs, name, [f"{name}-{i}" for i in range(n)], pz, sol, {"solve": np.ones(n, bool)}, labels(pz))
        for lv in range(1, 13):
            np.save(runs / name / f"L{lv:02d}.npy", rng.standard_normal((n, 81, dim)).astype(np.float32))
        for lv in (2, 6, 12):
            np.save(runs / name / f"T{lv:02d}.npy", rng.standard_normal((n, 81, dim)).astype(np.float32))


def test_e3_probes_guard(tmp_path, monkeypatch):
    mod = _load("e3_probes"); monkeypatch.setattr(mod, "OUT", tmp_path)
    (tmp_path / "probes.json").write_text("{}")
    with pytest.raises(SystemExit):
        mod.guard(force=False)
    mod.guard(force=True)


def test_depth_breakdown_per_class():
    mod = _load("e3_probes")
    empty = np.zeros((2, 81), bool); empty[:, :3] = True
    depth = np.zeros((2, 81), np.int16); depth[:, :3] = [1, 2, -1]
    mask = np.zeros((2, 81, 9), np.uint8)
    preds = np.zeros((6, 9)); preds[0] = 1.0  # puzzle 0, cell 0 (depth 1): Brier 1
    out = mod.depth_breakdown(preds, mask, empty, depth)
    assert out["1"] == {"brier": pytest.approx(0.5), "n_cells": 2, "n_puzzles": 2}
    assert out["2"]["brier"] == 0.0 and out["stuck"]["n_cells"] == 2
    assert out[">=4"] == {"brier": None, "n_cells": 0, "n_puzzles": 0}


def test_test_size_rule():
    mod = _load("e3_equiv_power")
    assert mod.test_size(None) is None and mod.test_size(250) == 600 and mod.test_size(640) == 700


def _env():
    return {"deterministic": torch.are_deterministic_algorithms_enabled()}


def test_e3_probes_and_equiv_power_end_to_end(tmp_path, monkeypatch):
    runs, out = tmp_path / "runs", tmp_path / "exp"
    _toy_runs(runs)
    mod = _load("e3_probes")
    monkeypatch.setattr(mod, "RUNS", runs); monkeypatch.setattr(mod, "OUT", out)
    monkeypatch.setattr(mod, "MODELS", runs / "models"); monkeypatch.setattr(mod, "KW", FAST)
    monkeypatch.setattr(mod, "SIZES", (4, 8)); monkeypatch.setattr(mod, "environment_record", _env)
    monkeypatch.setattr(mod, "code_state", lambda: {"commit": "abc", "dirty": False, "diff_sha256": None})
    monkeypatch.setattr(mod.sys, "argv", ["e3_probes.py"])
    torch.use_deterministic_algorithms(False)  # F4: main() must enable it before recording
    mod.main()
    r = json.loads((out / "probes.json").read_text(encoding="utf-8"))
    st = r["stages"]
    assert {f"L{lv:02d}_linear" for lv in range(1, 13)} <= set(st)
    assert {"L02_mlp", "L06_mlp", "L12_mlp", "L02_permuted_linear", "L12_permuted_linear", "controls",
            "unit_digit", "training_size", "depth_L06", "models_L06"} <= set(st)
    assert set(st["training_size"]) == {"4", "8"} and st["training_size"]["8"]["reused"] is True
    assert set(st["depth_L06"]) == {"aggregation", "generated_linear", "raw_linear"}
    assert st["models_L06"]["retrain_matches"] is True
    assert set(r["stage_environment"]) >= {"L01_linear", "controls"}
    assert r["stage_environment"]["controls"]["code"]["commit"] == "abc"
    assert len(st["depth_L06"]["generated_linear"]["1"]["brier_per_seed"]) == 3
    assert len(list((runs / "models").glob("L06_linear_seed*.pt"))) == 3
    h1 = json.loads((out / "h1_diffs.json").read_text(encoding="utf-8"))
    assert h1["ids"] == [f"probe_val-{i}" for i in range(4)] and len(h1["diffs"]) == 4
    expect = np.subtract(st["controls"]["permuted_linear"]["per_puzzle"], st["L06_linear"]["per_puzzle"])
    assert np.allclose(h1["diffs"], expect)
    assert r["environment"]["deterministic"] is True  # F4
    # F1: permuted control headline = scored value on unpermuted PROBE-VAL, tuning value kept apart
    pl = st["controls"]["permuted_linear"]
    assert pl["val_brier_mean"] == pytest.approx(np.nanmean(pl["per_puzzle"])) and "tune_brier_mean" in pl
    # F1/F6: theta1 preview and relative improvement at levels 2, 6, 12
    for lv in (2, 12):
        d = json.loads((out / f"h1_diffs_L{lv:02d}.json").read_text(encoding="utf-8"))
        exp = np.subtract(st[f"L{lv:02d}_permuted_linear"]["per_puzzle"], st[f"L{lv:02d}_linear"]["per_puzzle"])
        assert d["ids"] == h1["ids"] and np.allclose(d["diffs"], exp)
    for lv, perm in ((2, st["L02_permuted_linear"]), (6, pl), (12, st["L12_permuted_linear"])):
        h = r["h1"][f"L{lv:02d}"]
        dd = np.subtract(perm["per_puzzle"], st[f"L{lv:02d}_linear"]["per_puzzle"])
        assert h["mean_diff"] == pytest.approx(np.nanmean(dd))
        assert h["relative_improvement"] == pytest.approx(np.nanmean(dd) / np.nanmean(perm["per_puzzle"]))
    report = (out / "probes_report.md").read_text(encoding="utf-8")
    assert "Non-confirmatory" in report and "best epoch" in report
    assert "relative improvement" in report and "early-stopping" in report  # F6, F8
    with pytest.raises(SystemExit):
        mod.main()
    monkeypatch.setattr(mod.sys, "argv", ["e3_probes.py", "--resume"])
    monkeypatch.setattr(mod, "fit_cells", lambda *a, **k: pytest.fail("--resume must skip finished stages"))
    mod.main()

    eq = _load("e3_equiv_power")
    monkeypatch.setattr(eq, "RUNS", runs); monkeypatch.setattr(eq, "OUT", out)
    monkeypatch.setattr(eq, "MODELS", runs / "models"); monkeypatch.setattr(eq, "N_EQUIV", 2)
    monkeypatch.setattr(eq, "environment_record", lambda: {"git": "x"})
    monkeypatch.setattr(eq, "code_state", lambda: {"commit": "abc", "dirty": False, "diff_sha256": None})
    monkeypatch.setattr(eq, "load_model", lambda path: None)
    monkeypatch.setattr(eq, "model_predict_fn", lambda m, probe, cache: lambda pz: np.stack(
        [candidate_mask(p) for p in pz]).astype(float))
    monkeypatch.setattr(eq, "h1_sample_size", lambda d: power.h1_sample_size(
        d, reps=5, n_boot_sim=20, ns=range(100, 201, 100)))
    monkeypatch.setattr(eq.sys, "argv", ["e3_equiv_power.py"])
    eq.main()
    e = json.loads((out / "equivariance.json").read_text(encoding="utf-8"))
    assert e["acceptable"] == 0.0 and len(e["deviation"]["all"]) == 2 and "non-confirmatory" in e["note"]
    assert e["probe"]["retrain_matches"] is True and e["probe"]["in_dim"] == 4 + 81
    assert e["mean_brier"]["all"] == 0.0 and e["mean_brier_original"] == 0.0 and len(e["brier"]["digit"]) == 2  # F2
    assert e["code"]["commit"] == "abc"  # F3
    s = json.loads((out / "sample_size_h1.json").read_text(encoding="utf-8"))
    assert "test_size" in s and "shortfall" in s and "non-confirmatory" in s["note"]
    assert s["code"]["commit"] == "abc"  # F3
    with pytest.raises(SystemExit):
        eq.main()
    monkeypatch.setattr(eq, "load_model", lambda path: pytest.fail("--power-only must not load the model"))
    monkeypatch.setattr(eq.sys, "argv", ["e3_equiv_power.py", "--power-only"])
    eq.main()


def test_depth_breakdown_seeds_is_mean_of_per_seed():
    mod = _load("e3_probes")
    rng = np.random.default_rng(0)
    empty = rng.random((3, 81)) < 0.6
    depth = np.where(empty, rng.integers(1, 6, (3, 81)), 0).astype(np.int16)
    mask = rng.integers(0, 2, (3, 81, 9)).astype(np.uint8)
    preds = [rng.random((int(empty.sum()), 9)) for _ in range(3)]
    out = mod.depth_breakdown_seeds(preds, mask, empty, depth)
    per = [mod.depth_breakdown(p, mask, empty, depth) for p in preds]
    for c in ("1", "2", "3", ">=4"):
        assert out[c]["brier"] == pytest.approx(np.mean([x[c]["brier"] for x in per]))
        assert out[c]["brier_per_seed"] == [x[c]["brier"] for x in per]
        assert out[c]["n_cells"] == per[0][c]["n_cells"]
    assert out["stuck"]["brier"] is None


def _resume_setup(tmp_path, monkeypatch):
    runs, out = tmp_path / "runs", tmp_path / "exp"
    _toy_runs(runs)
    mod = _load("e3_probes")
    for k, v in dict(RUNS=runs, OUT=out, MODELS=runs / "models", KW=FAST, SIZES=(4, 8)).items():
        monkeypatch.setattr(mod, k, v)
    monkeypatch.setattr(mod, "environment_record", lambda: {})
    monkeypatch.setattr(mod, "code_state", lambda: {"commit": "abc", "dirty": False, "diff_sha256": None})
    monkeypatch.setattr(mod, "LEVELS", range(1, 2))  # one cheap stage
    monkeypatch.setattr(mod.sys, "argv", ["e3_probes.py"])
    mod.main()
    monkeypatch.setattr(mod.sys, "argv", ["e3_probes.py", "--resume"])
    return mod, runs


@pytest.mark.parametrize("change", ["n_val", "val_ids", "budget", "commit", "dirty"])
def test_resume_mismatch_exits(tmp_path, monkeypatch, change):
    mod, runs = _resume_setup(tmp_path, monkeypatch)
    mod.main()  # unchanged: resume is accepted
    if change == "n_val":
        _toy_runs(runs, n_va=5)
    elif change == "val_ids":
        ids = runs / "probe_val" / "ids.json"
        ids.write_text(json.dumps([f"other-{i}" for i in range(4)]))
    elif change == "budget":
        monkeypatch.setattr(mod, "KW", dict(epochs=2, min_steps=1))
    elif change == "commit":
        monkeypatch.setattr(mod, "code_state", lambda: {"commit": "def", "dirty": False, "diff_sha256": None})
    else:
        monkeypatch.setattr(mod, "code_state", lambda: {"commit": "abc", "dirty": True, "diff_sha256": "x"})
    with pytest.raises(SystemExit, match="resume"):
        mod.main()


def test_force_and_resume_rejected(tmp_path, monkeypatch):
    mod = _load("e3_probes"); monkeypatch.setattr(mod, "OUT", tmp_path)
    monkeypatch.setattr(mod.sys, "argv", ["e3_probes.py", "--force", "--resume"])
    with pytest.raises(SystemExit, match="--force"):
        mod.main()


CODE = {"commit": "abc", "dirty": False, "diff_sha256": None}


def test_e3_extract_records_code_labels_hash_and_determinism(tmp_path, monkeypatch):
    """F3/F4: extract.json carries the code state, the labels.py SHA-256 and a
    deterministic=True environment record."""
    import hashlib
    mod = _load("e3_extract")
    monkeypatch.setattr(mod, "RUNS", tmp_path / "runs"); monkeypatch.setattr(mod, "OUT", tmp_path / "extract.json")
    monkeypatch.setattr(mod, "GUARD", tmp_path / "none.npy"); monkeypatch.setattr(mod, "SUBSETS", {"probe_val": 2})
    monkeypatch.setattr(mod, "assert_generator_frozen", lambda: None)
    monkeypatch.setattr(mod, "load_model", lambda path: None)
    monkeypatch.setattr(mod, "generate_subset", lambda name, n: [
        SimpleNamespace(puzzle=np.asarray(P), solution=np.asarray(S), puzzle_id=f"{name}-{i}") for i in range(n)])
    monkeypatch.setattr(mod, "extract_streamed", lambda m, d, pz, sol, batch: np.ones(len(pz), bool))
    monkeypatch.setattr(mod, "save_subset", lambda *a, **k: None)
    monkeypatch.setattr(mod, "environment_record", _env)
    monkeypatch.setattr(mod, "code_state", lambda: CODE)
    monkeypatch.setattr(mod.sys, "argv", ["e3_extract.py"])
    torch.use_deterministic_algorithms(False)
    mod.main()
    r = json.loads((tmp_path / "extract.json").read_text(encoding="utf-8"))
    assert r["environment"]["deterministic"] is True and r["code"] == CODE
    labels_py = ROOT / "src" / "ncm_sudoku" / "labels.py"
    assert r["labels_sha256"] == hashlib.sha256(labels_py.read_bytes()).hexdigest()


def test_e3_screen_records_code(tmp_path, monkeypatch):
    mod = _load("e3_screen")
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "assert_generator_frozen", lambda: None)
    monkeypatch.setattr(mod, "load_released", lambda path: (None, []))
    monkeypatch.setattr(mod, "generate_subset", lambda name, n: [])
    monkeypatch.setattr(mod, "screen_canonical", lambda subsets, rel: {"n_entries": 0, "exact_duplicates": 0, "classes": []})
    monkeypatch.setattr(mod, "code_state", lambda: CODE)
    mod.main()
    r = json.loads((tmp_path / "experiments" / "e3prep" / "screen.json").read_text(encoding="utf-8"))
    assert r["code"] == CODE


GOLDEN = Path(__file__).parent / "golden" / "e3_scripts_toy.json"


def _script_stages(tmp: Path, mp) -> dict:
    """`stages` of scripts/e3_wholelayer.py (K = 8) and scripts/e3_probes.py (SIZES (4, 8))
    on `_toy_runs` with KW = FAST, after a JSON round trip."""
    runs = tmp / "runs"
    _toy_runs(runs)
    out = {}
    for name, result, extra in (("e3_wholelayer", "wholelayer.json", dict(K=8)),
                                ("e3_probes", "probes.json", dict(MODELS=runs / "models", SIZES=(4, 8)))):
        mod = _load(name)
        for k, v in dict(RUNS=runs, OUT=tmp / name, KW=FAST, **extra).items():
            mp.setattr(mod, k, v)
        mp.setattr(mod, "environment_record", lambda: {})
        mp.setattr(mod, "code_state", lambda: CODE)
        mp.setattr(mod.sys, "argv", [f"{name}.py"])
        mod.main()
        out[name] = json.loads((tmp / name / result).read_text(encoding="utf-8"))["stages"]
    return out


def test_e3_scripts_match_golden_after_move(tmp_path, monkeypatch):
    # tests/golden/e3_scripts_toy.json was written by _script_stages from the scripts before
    # the WP2 Task 8 helper move (wholelayer.pca_info/cell_pca_features/raw_pca_features,
    # e3controls.first_n); it pins their outputs exactly.
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert _script_stages(tmp_path, monkeypatch) == golden
