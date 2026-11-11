import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import torch

from ncm_sudoku import e3equiv
from ncm_sudoku.e3data import labels, save_subset
from ncm_sudoku.symmetry import apply_symmetry, random_symmetry
from sudoku_cases import P, S

ROOT = Path(__file__).resolve().parents[1]
FAST = dict(epochs=2, min_steps=1)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _onehot_states(m, puzzles, level, batch=50):
    """Toy 'model': level states = one-hot of the cell digit (10-d)."""
    assert level == 12
    return np.eye(10, dtype=np.float32)[np.asarray(puzzles)]


def _toy(runs: Path, n_tr: int = 8, n_va: int = 4) -> None:
    rng = np.random.default_rng(0)
    for name, n in (("probe_train", n_tr), ("probe_val", n_va)):
        syms = [random_symmetry(rng) for _ in range(n)]
        pz = np.stack([apply_symmetry(P, s) for s in syms])
        sol = np.stack([apply_symmetry(S, s) for s in syms])
        save_subset(runs, name, [f"{name}-{i}" for i in range(n)], pz, sol, {"solve": np.ones(n, bool)}, labels(pz))
        np.save(runs / name / "L12.npy", _onehot_states(None, pz, 12))


def _setup(mod, tmp_path, monkeypatch):
    _toy(tmp_path / "e3prep")
    monkeypatch.setattr(mod, "E3RUNS", tmp_path / "e3prep"); monkeypatch.setattr(mod, "RUNS", tmp_path / "lock_runs")
    monkeypatch.setattr(mod, "OUT", tmp_path / "exp"); monkeypatch.setattr(mod, "WHOLELAYER", tmp_path / "none.json")
    monkeypatch.setattr(mod, "K", 8); monkeypatch.setattr(mod, "KW", FAST); monkeypatch.setattr(mod, "N_EQUIV", 2)
    monkeypatch.setattr(mod, "load_model", lambda path: None)
    monkeypatch.setattr(e3equiv, "cell_level_states", _onehot_states)
    monkeypatch.setattr(mod, "environment_record", lambda: {"deterministic": torch.are_deterministic_algorithms_enabled()})
    monkeypatch.setattr(mod, "code_state", lambda: {"commit": "abc", "dirty": False, "diff_sha256": None})
    monkeypatch.setattr(mod.sys, "argv", ["lock_equiv_l12.py"])


def test_lock_equiv_l12_end_to_end(tmp_path, monkeypatch):
    mod = _load("lock_equiv_l12")
    _setup(mod, tmp_path, monkeypatch)
    torch.use_deterministic_algorithms(False)
    mod.main()
    e = json.loads((tmp_path / "exp" / "equivariance_l12.json").read_text(encoding="utf-8"))
    assert e["non_confirmatory"] is True and "exploratory" in e["note"]
    assert e["level"] == 12 and e["n"] == 2 and e["k"] == 4 and e["seed"] == 0 and e["n_predictors"] == 3
    assert e["elements_per_puzzle"] == {"all": 4, "digit": 2, "geometric": 2}
    assert set(e["mean_deviation"]) == set(e["share_within"]) == set(e["mean_brier"]) == {"all", "digit", "geometric"}
    assert e["acceptable"] >= 0 and "mean_brier_original" in e and len(e["seed_noise"]) == 2
    assert e["probe"]["config"] == [0.1, 0.001] and e["probe"]["in_dim"] == 8 + 10 + 81
    assert e["probe"]["matches_d67"] is None and e["code"]["commit"] == "abc"
    assert e["environment"]["deterministic"] is True and e["ids"] == ["probe_val-0", "probe_val-1"]
    assert set(e["seconds"]) == {"train", "equivariance"}

    # saved models and PCA reload with weights_only=True and reproduce the predictions
    probes, pca, meta = mod.load_saved(tmp_path / "lock_runs")
    assert len(probes) == 3 and meta["files"] == [f"L12_wholelayer_seed{s}.pt" for s in (0, 1, 2)]
    pz = np.load(tmp_path / "e3prep" / "probe_val" / "puzzles.npy")[:2]
    feats = lambda s: mod.whole_layer_features(s, pca)  # noqa: E731
    pred = e3equiv.model_predict_fn(None, probes[0], level=12, features=feats)(pz)
    assert pred.shape == (2, 81, 9) and np.isfinite(pred).all()

    with pytest.raises(SystemExit):
        mod.main()
    # matches_d67 against a stored whole-layer L12 result with the same per-puzzle Brier
    wl = {"val_ids": json.loads((tmp_path / "e3prep" / "probe_val" / "ids.json").read_text(encoding="utf-8")),
          "stages": {"L12": {"generated_linear": {"config": [0.1, 0.001], "per_puzzle": meta["per_puzzle"]}}}}
    (tmp_path / "wl.json").write_text(json.dumps(wl), encoding="utf-8")
    monkeypatch.setattr(mod, "WHOLELAYER", tmp_path / "wl.json")
    monkeypatch.setattr(mod.sys, "argv", ["lock_equiv_l12.py", "--force"])
    mod.main()
    e2 = json.loads((tmp_path / "exp" / "equivariance_l12.json").read_text(encoding="utf-8"))
    assert e2["probe"]["matches_d67"] is True and e2["acceptable"] == pytest.approx(e["acceptable"])


def test_lock_equiv_l12_guard(tmp_path, monkeypatch):
    mod = _load("lock_equiv_l12")
    monkeypatch.setattr(mod, "OUT", tmp_path)
    (tmp_path / "equivariance_l12.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(mod.sys, "argv", ["lock_equiv_l12.py"])
    with pytest.raises(SystemExit):
        mod.main()
