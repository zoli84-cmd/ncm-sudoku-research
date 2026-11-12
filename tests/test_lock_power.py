import hashlib
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


def _paths(mod, tmp_path, monkeypatch, diffs_obj):
    raw, diffs = tmp_path / "pilot2.json", tmp_path / "diffs.json"
    raw.write_text("{}", encoding="utf-8")
    diffs.write_text(json.dumps(diffs_obj), encoding="utf-8")
    xp = {f"p{i}": v for i, v in enumerate(np.r_[np.full(2, 1.0), np.full(2, -1.0), np.zeros(296)])}
    monkeypatch.setattr(mod, "puzzle_values", lambda out, c, policy: xp)
    monkeypatch.setattr(mod, "RAW", raw); monkeypatch.setattr(mod, "DIFFS", diffs)
    monkeypatch.setattr(mod, "OUT", tmp_path / "lock")
    monkeypatch.setattr(mod, "code_state", lambda: {"commit": "abc", "dirty": False, "diff_sha256": None})
    return raw, diffs


def test_lock_power_toy(tmp_path, monkeypatch):
    mod = _load("lock_power")
    rng = np.random.default_rng(0)
    raw, diffs = _paths(mod, tmp_path, monkeypatch, {"quantity": "B_permuted - B_generated (toy)",
                                                     "ids": [f"v{i}" for i in range(300)],
                                                     "diffs": rng.normal(0.003, 0.004, 300).tolist()})
    monkeypatch.setattr(mod, "EQ_KW", {"reps": 5, "n_boot_sim": 50})
    monkeypatch.setattr(mod, "H1_KW", {"reps": 5, "n_boot_sim": 50})
    mod.main()
    out = json.loads((tmp_path / "lock" / "power.json").read_text(encoding="utf-8"))
    assert set(out) >= {"note", "code", "inputs", "planning_parameters", "e2_equivalence_boundary", "h1_tost"}
    assert out["planning_parameters"]["e2_equivalence_boundary"]["reps"] == 5
    assert out["planning_parameters"]["h1_tost"]["n_boot_sim"] == 50
    inp = out["inputs"]
    assert inp["n_theta2_prime"] == 300 and inp["n_h1_diffs"] == inp["n_h1_diffs_ids"] == 300
    assert inp["theta2_prime_sha256"] == hashlib.sha256(raw.read_bytes()).hexdigest()
    assert inp["h1_diffs_sha256"] == hashlib.sha256(diffs.read_bytes()).hexdigest()
    assert inp["h1_diffs_quantity"] == "B_permuted - B_generated (toy)"
    e = out["e2_equivalence_boundary"]
    assert set(e["error"]) == set(e["detail"]) == {"+0.03", "-0.03"}
    assert "power_at_zero" in out["h1_tost"]
    md = (tmp_path / "lock" / "power.md").read_text(encoding="utf-8")
    assert "non-confirmatory" in md and "+0.03" in md and "bound path" in md
    mod.main()  # deterministic, safe to rerun
    again = json.loads((tmp_path / "lock" / "power.json").read_text(encoding="utf-8"))
    assert again["e2_equivalence_boundary"] == e and again["h1_tost"] == out["h1_tost"]


def test_lock_power_rejects_misaligned_diffs(tmp_path, monkeypatch):
    mod = _load("lock_power")
    _paths(mod, tmp_path, monkeypatch, {"quantity": "q", "ids": ["a", "b"], "diffs": [0.1]})
    with pytest.raises(AssertionError):
        mod.main()
    assert not (tmp_path / "lock" / "power.json").exists()


def test_lock_power_uses_function_defaults():
    mod = _load("lock_power")
    assert mod.EQ_KW == {} and mod.H1_KW == {} and not hasattr(mod, "PARAMS")
