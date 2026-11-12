import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from e2p2_fakes import N_TOY, TOY_LEVELS, install_fakes, toy_puzzles
from ncm_sudoku import e2p2
from ncm_sudoku.perturb import code_frequencies

ROOT = Path(__file__).resolve().parents[1]
IDS = [f"cal-{i}" for i in range(N_TOY)]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _legacy_pilot(monkeypatch) -> dict:
    """Pilot-2 output in the pre-fix layout: no no-op records, no `noop` field."""
    install_fakes(monkeypatch, [])
    pz = toy_puzzles()
    out = e2p2.run_pilot2(SimpleNamespace(levels=TOY_LEVELS), pz, pz.copy(), IDS, chunk=2)
    out["level1"] = [{k: v for k, v in r.items() if k != "noop"} for r in out["level1"] if not r["noop"]]
    out.pop("level1_noop_mismatch"); out.pop("freq_source")
    for r in out["records"]:  # the toy runs level 2 only; relabel it as the level-11 term of theta2
        r["level"] = 11
    return out


def _setup(mod, tmp_path, monkeypatch, pilot: dict):
    pz = toy_puzzles()
    A = torch.as_tensor(pz[:, 1:4].astype(np.int64))
    levels = {str(lv): {"counts": torch.bincount(A[:, sl].reshape(-1), minlength=16).tolist(), "frequencies": f.tolist()}
              for lv, (sl, f) in enumerate(zip(e2p2.level_slices(TOY_LEVELS), code_frequencies(A, TOY_LEVELS)), 1)}
    (tmp_path / "cal_freqs.json").write_text(json.dumps({"levels": levels}), encoding="utf-8")
    (tmp_path / "pilot2.json").write_text(json.dumps(pilot), encoding="utf-8")
    monkeypatch.setattr(mod, "FREQS", tmp_path / "cal_freqs.json"); monkeypatch.setattr(mod, "PILOT", tmp_path / "pilot2.json")
    monkeypatch.setattr(mod, "OUT", tmp_path / "lock" / "level1_check.json")
    monkeypatch.setattr(mod, "RAW", tmp_path / "runs" / "level1_full_batch.json")
    monkeypatch.setattr(mod, "N_CAL", N_TOY); monkeypatch.setattr(mod, "CHUNK", 2)
    monkeypatch.setattr(mod, "assert_generator_frozen", lambda: None)
    monkeypatch.setattr(mod, "generate_subset", lambda name, n: [
        SimpleNamespace(puzzle=pz[i], solution=pz[i].copy(), puzzle_id=IDS[i]) for i in range(n)])
    order = []
    monkeypatch.setattr(mod, "load_model", lambda path: order.append("model") or SimpleNamespace(levels=TOY_LEVELS))
    monkeypatch.setattr(mod, "environment_record", lambda: order.append("env") or {"env": 1})
    monkeypatch.setattr(mod, "code_state", lambda: {"commit": "abc", "dirty": False, "diff_sha256": None})
    monkeypatch.setattr(mod.sys, "argv", ["lock_level1_check.py"])
    return order


def test_lock_level1_check_matches_pilot(tmp_path, monkeypatch):
    pilot = _legacy_pilot(monkeypatch)
    mod = _load("lock_level1_check")
    order = _setup(mod, tmp_path, monkeypatch, pilot)
    mod.main()
    assert order == ["model", "env"]  # environment recorded after load_model
    out = json.loads((tmp_path / "lock" / "level1_check.json").read_text(encoding="utf-8"))
    assert "non-confirmatory" in out["note"] and out["code"]["commit"] == "abc" and out["environment"] == {"env": 1}
    c = out["comparison"]
    assert c["n_matched"] == len(pilot["level1"]) == 15 * N_TOY
    assert c["n_missing_in_pilot"] == 0 and c["n_missing_in_new"] == 0
    assert all(f["n_diff"] == 0 for f in c["fields"].values())
    assert c["fields"]["tv"]["max_abs_diff"] == 0.0 and "max_abs_diff" not in c["fields"]["solve_C"]
    assert out["level1_noop_mismatch"] == 0 and out["n_noop"] == N_TOY
    assert out["base_diff"] == {"solve_A": 0, "solve_B1": 0}
    for policy in ("frequency", "uniform"):
        t = out["theta"][policy]
        for q in ("level1_term_theta2", "theta_comp", "theta2"):
            assert t[q]["new"] == pytest.approx(t[q]["pilot"]) and t[q]["max_abs_diff"] == 0.0
            assert t[q]["n_new"] == t[q]["n_pilot"] > 0
    raw = json.loads((tmp_path / "runs" / "level1_full_batch.json").read_text(encoding="utf-8"))
    assert len(raw["level1"]) == 16 * N_TOY and raw["freq_source"] == "frozen"
    with pytest.raises(SystemExit):  # rerun guard
        mod.main()


def test_lock_level1_check_reports_forced_difference(tmp_path, monkeypatch):
    pilot = _legacy_pilot(monkeypatch)
    r = pilot["level1"][4]
    r["solve_D"] = 1 - r["solve_D"]
    r["tv"] += 0.5
    mod = _load("lock_level1_check")
    _setup(mod, tmp_path, monkeypatch, pilot)
    mod.main()
    out = json.loads((tmp_path / "lock" / "level1_check.json").read_text(encoding="utf-8"))
    f = out["comparison"]["fields"]
    assert f["solve_D"]["n_diff"] == 1 and f["tv"]["n_diff"] == 1 and f["tv"]["max_abs_diff"] == pytest.approx(0.5)
    assert f["solve_C"]["n_diff"] == 0
    assert out["comparison"]["differing"][0]["puzzle_id"] == r["puzzle_id"]
    assert out["theta"]["uniform"]["theta_comp"]["max_abs_diff"] > 0  # uniform weight 1/15 on that record
