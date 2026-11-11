import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_lock_power_toy(tmp_path, monkeypatch):
    mod = _load("lock_power")
    raw, diffs = tmp_path / "pilot2.json", tmp_path / "diffs.json"
    raw.write_text("{}", encoding="utf-8")
    rng = np.random.default_rng(0)
    diffs.write_text(json.dumps({"ids": ["a"] * 300, "diffs": rng.normal(0.003, 0.004, 300).tolist()}), encoding="utf-8")
    xp = {f"p{i}": v for i, v in enumerate(np.r_[np.full(2, 1.0), np.full(2, -1.0), np.zeros(296)])}
    monkeypatch.setattr(mod, "puzzle_values", lambda out, c, policy: xp)
    monkeypatch.setattr(mod, "RAW", raw); monkeypatch.setattr(mod, "DIFFS", diffs)
    monkeypatch.setattr(mod, "OUT", tmp_path / "lock")
    monkeypatch.setattr(mod, "PARAMS", {"n": 600, "reps": 5, "n_boot_sim": 50, "seed": 0})
    mod.main()
    out = json.loads((tmp_path / "lock" / "power.json").read_text(encoding="utf-8"))
    assert set(out) >= {"note", "code", "inputs", "planning_parameters", "e2_equivalence_boundary", "h1_tost"}
    assert out["planning_parameters"]["reps"] == 5 and out["inputs"]["n_theta2_prime"] == 300
    assert set(out["e2_equivalence_boundary"]["error"]) == {"+0.03", "-0.03"}
    assert "power_at_zero" in out["h1_tost"]
    md = (tmp_path / "lock" / "power.md").read_text(encoding="utf-8")
    assert "non-confirmatory" in md and "+0.03" in md
    first = out
    mod.main()  # deterministic, safe to rerun
    again = json.loads((tmp_path / "lock" / "power.json").read_text(encoding="utf-8"))
    assert again["e2_equivalence_boundary"] == first["e2_equivalence_boundary"] and again["h1_tost"] == first["h1_tost"]
