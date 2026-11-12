import math

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
    for r in out["records"] + out["level1"]:
        assert math.isfinite(r["tv"]) and 0.0 <= r["tv"] <= 1.0
        assert "hamming_CA_empty" in r and (r["hamming_CA_empty"] is None) == (r["hamming_CA"] is None)
        if not r["well_formed_C"]:  # hamming needs both C and A well formed
            assert r["hamming_CA"] is None


def _rec(pid, level, dose, seed, D, eligible=True, policy="frequency"):
    return {"puzzle_id": pid, "level": level, "policy": policy, "dose": dose, "seed": seed,
            "eligible": eligible, "solve_A": 1, "solve_B": 1, "solve_C": 1, "solve_D": D,
            "well_formed_C": True, "well_formed_D": True, "tv": 0.1 * level, "tv_empty": 0.1,
            "hamming_CA": 0, "hamming_CA_empty": 0, "latent": 0.5, "codebook_rms": 1.0, "requant_ratio": 0.2,
            "downstream_changes_D": 0}


def _l1(pid, v, w, C, D):
    return {"puzzle_id": pid, "value": v, "w_frequency": w, "w_uniform": w, "solve_C": C, "solve_D": D,
            "well_formed_C": True, "well_formed_D": True, "tv": 0.01, "tv_empty": 0.01, "hamming_CA": 0,
            "hamming_CA_empty": 0, "latent": 0.1, "codebook_rms": 1.0, "requant_ratio": 0.1, "downstream_changes_D": 0}


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


def test_interval_treats_float_noise_as_zero():
    r = interval(np.full(300, 1e-16), 0.95)
    assert r["n_nonzero"] == 0 and r["method"] == "bound"


def test_summarize2_reports_hamming_empty_and_sham_mismatch():
    out = _toy_out()
    out["base"][1]["solve_B1"] = 0  # p2: B1 != A
    for r in out["records"]:
        if r["puzzle_id"] == "p1" and r["level"] == 2:
            r["solve_B"] = 0  # p1: B != A at level 2 (every policy/dose/seed record)
    s = summarize2(out, n_boot=100)
    assert s["sham_mismatch"] == {"level1_B1": 1, "levels_B": {"2": 1, "11": 0}}
    cfg = s["configurations"][0]
    assert cfg["quantiles"]["hamming_CA_empty"] == pytest.approx([0] * 5)
    assert s["level1"]["frequency"]["quantiles"]["hamming_CA_empty"] == pytest.approx([0] * 5)


# --- frozen CAL code frequencies (v3.7 review CARBON-1) ---

import json  # noqa: E402

import torch  # noqa: E402

from ncm_sudoku.perturb import code_frequencies  # noqa: E402


def test_pilot_freqs_default_is_input():
    A = torch.tensor([[1, 2, 2, 3], [1, 2, 5, 5]])
    freqs, source = e2p2.pilot_freqs(A, (1, 3), None)
    assert source == "input" and set(freqs) == {1, 2}
    for lv, f in zip((1, 2), code_frequencies(A, (1, 3))):
        assert torch.equal(freqs[lv], f)


def test_pilot_freqs_frozen_overrides_and_validates():
    A = torch.zeros((2, 12), dtype=torch.long)
    levels = (1,) * 12
    frozen = {lv: np.eye(16)[lv % 16] for lv in range(1, 13)}
    freqs, source = e2p2.pilot_freqs(A, levels, frozen)
    assert source == "frozen"
    assert torch.equal(freqs[6], torch.tensor(np.eye(16)[6], dtype=torch.float32))
    assert freqs[6].dtype == torch.float32
    with pytest.raises(ValueError):
        e2p2.pilot_freqs(A, levels, {lv: v for lv, v in frozen.items() if lv != 11})
    with pytest.raises(ValueError):
        e2p2.pilot_freqs(A, levels, {**frozen, 2: np.full(16, 0.5)})  # does not sum to 1
    with pytest.raises(ValueError):
        e2p2.pilot_freqs(A, levels, {**frozen, 2: np.ones(15) / 15})  # wrong length


def test_load_frozen_freqs_toy(tmp_path):
    f = [0.0] * 16; f[3] = 0.25; f[7] = 0.75
    obj = {"levels": {str(lv): {"counts": [0] * 3 + [1] + [0] * 3 + [3] + [0] * 8, "frequencies": f}
                      for lv in range(1, 13)}}
    path = tmp_path / "cal_freqs.json"
    path.write_text(json.dumps(obj), encoding="utf-8")
    out = e2p2.load_frozen_freqs(path)
    assert set(out) == set(range(1, 13))
    assert out[11].dtype == np.float32 and out[11][7] == np.float32(0.75) and out[11].shape == (16,)
    obj["levels"]["2"]["frequencies"] = [1 / 16] * 16  # inconsistent with counts
    path.write_text(json.dumps(obj), encoding="utf-8")
    with pytest.raises(ValueError):
        e2p2.load_frozen_freqs(path)


@needs_model
@pytest.mark.slow
def test_run_pilot2_frozen_freqs_drive_draws(model, released, monkeypatch):
    monkeypatch.setattr(e2p2, "LEVELS_P2", (11,))
    monkeypatch.setattr(e2p2, "SEEDS_P2", (0,))
    drawn = []
    real = e2p2.perturb_level

    def spy(level_codes, dose, policy, freqs, gen):
        new, eligible = real(level_codes, dose, policy, freqs, gen)
        if policy == "frequency":
            drawn.append((level_codes.clone(), new.clone(), eligible.clone()))
        return new, eligible
    monkeypatch.setattr(e2p2, "perturb_level", spy)
    puzzles, sols = released
    v = 13
    frozen = {lv: np.eye(16, dtype=np.float32)[v] for lv in range(1, 13)}
    out = e2p2.run_pilot2(model, puzzles[:2], sols[:2], ["r0", "r1"], chunk=2, frozen_freqs=frozen)
    assert out["freq_source"] == "frozen" and out["freqs_level1"] == np.eye(16)[v].tolist()
    assert drawn
    for orig, new, eligible in drawn:
        changed = new != orig
        assert (new[changed] == v).all()
        assert (~eligible | changed.any(dim=1)).all()
    for r in out["level1"]:
        assert r["w_frequency"] == (1.0 if r["value"] == v else 0.0)
    drawn.clear()
    default = e2p2.run_pilot2(model, puzzles[:2], sols[:2], ["r0", "r1"], chunk=2)
    assert default["freq_source"] == "input"
    A = e2p2.clean_codes(model, puzzles[:2], chunk=2)
    assert default["freqs_level1"] == code_frequencies(A, model.levels)[0].tolist()
