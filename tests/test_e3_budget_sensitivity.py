import importlib.util
import json
from pathlib import Path

import torch

from test_e3_scripts import FAST, _toy_runs

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("e3_budget_sensitivity", ROOT / "scripts" / "e3_budget_sensitivity.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_configure_targets_subdir_budget_and_level6_only():
    sens = _load()
    m = sens.load_wholelayer()
    committed_out = m.OUT
    sens.configure(m)
    assert m.OUT == committed_out / "budget_sensitivity"
    assert m.KW["min_steps"] == 6000
    assert [s[0] for s in m.STAGES] == ["L06"]


def test_sensitivity_run_writes_only_to_subdir(tmp_path, monkeypatch):
    sens = _load()
    monkeypatch.setattr(sens, "MIN_STEPS", 3)
    m = sens.load_wholelayer()
    runs = tmp_path / "runs"
    _toy_runs(runs)
    m.ROOT = tmp_path
    m.RUNS, m.KW, m.K = runs, dict(FAST), 6
    sens.configure(m)
    m.environment_record = lambda: {"deterministic": torch.are_deterministic_algorithms_enabled()}
    m.code_state = lambda: {"commit": "x", "dirty": False, "diff_sha256": None}
    monkeypatch.setattr(m.sys, "argv", ["e3_budget_sensitivity.py"])
    m.main()
    out = tmp_path / "experiments" / "e3prep" / "budget_sensitivity"
    res = json.loads((out / "wholelayer.json").read_text(encoding="utf-8"))
    assert list(res["stages"]) == ["L06"]
    assert res["budget_overrides"]["min_steps"] == 3
    assert (out / "wholelayer_h1_diffs_L06.json").exists()
    assert sorted(p.name for p in (tmp_path / "experiments" / "e3prep").iterdir()) == ["budget_sensitivity"]
