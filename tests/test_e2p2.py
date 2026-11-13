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
    assert len(out["level1"]) == 2 * 16  # full ordered batch: every value on both rows
    assert sum(r["noop"] for r in out["level1"]) == 2 and out["level1_noop_mismatch"] == 0  # in-batch sham
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


# --- full-batch level-1 enumeration (v3.7 Final ASTRA-1) ---

from e2p2_fakes import N_TOY, TOY_LEVELS, install_fakes, toy_puzzles  # noqa: E402
from types import SimpleNamespace  # noqa: E402


def _toy_run(monkeypatch, **kw):
    calls = []
    install_fakes(monkeypatch, calls, **kw)
    pz = toy_puzzles()
    out = e2p2.run_pilot2(SimpleNamespace(levels=TOY_LEVELS), pz, pz.copy(), [f"p{i}" for i in range(N_TOY)], chunk=2)
    return out, calls


def test_level1_enumeration_runs_full_ordered_batch(monkeypatch):
    out, calls = _toy_run(monkeypatch)
    lvl1_d = [c for c in calls if c[0] == "D" and c[1] == 1]
    # B1 (codes = A's own level-1 code) plus one full-batch pass per value, each in chunks of 2
    assert len(lvl1_d) == 3 * (1 + 16)
    rows = [r for c in lvl1_d for r in c[2]]
    assert rows == list(range(1, N_TOY + 1)) * 17          # all rows, original order, every pass
    assert [len(c[2]) for c in lvl1_d[:3]] == [2, 2, 1]    # same chunking as A/B
    for v in range(16):  # pass v sets every row's level-1 code to v
        assert all(x == v for c in lvl1_d[3 * (v + 1): 3 * (v + 2)] for x in c[3])
    assert len(out["level1"]) == 16 * N_TOY
    assert [r["value"] for r in out["level1"]] == [v for v in range(16) for _ in range(N_TOY)]
    assert [r["puzzle_id"] for r in out["level1"][:N_TOY]] == [f"p{i}" for i in range(N_TOY)]


def test_level1_noop_rows_flagged_with_zero_weight(monkeypatch):
    out, _ = _toy_run(monkeypatch)
    a1 = dict(zip([f"p{i}" for i in range(N_TOY)], toy_puzzles()[:, 1].tolist()))
    for r in out["level1"]:
        assert r["noop"] == (a1[r["puzzle_id"]] == r["value"])
        if r["noop"]:
            assert r["w_frequency"] == 0.0 and r["w_uniform"] == 0.0 and r["tv"] == 0.0
    assert sum(r["noop"] for r in out["level1"]) == N_TOY
    assert out["level1_noop_mismatch"] == 0


def test_level1_noop_rows_do_not_change_estimates(monkeypatch):
    out, _ = _toy_run(monkeypatch)
    trimmed = {**out, "level1": [r for r in out["level1"] if not r["noop"]]}
    for c in ("theta2", "theta_comp", "theta2_prime"):
        for policy in ("frequency", "uniform"):
            assert puzzle_values(out, c, policy) == puzzle_values(trimmed, c, policy)
    full, cut = summarize2(out, n_boot=50), summarize2(trimmed, n_boot=50)
    assert full["level1"] == cut["level1"] and full["contrasts"] == cut["contrasts"]
    assert full["level1_noop_mismatch"] == 0


def test_level1_noop_filter_is_explicit():
    """No-op records are dropped even if a weight were nonzero (non-weight-based quantities too)."""
    out = {
        "base": [{"puzzle_id": "p", "solve_A": 1, "solve_B1": 1}],
        "level1": [
            {"puzzle_id": "p", "value": 1, "noop": False, "w_frequency": 1.0, "w_uniform": 1.0, "solve_C": 0,
             "solve_D": 0, "well_formed_C": True, "well_formed_D": True,
             **{k: 0.5 for k in e2p2.DAMAGE_KEYS}},
            {"puzzle_id": "p", "value": 2, "noop": True, "w_frequency": 5.0, "w_uniform": 5.0, "solve_C": 1,
             "solve_D": 1, "well_formed_C": False, "well_formed_D": False,
             **{k: 9.0 for k in e2p2.DAMAGE_KEYS}},
        ],
    }
    assert e2p2._level1_terms(out, "frequency") == {"p": (-1.0, 0.0)}
    assert e2p2._level1_weighted(out["level1"], "frequency", "tv", {"p"}) == [{"tv": 0.5}]


