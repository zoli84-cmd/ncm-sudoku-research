import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from ncm_sudoku import e2p2
from ncm_sudoku.perturb import code_frequencies

ROOT = Path(__file__).resolve().parents[1]
LEVELS = (1, 2, 3)  # toy model: 3 levels, 6 codes per row
A = torch.tensor([[3, 1, 1, 5, 5, 5], [3, 2, 1, 0, 5, 15], [7, 1, 2, 5, 5, 4]])


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _setup(mod, tmp_path, monkeypatch, freqs_level1):
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({"freqs_level1": freqs_level1}), encoding="utf-8")
    calls = {}
    monkeypatch.setattr(mod, "SUMMARY", summary); monkeypatch.setattr(mod, "OUT", tmp_path / "lock" / "cal_freqs.json")
    monkeypatch.setattr(mod, "N_CAL", 3)
    monkeypatch.setattr(mod, "generate_subset", lambda name, n: calls.setdefault("subset", (name, n)) and [
        SimpleNamespace(puzzle=np.zeros(81, np.int8), puzzle_id=f"cal-{i}") for i in range(n)])
    monkeypatch.setattr(mod, "assert_generator_frozen", lambda: None)
    monkeypatch.setattr(mod, "load_model", lambda path: SimpleNamespace(levels=LEVELS))

    def fake_clean(m, puzzles, chunk=50):
        calls["chunk"] = chunk
        return A
    monkeypatch.setattr(mod, "clean_codes", fake_clean)
    monkeypatch.setattr(mod, "environment_record", lambda: {"env": 1})
    monkeypatch.setattr(mod, "code_state", lambda: {"commit": "abc", "dirty": False, "diff_sha256": None})
    monkeypatch.setattr(mod.sys, "argv", ["lock_cal_freqs.py"])
    return calls


def test_lock_cal_freqs_writes_counts_and_frequencies(tmp_path, monkeypatch):
    mod = _load("lock_cal_freqs")
    calls = _setup(mod, tmp_path, monkeypatch, code_frequencies(A, LEVELS)[0].tolist())
    mod.main()
    assert calls["subset"] == ("cal", 3) and calls["chunk"] == 50
    out = json.loads((tmp_path / "lock" / "cal_freqs.json").read_text(encoding="utf-8"))
    assert out["n_cal"] == 3 and out["level1_matches_pilot"] is True and out["code"]["commit"] == "abc"
    assert set(out["levels"]) == {"1", "2", "3"}
    assert out["levels"]["3"]["counts"][5] == 6 and sum(out["levels"]["3"]["counts"]) == 9
    for lv, f in zip(("1", "2", "3"), code_frequencies(A, LEVELS)):
        assert out["levels"][lv]["frequencies"] == f.tolist()
    loaded = e2p2.load_frozen_freqs(tmp_path / "lock" / "cal_freqs.json")
    assert np.array_equal(loaded[2], code_frequencies(A, LEVELS)[1].numpy())
    with pytest.raises(SystemExit):  # rerun guard
        mod.main()
    monkeypatch.setattr(mod.sys, "argv", ["lock_cal_freqs.py", "--force"])
    mod.main()


def test_lock_cal_freqs_level1_mismatch_exits(tmp_path, monkeypatch):
    mod = _load("lock_cal_freqs")
    _setup(mod, tmp_path, monkeypatch, [1 / 16] * 16)
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code not in (None, 0)
    assert not (tmp_path / "lock" / "cal_freqs.json").exists()
