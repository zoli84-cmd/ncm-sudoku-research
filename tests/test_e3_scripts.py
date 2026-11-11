import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

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


def test_e3_probes_and_equiv_power_end_to_end(tmp_path, monkeypatch):
    runs, out = tmp_path / "runs", tmp_path / "exp"
    _toy_runs(runs)
    mod = _load("e3_probes")
    monkeypatch.setattr(mod, "RUNS", runs); monkeypatch.setattr(mod, "OUT", out)
    monkeypatch.setattr(mod, "MODELS", runs / "models"); monkeypatch.setattr(mod, "KW", FAST)
    monkeypatch.setattr(mod, "SIZES", (4, 8)); monkeypatch.setattr(mod, "environment_record", lambda: {"git": "x"})
    monkeypatch.setattr(mod.sys, "argv", ["e3_probes.py"])
    mod.main()
    r = json.loads((out / "probes.json").read_text(encoding="utf-8"))
    st = r["stages"]
    assert {f"L{lv:02d}_linear" for lv in range(1, 13)} <= set(st)
    assert {"L02_mlp", "L06_mlp", "L12_mlp", "L02_permuted_linear", "L12_permuted_linear", "controls",
            "unit_digit", "training_size", "depth_L06", "models_L06"} <= set(st)
    assert set(st["training_size"]) == {"4", "8"} and st["training_size"]["8"]["reused"] is True
    assert set(st["depth_L06"]) == {"generated_linear", "raw_linear"}
    assert st["models_L06"]["retrain_matches"] is True
    assert len(list((runs / "models").glob("L06_linear_seed*.pt"))) == 3
    h1 = json.loads((out / "h1_diffs.json").read_text(encoding="utf-8"))
    assert h1["ids"] == [f"probe_val-{i}" for i in range(4)] and len(h1["diffs"]) == 4
    expect = np.subtract(st["controls"]["permuted_linear"]["per_puzzle"], st["L06_linear"]["per_puzzle"])
    assert np.allclose(h1["diffs"], expect)
    report = (out / "probes_report.md").read_text(encoding="utf-8")
    assert "Non-confirmatory" in report and "best epoch" in report
    with pytest.raises(SystemExit):
        mod.main()
    monkeypatch.setattr(mod.sys, "argv", ["e3_probes.py", "--resume"])
    monkeypatch.setattr(mod, "fit_cells", lambda *a, **k: pytest.fail("--resume must skip finished stages"))
    mod.main()

    eq = _load("e3_equiv_power")
    monkeypatch.setattr(eq, "RUNS", runs); monkeypatch.setattr(eq, "OUT", out)
    monkeypatch.setattr(eq, "MODELS", runs / "models"); monkeypatch.setattr(eq, "N_EQUIV", 2)
    monkeypatch.setattr(eq, "environment_record", lambda: {"git": "x"})
    monkeypatch.setattr(eq, "load_model", lambda path: None)
    monkeypatch.setattr(eq, "model_predict_fn", lambda m, probe, cache: lambda pz: np.stack(
        [candidate_mask(p) for p in pz]).astype(float))
    monkeypatch.setattr(eq, "h1_sample_size", lambda d: power.h1_sample_size(
        d, reps=5, n_boot_sim=20, ns=range(100, 201, 100)))
    monkeypatch.setattr(eq.sys, "argv", ["e3_equiv_power.py"])
    eq.main()
    e = json.loads((out / "equivariance.json").read_text(encoding="utf-8"))
    assert e["acceptable"] == 0.0 and len(e["deviation"]["all"]) == 2 and "non-confirmatory" in e["note"]
    s = json.loads((out / "sample_size_h1.json").read_text(encoding="utf-8"))
    assert "test_size" in s and "shortfall" in s and "non-confirmatory" in s["note"]
    with pytest.raises(SystemExit):
        eq.main()
    monkeypatch.setattr(eq, "load_model", lambda path: pytest.fail("--power-only must not load the model"))
    monkeypatch.setattr(eq.sys, "argv", ["e3_equiv_power.py", "--power-only"])
    eq.main()