def test_level1_noop_mismatch_counts_forced_mismatch(monkeypatch):
    out, _ = _toy_run(monkeypatch, flip_noop_solve=True)  # p0 (a1 = 3): C solve flipped when v = 3
    assert out["level1_noop_mismatch"] == 1
    assert summarize2(out, n_boot=50)["level1_noop_mismatch"] == 1
    out, _ = _toy_run(monkeypatch, tv_value=0.25)        # every no-op row has TV != 0
    assert out["level1_noop_mismatch"] == N_TOY


def test_level1_noop_mismatch_function():
    base = [{"puzzle_id": "a", "solve_A": 1, "solve_B1": 0}, {"puzzle_id": "b", "solve_A": 0, "solve_B1": 0}]
    recs = [{"puzzle_id": "a", "noop": True, "solve_C": 1, "solve_D": 0, "tv": 0.0, "tv_empty": 0.0},
            {"puzzle_id": "b", "noop": True, "solve_C": 0, "solve_D": 1, "tv": 0.0, "tv_empty": 0.0},
            {"puzzle_id": "b", "noop": False, "solve_C": 1, "solve_D": 1, "tv": 0.3, "tv_empty": 0.3}]
    assert e2p2.level1_noop_mismatch(recs, base) == 1


def test_summarize2_without_noop_field_reports_none(monkeypatch):
    out, _ = _toy_run(monkeypatch)
    legacy = {k: v for k, v in out.items() if k != "level1_noop_mismatch"}
    legacy["level1"] = [{k: v for k, v in r.items() if k != "noop"} for r in out["level1"] if not r["noop"]]
    assert summarize2(legacy, n_boot=50)["level1_noop_mismatch"] is None


def test_level1_noop_mismatch_counts_tv_empty_and_reports_max_tv():
    base = [{"puzzle_id": "a", "solve_A": 1, "solve_B1": 0}]
    recs = [{"puzzle_id": "a", "noop": True, "solve_C": 1, "solve_D": 0, "tv": 0.0, "tv_empty": 1e-9},
            {"puzzle_id": "a", "noop": True, "solve_C": 1, "solve_D": 0, "tv": 0.0, "tv_empty": 0.0},
            {"puzzle_id": "a", "noop": False, "solve_C": 0, "solve_D": 1, "tv": 0.7, "tv_empty": 0.9}]
    assert e2p2.level1_noop_mismatch(recs, base) == 1  # exact: any nonzero tv_empty counts
    assert e2p2.level1_noop_max_tv(recs) == {"tv": 0.0, "tv_empty": 1e-9}  # no-op rows only
    assert e2p2.level1_noop_max_tv([r for r in recs if not r["noop"]]) == {"tv": None, "tv_empty": None}


def test_run_pilot2_and_summarize2_report_noop_max_tv(monkeypatch):
    out, _ = _toy_run(monkeypatch, tv_value=0.25)
    assert out["level1_noop_max_tv"] == {"tv": 0.25, "tv_empty": 0.25}
    s = summarize2(out, n_boot=50)
    assert s["level1_noop_mismatch"] == N_TOY and s["level1_noop_max_tv"] == {"tv": 0.25, "tv_empty": 0.25}
    legacy = {k: v for k, v in out.items() if k not in ("level1_noop_mismatch", "level1_noop_max_tv")}
    assert summarize2(legacy, n_boot=50)["level1_noop_max_tv"] is None


# --- WP2 Task 2: summary helpers, resumable stages, chunked decoding, diagnostics ---

from pathlib import Path  # noqa: E402

GOLDEN = Path(__file__).parent / "golden" / "summarize2_toy.json"


def test_summarize2_matches_golden():
    # tests/golden/summarize2_toy.json was written from the pre-WP2 summarize2 on _toy_out() (n_boot=200)
    got = json.loads(json.dumps(summarize2(_toy_out(), n_boot=200)))
    assert got == json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_summary_helpers_equal_summarize2_blocks():
    s = summarize2(_toy_out(), n_boot=200)
    assert e2p2.sham_mismatch_counts(_toy_out()) == s["sham_mismatch"]
    assert e2p2.configuration_table(_toy_out()) == s["configurations"]
    assert e2p2.level1_table(_toy_out()) == s["level1"]


