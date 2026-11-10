import numpy as np
import pytest

import ncm_sudoku.e2p2 as e2p2
from ncm_sudoku.e2p2 import auc_pair, cp_upper, dose_nodes, interval, puzzle_values, summarize2
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


def _rec(pid, level, dose, seed, D, eligible=True, policy="frequency"):
    return {"puzzle_id": pid, "level": level, "policy": policy, "dose": dose, "seed": seed,
            "eligible": eligible, "solve_A": 1, "solve_B": 1, "solve_C": 1, "solve_D": D,
            "well_formed_C": True, "well_formed_D": True, "tv": 0.1 * level, "tv_empty": 0.1,
            "hamming_CA": 0, "latent": 0.5, "codebook_rms": 1.0, "requant_ratio": 0.2,
            "downstream_changes_D": 0}


def _l1(pid, v, w, C, D):
    return {"puzzle_id": pid, "value": v, "w_frequency": w, "w_uniform": w, "solve_C": C, "solve_D": D,
            "well_formed_C": True, "well_formed_D": True, "tv": 0.01, "tv_empty": 0.01, "hamming_CA": 0,
            "latent": 0.1, "codebook_rms": 1.0, "requant_ratio": 0.1, "downstream_changes_D": 0}


def _toy_out():
    records = []
    for s, d in enumerate([0, 1, 1]):
        records.append(_rec("p1", 11, 1, s, d))
        records.append(_rec("p2", 11, 1, s, 1))
    for s in range(3):
        records += [_rec("p1", 2, 1, s, 1), _rec("p2", 2, 1, s, 1)]
    return {
        "freqs_level1": [1 / 16] * 16,
        "base": [{"puzzle_id": "p1", "solve_A": 1, "solve_B1": 1}, {"puzzle_id": "p2", "solve_A": 1, "solve_B1": 1}],
        "level1": [_l1("p1", 1, 0.75, 0, 0), _l1("p1", 2, 0.25, 0, 1), _l1("p2", 1, 1.0, 1, 1)],
        "records": records,
    }


def test_cp_upper_known():
    assert cp_upper(0, 300, 0.95) == pytest.approx(1 - 0.05 ** (1 / 300), rel=1e-6)
    assert cp_upper(300, 300, 0.95) == 1.0


def test_interval_switches_to_bound():
    v = np.zeros(300); v[:5] = -1
    r = interval(v, 0.95)
    assert r["method"] == "bound" and r["n_nonzero"] == 5 and r["ci"][1] - r["ci"][0] > 0
    z = interval(np.zeros(300), 0.95)
    assert z["method"] == "bound" and z["ci"][1] > 0


def test_interval_bootstrap():
    v = np.r_[np.full(50, -1.0), np.zeros(250)]
    r = interval(v, 0.95, n_boot=2000)
    assert r["method"] == "bootstrap" and r["ci"][0] < -1 / 6 < r["ci"][1] < 0


def test_auc_pair_rules():
    a = [(0.0, 0.0), (0.1, -0.1), (0.2, -0.2)]
    b = [(0.05, 0.0), (0.15, -0.3)]
    r = auc_pair(a, b)
    assert r["range"] == (0.05, 0.15) and r["auc_a"] == pytest.approx(-0.1) and r["auc_b"] == pytest.approx(-0.15)
    assert auc_pair(a, [(0.3, 0.0), (0.4, 0.0)])["reason"] == "no positive-width common range"
    assert auc_pair(a, [(0.1, 0.0), (0.1, -0.2)])["reason"] == "fewer than two distinct damage values"


def test_puzzle_values_toy():
    out = _toy_out()
    t2 = puzzle_values(out, "theta2")
    assert t2 == pytest.approx({"p1": (0.75 * -1 + 0.25 * 0) - (-1 / 3), "p2": 0.0})
    tc = puzzle_values(out, "theta_comp")
    assert tc == pytest.approx({"p1": 0.75 * (0 - 0) + 0.25 * (1 - 0) - (1 - 1), "p2": 0.0})
    assert puzzle_values(out, "theta2_prime") == pytest.approx({"p1": 0 - (-1 / 3), "p2": 0.0})


def test_puzzle_values_excludes_ineligible():
    out = _toy_out()
    out["level1"] = [dict(r, w_frequency=0.0) if r["puzzle_id"] == "p2" else r for r in out["level1"]]
    assert set(puzzle_values(out, "theta2")) == {"p1"}
    assert set(puzzle_values(out, "theta_comp")) == {"p1"}
    out = _toy_out()
    out["records"][0]["eligible"] = False  # p1, level 11, seed 0
    assert set(puzzle_values(out, "theta2")) == {"p2"}
    assert set(puzzle_values(out, "theta_comp")) == {"p1", "p2"}


def test_dose_nodes_averages_seeds_then_puzzles():
    out = _toy_out()
    out["records"].append(dict(_rec("p1", 11, 4, 0, 0), tv=0.4))
    out["records"].append(dict(_rec("p1", 11, 4, 1, 1), tv=0.6, eligible=False))
    nodes = dose_nodes(out, 11)
    assert nodes[0] == pytest.approx((1.1, (-1 / 3 + 0) / 2))
    assert nodes[1] == pytest.approx((0.4, -1.0))


def test_summarize2_toy():
    s = summarize2(_toy_out(), n_boot=200)
    assert s["non_confirmatory"] is True and len(s["freqs_level1"]) == 16
    t2 = s["contrasts"]["theta2"]["frequency"]
    assert t2["estimate"] == pytest.approx(((-0.75 + 1 / 3) + 0) / 2)
    assert t2["family"]["level"] == pytest.approx(1 - 0.05 / 3) and t2["family"]["method"] == "bound"
    assert s["contrasts"]["theta2"]["uniform"]["family"] is None
    assert s["contrasts"]["theta2_prime"]["frequency"]["tost90"]["method"] == "bound"
    assert s["equivalence_tost"] is False
    cfg = [c for c in s["configurations"] if c["level"] == 11 and c["policy"] == "frequency"][0]
    assert cfg["solve_mean"]["D"] == pytest.approx(5 / 6) and cfg["excluded_share"] == 0.0
    assert cfg["quantiles"]["tv"][2] == pytest.approx(1.1)
    assert s["level1"]["frequency"]["solve_mean"]["D"] == pytest.approx((0.25 + 1) / 2)
    assert set(s["auc"]) == {"6-11", "2-11"}


def test_summarize2_level1_damage_is_weighted():
    out = _toy_out()
    tvs = {("p1", 1): 0.1, ("p1", 2): 0.5, ("p2", 1): 0.3}
    hams = {("p1", 1): 2, ("p1", 2): None, ("p2", 1): 6}
    out["level1"] = [dict(r, tv=tvs[r["puzzle_id"], r["value"]], hamming_CA=hams[r["puzzle_id"], r["value"]],
                          w_uniform=0.5 if r["puzzle_id"] == "p1" else 1.0) for r in out["level1"]]
    s = summarize2(out, n_boot=100)["level1"]
    # frequency: p1 = .75*.1 + .25*.5 = .2, p2 = .3; uniform: p1 = .3, p2 = .3
    assert s["frequency"]["quantiles"]["tv"] == pytest.approx([0.2, 0.225, 0.25, 0.275, 0.3])
    assert s["uniform"]["quantiles"]["tv"] == pytest.approx([0.3] * 5)
    # hamming renormalized over non-None values: p1 = 2, p2 = 6
    assert s["frequency"]["quantiles"]["hamming_CA"] == pytest.approx([2, 3, 4, 5, 6])
