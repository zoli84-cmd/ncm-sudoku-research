import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _setup(mod, tmp_path, monkeypatch):
    from ncm_sudoku.subsets import generate_subset
    calls = []

    def gen(name, n):
        calls.append(name)
        return generate_subset(name, n)
    monkeypatch.setattr(mod, "generate_subset", gen)
    monkeypatch.setattr(mod, "N_TEST", 3)
    monkeypatch.setattr(mod, "SIZES", {"gate": 2, "cal": 2, "probe_train": 2, "probe_val": 2})
    gate = generate_subset("gate", 1)[0]
    monkeypatch.setattr(mod, "load_released", lambda path: (gate.puzzle[None], gate.solution[None]))
    monkeypatch.setattr(mod, "OUT", tmp_path / "test_set.json"); monkeypatch.setattr(mod, "DATA", tmp_path / "runs" / "test")
    monkeypatch.setattr(mod, "code_state", lambda: {"commit": "abc", "dirty": False, "diff_sha256": None})
    monkeypatch.setattr(mod.sys, "argv", ["lock_test_set.py"])
    return calls


def test_hashes_are_stable_and_format_defined():
    mod = _load("lock_test_set")
    ids = ["gen-v1-6-1", "gen-v1-6-0"]
    assert mod.sha256_ids(ids) == mod.sha256_ids(list(ids))
    import hashlib
    assert mod.sha256_ids(ids) == hashlib.sha256(json.dumps(ids).encode("utf-8")).hexdigest()
    assert mod.sha256_ids(ids) != mod.sha256_ids(sorted(ids))  # generation order, not sorted
    a = np.arange(81, dtype=np.int64).reshape(1, 81) % 10
    assert mod.sha256_array(a) == mod.sha256_array(a.astype(np.uint8)) == mod.sha256_array(np.asfortranarray(a))
    assert mod.sha256_array(a) == hashlib.sha256(a.astype(np.uint8).tobytes(order="C")).hexdigest()
    assert mod.sha256_array(a) != mod.sha256_array(a[:, ::-1])


def test_lock_test_set_end_to_end_and_guard(tmp_path, monkeypatch):
    mod = _load("lock_test_set")
    calls = _setup(mod, tmp_path, monkeypatch)
    mod.main()
    assert "test" in calls
    out = json.loads((tmp_path / "test_set.json").read_text(encoding="utf-8"))
    assert out["count"] == 3 and out["seed_namespace"] == 6 and out["subset"] == "test"
    ids = json.loads((tmp_path / "runs" / "test" / "ids.json").read_text(encoding="utf-8"))
    puzzles = np.load(tmp_path / "runs" / "test" / "puzzles.npy")
    solutions = np.load(tmp_path / "runs" / "test" / "solutions.npy")
    assert ids == out["ids"] and len(ids) == 3 and puzzles.shape == solutions.shape == (3, 81)
    assert out["sha256"]["ids"] == mod.sha256_ids(ids)
    assert "generation order" in out["hash_format"]["ids"] and "sort_keys" not in out["hash_format"]["ids"]
    assert out["sha256"]["puzzles"] == mod.sha256_array(puzzles) and out["sha256"]["solutions"] == mod.sha256_array(solutions)
    scr = out["screen"]
    assert scr["n_entries"] == 1 + 8 + 3 and scr["subsets"]["test"] == 3
    # the released stand-in is the gate's first grid: one exact duplicate, outside TEST
    assert scr["exact_duplicates"] == [["released-0", "gen-v1-1-0"]]
    assert scr["test_classes"] == [] and scr["test_exact_duplicates"] == []
    assert set(out["generator"]["sha256"]) == {"generate.py", "solve.py"} and out["generator"]["numpy"]
    assert out["code"]["commit"] == "abc" and out["non_confirmatory"] is True

    first = out["sha256"]
    with pytest.raises(SystemExit):
        mod.main()
    monkeypatch.setattr(mod.sys, "argv", ["lock_test_set.py", "--force"])
    mod.main()
    assert json.loads((tmp_path / "test_set.json").read_text(encoding="utf-8"))["sha256"] == first


def test_lock_test_set_respects_frozen_generator(tmp_path, monkeypatch):
    mod = _load("lock_test_set")
    _setup(mod, tmp_path, monkeypatch)
    from ncm_sudoku import subsets
    monkeypatch.setattr(subsets, "FROZEN_NUMPY", "0.0.0")
    monkeypatch.setattr(mod, "generate_subset", subsets.generate_subset)
    with pytest.raises(RuntimeError):
        mod.main()
    assert not (tmp_path / "test_set.json").exists()