from e2p2_fakes import toy_model  # noqa: E402

FULL_DESIGN = (1, 2, 4, 6, 9, 13, 18, 26, 37, 50, 67, 89)
BASIC_KEYS = {"changed_C", "changed_D", "later_changes_D", "positions", "orig", "new", "p_new", "p_orig",
              "freq_new", "replacement_norm"}
FULL_KEYS = {"state_dist_C", "state_dist_D", "level_changed_C", "level_changed_D"}


def _run(monkeypatch, calls=None, fakes=None, m=None, **kw):
    calls = [] if calls is None else calls
    install_fakes(monkeypatch, calls, **(fakes or {}))
    pz = toy_puzzles()
    m = toy_model() if m is None else m
    return e2p2.run_pilot2(m, pz, pz.copy(), [f"p{i}" for i in range(N_TOY)], chunk=2, **kw)


def _collect():
    """on_stage callback storing value, diag and technical per key."""
    slots = {"value": {}, "diag": {}, "tech": {}}

    def cb(k, v, d, t):
        slots["value"][k], slots["diag"][k], slots["tech"][k] = v, d, t
    return cb, slots


def test_stage_keys_cover_full_design():
    keys = e2p2.stage_keys(FULL_DESIGN)
    assert len(keys) == 1 + 16 + 3 + 78 and keys[0] == "base" and keys[1] == "level1/v00"
    assert keys[16] == "level1/v15" and keys[17] == "L02/B"
    assert "L11/frequency/d67/s2" in keys and keys.index("L02/B") < keys.index("L02/frequency/d01/s0")
    assert keys.index("L02/frequency/d02/s2") < keys.index("L02/uniform/d01/s0") < keys.index("L06/B")
    assert len(set(keys)) == len(keys)


def test_primary_stages():
    assert e2p2.PRIMARY_STAGES == tuple(f"level1/v{v:02d}" for v in range(16)) + tuple(
        f"L11/frequency/d01/s{s}" for s in range(3))
    assert set(e2p2.PRIMARY_STAGES) <= set(e2p2.stage_keys(FULL_DESIGN))


def test_run_pilot2_stage_keys_follow_stage_keys(monkeypatch):
    cb, slots = _collect()
    _run(monkeypatch, on_stage=cb)
    assert list(slots["value"]) == e2p2.stage_keys(TOY_LEVELS)


