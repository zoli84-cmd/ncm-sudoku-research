import pytest

import ncm_sudoku.e2p2 as e2p2
from conftest import needs_model


@needs_model
@pytest.mark.slow
def test_run_pilot2_small(model, released, monkeypatch):
    monkeypatch.setattr(e2p2, "LEVELS_P2", (11,))
    monkeypatch.setattr(e2p2, "SEEDS_P2", (0,))
    puzzles, sols = released
    out = e2p2.run_pilot2(model, puzzles[:2], sols[:2], ["r0", "r1"], chunk=2)
    assert len(out["base"]) == 2 and all(b["solve_B1"] == b["solve_A"] for b in out["base"])
    assert len(out["level1"]) == 2 * 15
    for pid in ("r0", "r1"):
        ws = [r["w_uniform"] for r in out["level1"] if r["puzzle_id"] == pid]
        assert sum(ws) == pytest.approx(1.0)
    doses = sorted({r["dose"] for r in out["records"]})
    assert doses == [1, 4, 11, 21, 41, 67]
    assert len(out["records"]) == 6 * 2 * 1 * 2
    assert all(0.0 <= r["tv"] <= 1.0 for r in out["records"] + out["level1"])
    assert all(r["solve_B"] == r["solve_A"] for r in out["records"])