def test_run_pilot2_stages_resume_identical(monkeypatch):
    calls = []
    cb, slots = _collect()
    full = _run(monkeypatch, calls, on_stage=cb)
    stages = slots["value"]
    n_D_full = len([c for c in calls if c[0] == "D"])
    keys = list(stages)
    half = {k: stages[k] for k in keys[: len(keys) // 2]}
    seen = []
    calls.clear()
    again = _run(monkeypatch, calls, done=half, on_stage=lambda k, v, d, t: seen.append(k))
    assert again == full and seen == keys[len(keys) // 2:]
    assert len([c for c in calls if c[0] == "D"]) < n_D_full


def test_run_pilot2_stages_compose_output(monkeypatch):
    cb, slots = _collect()
    out = _run(monkeypatch, on_stage=cb)
    st = slots["value"]
    assert st["base"] == out["base"]
    assert [r for v in range(16) for r in st[f"level1/v{v:02d}"]] == out["level1"]
    assert st["L02/B"] == [r["solve_B"] for r in out["records"][:N_TOY]]
    cfg = [k for k in st if k.count("/") == 3]
    assert [r for k in cfg for r in st[k]] == out["records"]


def test_run_pilot2_given_A_skips_generation(monkeypatch):
    full = _run(monkeypatch)
    A_full = e2p2.clean_codes(None, toy_puzzles(), chunk=2)
    monkeypatch.setattr(e2p2, "generate_codes", lambda *a, **k: pytest.fail("A was given"))
    pz = toy_puzzles()
    again = e2p2.run_pilot2(toy_model(), pz, pz.copy(), [f"p{i}" for i in range(N_TOY)], chunk=2, A=A_full)
    assert again == full


def test_level1_enumeration_equals_concatenated_level1_value(monkeypatch):
    install_fakes(monkeypatch, [])
    pz, ids = toy_puzzles(), [f"p{i}" for i in range(N_TOY)]
    m = toy_model()
    A = e2p2.clean_codes(m, pz, chunk=2)
    freqs1 = e2p2.pilot_freqs(A, m.levels)[0][1]
    ctx = e2p2.branch_context(m, pz, pz.copy(), A, 2)
    a1 = A[:, 0]
    w = {p: e2p2.level1_weights(a1, freqs1, p) for p in e2p2.POLICIES}
    parts = [r for v in range(16) for r in e2p2.level1_value(ctx, a1, w, ids, v)]
    assert e2p2.level1_enumeration(m, pz, pz.copy(), ids, A, freqs1, 2, ctx) == parts


def test_decode_chunk_reaches_every_eval(monkeypatch):
    calls = []
    _run(monkeypatch, calls, decode_chunk=50)
    chunks = [c[2] for c in calls if c[0] == "eval"]
    assert chunks and set(chunks) == {50}
    calls.clear()
    _run(monkeypatch, calls)
    assert set(c[2] for c in calls if c[0] == "eval") == {None}


def test_decode_chunk_does_not_change_output(monkeypatch):
    assert _run(monkeypatch, decode_chunk=2) == _run(monkeypatch)


def test_diagnostics_do_not_change_records(monkeypatch):
    plain = _run(monkeypatch)
    cb, slots = _collect()
    with_diag = _run(monkeypatch, diagnostics=True, decode_chunk=2, on_stage=cb)
    diags = slots["diag"]
    assert with_diag == plain and diags["base"] is None and diags["L02/B"] is None
    assert set(diags["L02/frequency/d01/s0"]) == BASIC_KEYS
    assert set(diags["level1/v03"]) == BASIC_KEYS | FULL_KEYS
    plain_cb, plain_slots = _collect()
    _run(monkeypatch, on_stage=plain_cb)
    assert all(d is None for d in plain_slots["diag"].values())
    assert all(t["code_mismatch"] is None and t["diag_seconds"] == 0.0 for t in plain_slots["tech"].values())


def test_output_dict_unchanged_by_diagnostics(monkeypatch):
    assert set(_run(monkeypatch, diagnostics=True)) == set(_run(monkeypatch))


def test_diagnostic_arrays_consistent_with_records(monkeypatch):
    cb, slots = _collect()
    out = _run(monkeypatch, diagnostics=True, on_stage=cb)
    diags, st = slots["diag"], slots["value"]
    A = torch.as_tensor(toy_puzzles()[:, 1:4].astype(np.int64))
    L = len(TOY_LEVELS)
    for key, d in diags.items():
        if d is None:
            continue
        recs = st[key]
        n = len(recs)
        assert d["changed_C"].shape == (n, 81) and d["changed_C"].dtype == np.bool_
        assert d["changed_D"].shape == (n, 81) and d["changed_D"].dtype == np.bool_
        assert d["later_changes_D"].shape == (n, L) and d["later_changes_D"].dtype == np.int16
        assert d["later_changes_D"].sum(axis=1).tolist() == [r["downstream_changes_D"] for r in recs]
        for k in ("positions", "orig", "new"):
            assert d[k].dtype == np.int16 and d[k].shape[0] == n
        for k in ("p_new", "p_orig", "freq_new", "replacement_norm"):
            assert d[k].dtype == np.float32
        if "state_dist_C" in d:
            assert d["state_dist_C"].shape == (n, L) and d["state_dist_D"].dtype == np.float32
            assert d["level_changed_D"].shape == (n, L, 81) and d["level_changed_C"].dtype == np.bool_
    freqs1 = np.asarray(out["freqs_level1"], dtype=np.float32)
    for v in range(16):
        d, recs = diags[f"level1/v{v:02d}"], st[f"level1/v{v:02d}"]
        noop = np.array([r["noop"] for r in recs])
        assert not d["changed_C"][noop].any()  # C equals A on no-op rows
        assert d["changed_C"][~noop].any(axis=1).all()  # the level-1 code is visible in the fake tokens
        assert (d["positions"] == 0).all() and (d["new"][:, 0] == v).all()
        assert d["orig"][:, 0].tolist() == A[:, 0].tolist()
        assert (d["replacement_norm"][noop] == 0).all() and (d["replacement_norm"][~noop] > 0).all()
        assert d["level_changed_C"][~noop, 0].any(axis=1).all() and (d["state_dist_C"][noop] == 0).all()
        assert np.array_equal(d["freq_new"][:, 0], np.full(len(recs), freqs1[v], dtype=np.float32))
    # level 2: positions/orig/new agree with A vs C; ineligible rows -1 and NaN
    for key in [k for k in diags if k.startswith("L02/") and k.count("/") == 3]:
        d, recs = diags[key], st[key]
        dose = int(key.split("/")[2][1:])
        assert d["positions"].shape == (N_TOY, dose)
        for i, r in enumerate(recs):
            if r["eligible"]:
                pos = d["positions"][i]
                assert (pos >= 0).all() and (d["orig"][i] == A[i, 1 + pos].numpy()).all()
                assert (d["new"][i] != d["orig"][i]).all() and d["changed_C"][i].any()
                assert np.isfinite(d["p_new"][i]).all() and np.isfinite(d["replacement_norm"][i])
            else:
                assert (d["positions"][i] == -1).all() and np.isnan(d["p_new"][i]).all()
                assert np.isnan(d["freq_new"][i]).all() and np.isnan(d["replacement_norm"][i])


def test_ineligible_rows_marked(monkeypatch):
    # frozen frequencies with all mass on code 2: rows whose replaced level-2 code is 2 are ineligible
    frozen = {lv: np.eye(16, dtype=np.float32)[2] for lv in (1, 2, 6, 11)}
    cb, slots = _collect()
    _run(monkeypatch, diagnostics=True, on_stage=cb, frozen_freqs=frozen)
    d, recs = slots["diag"]["L02/frequency/d02/s0"], slots["value"]["L02/frequency/d02/s0"]
    elig = np.array([r["eligible"] for r in recs])
    assert elig.any() and not elig.all()
    assert (d["positions"][~elig] == -1).all() and (d["orig"][~elig] == -1).all()
    assert np.isnan(d["p_orig"][~elig]).all() and np.isnan(d["replacement_norm"][~elig]).all()
    assert (d["new"][elig] == 2).all() and (d["freq_new"][elig] == 1.0).all()


def test_code_probs_are_softmax_of_level_logits(monkeypatch):
    cb, slots = _collect()
    _run(monkeypatch, diagnostics=True, on_stage=cb)
    d = slots["diag"]["level1/v05"]
    pz = toy_puzzles()
    logits = 0.1 * torch.arange(16.0) + 0.01 * torch.as_tensor(pz[:, 0], dtype=torch.float32)[:, None]
    p = torch.softmax(logits, dim=-1)
    assert np.allclose(d["p_new"][:, 0], p[:, 5].numpy())
    assert np.allclose(d["p_orig"][:, 0], p[torch.arange(N_TOY), torch.as_tensor(pz[:, 1].astype(np.int64))].numpy())


def test_replacement_norm_from_embeddings(monkeypatch):
    from ncm_sudoku import damage
    E1 = torch.zeros(16, 4)
    E2 = torch.zeros(16, 4)
    for v in range(16):
        E2[v] = torch.tensor([v, 2.0 * v, v * v / 10, 1.0])
    m = toy_model([E1, E2])
    cb, slots = _collect()
    _run(monkeypatch, m=m, diagnostics=True, on_stage=cb)
    d = slots["diag"]["L02/uniform/d02/s0"]
    A = torch.as_tensor(toy_puzzles()[:, 1:4].astype(np.int64))
    for i in range(N_TOY):
        old, new = A[i, 1:3], torch.as_tensor(d["new"][i].astype(np.int64))
        assert d["positions"][i].tolist() == [0, 1]
        assert torch.equal(old, torch.as_tensor(d["orig"][i].astype(np.int64)))
        d1, d2 = ((E2[new[j]] - E2[old[j]]).norm() for j in range(2))
        assert d["replacement_norm"][i] == pytest.approx(float(torch.sqrt(d1 ** 2 + d2 ** 2)), rel=1e-6)
        rms = damage.codebook_rms(m, 2, old[None], new[None])[0]
        assert d["replacement_norm"][i] == pytest.approx(float(rms) * math.sqrt(2), rel=1e-6)


def test_full_diagnostics_only_for_primary_stages(monkeypatch):
    cb, slots = _collect()
    _run(monkeypatch, diagnostics=True, on_stage=cb)
    diags = slots["diag"]
    assert {k for k, d in diags.items() if d and "state_dist_C" in d} == set(e2p2.PRIMARY_STAGES) & set(diags)
    monkeypatch.setattr(e2p2, "PRIMARY_STAGES", ("L02/frequency/d01/s0",))  # read at call time
    cb, slots = _collect()
    _run(monkeypatch, diagnostics=True, on_stage=cb)
    assert {k for k, d in slots["diag"].items() if d and "state_dist_C" in d} == {"L02/frequency/d01/s0"}


def test_full_diagnostics_state_distances(monkeypatch):
    cb, slots = _collect()
    _run(monkeypatch, diagnostics=True, on_stage=cb, fakes={"exact_restart": True})
    d = slots["diag"]["level1/v06"]
    A = torch.as_tensor(toy_puzzles()[:, 1:4].astype(np.int64)).float()
    for i in range(N_TOY):
        z1 = A[i].clone()
        z1[1:] = 0
        c1 = z1.clone()
        c1[0] = 6
        assert d["state_dist_C"][i, 0] == pytest.approx(float((c1 - z1).norm() / z1.norm()))
        assert d["state_dist_D"][i, 1] == d["state_dist_C"][i, 1]  # exact restart: D = C
        assert (d["level_changed_D"][i] == d["level_changed_C"][i]).all()


def test_code_mismatch_zero_for_exact_restart(monkeypatch):
    cb, slots = _collect()
    _run(monkeypatch, diagnostics=True, on_stage=cb, fakes={"exact_restart": True})
    tech = slots["tech"]
    keyed = [k for k in tech if k == "base" or k.endswith("/B") or k.startswith("level1/")]
    assert len(keyed) == 1 + 16 + 1
    assert all(tech[k]["code_mismatch"] == 0 for k in keyed)
    assert all(tech[k]["code_mismatch"] is None for k in tech if k not in keyed)


def test_code_mismatch_counts_changed_sham_suffix(monkeypatch):
    install_fakes(monkeypatch, [], exact_restart=True)
    inner = e2p2.continue_generation

    def cont(m, prefix, codes_prefix, level):
        out = inner(m, prefix, codes_prefix, level).clone()
        out[prefix[:, 1] == 1, -1] += 1  # row p0: the last code changes; the fake solve ignores it
        return out

    monkeypatch.setattr(e2p2, "continue_generation", cont)
    pz = toy_puzzles()
    cb, slots = _collect()
    out = e2p2.run_pilot2(toy_model(), pz, pz.copy(), [f"p{i}" for i in range(N_TOY)], chunk=2,
                          diagnostics=True, on_stage=cb)
    tech = slots["tech"]
    assert tech["L02/B"]["code_mismatch"] == 1 and tech["base"]["code_mismatch"] == 1
    assert all(r["solve_B"] == r["solve_A"] for r in out["records"] if r["level"] == 2)
    assert all(b["solve_B1"] == b["solve_A"] for b in out["base"]) and out["level1_noop_mismatch"] == 0
    # p0's own level-1 code is 3: only that value has p0 as a no-op row
    assert tech["level1/v03"]["code_mismatch"] == 1
    assert all(tech[f"level1/v{v:02d}"]["code_mismatch"] == 0 for v in range(16) if v != 3)


def test_stage_technical_has_timings(monkeypatch):
    for diagnostics in (False, True):
        cb, slots = _collect()
        _run(monkeypatch, diagnostics=diagnostics, on_stage=cb)
        tech = slots["tech"]
        assert all(t["seconds"] >= t["diag_seconds"] >= 0.0 for t in tech.values())
        assert all(set(t) == {"seconds", "diag_seconds", "code_mismatch"} for t in tech.values())
        assert any(t["diag_seconds"] > 0.0 for t in tech.values()) == diagnostics
