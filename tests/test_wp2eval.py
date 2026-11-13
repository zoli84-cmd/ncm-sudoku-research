from pathlib import Path

import numpy as np
import pytest

import ncm_sudoku.e2
import ncm_sudoku.e2p2 as e2p2
from ncm_sudoku import power, wp2eval
from ncm_sudoku.e2p2 import cp_upper
from test_e2p2 import _toy_out

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- constants

def test_constants():
    assert wp2eval.N_BOOT == 10000 and wp2eval.BOOT_SEED == 0
    assert wp2eval.H1_MARGIN == 0.01 and wp2eval.THETA2P_MARGIN == 0.03 and wp2eval.THETA_T_MARGIN == 0.01
    assert wp2eval.ALPHA_FAMILY == 0.05 / 3
    assert wp2eval.AUC_RANGES == {"6-11": (3.291773618630916e-05, 7.930234551597304e-05), "2-11": None}
    assert wp2eval.EQUIV_TOLERANCE == 0.0116
    assert wp2eval.EQUIV_READING == "descriptive (no pre-specified criterion)"
    assert wp2eval.NONZERO_EPS == 1e-12


# ---------------------------------------------------------------- tost

def test_tost_matches_power_h1_rule():
    rng = np.random.default_rng(1)
    for _ in range(10):
        a = rng.normal(rng.uniform(-0.012, 0.012), 0.004, 600)
        assert wp2eval.tost(a, 0.01, 0.05 / 3, n_boot=2000)["equivalent"] == power._h1_tost_ok(a, 2000, 0.01)


def test_tost_matches_power_h1_rule_on_bound_path():
    rng = np.random.default_rng(2)
    for k in (3, 10, 19):
        a = np.zeros(600)
        a[rng.choice(600, k, replace=False)] = rng.choice([-1.0, 1.0], k)
        t = wp2eval.tost(a, 0.01, 0.05 / 3, n_boot=500)
        assert t["method"] == "bound" and t["equivalent"] == power._h1_tost_ok(a, 500, 0.01)


def test_tost_matches_power_equivalence_ok():
    rng = np.random.default_rng(3)
    for k in (5, 15, 25, 60, 120):  # pilot-like zero-heavy samples, both interval paths
        a = np.zeros(600)
        a[rng.choice(600, k, replace=False)] = rng.choice([-1.0, -1 / 3, 1 / 3, 1.0], k)
        assert wp2eval.tost(a, 0.03, 0.05, n_boot=1000)["equivalent"] == power.equivalence_ok(a, 1000)


def test_tost_bound_path():
    v = np.r_[np.full(5, 0.5), np.zeros(595)]
    t = wp2eval.tost(v, 0.03, 0.05)
    assert t["method"] == "bound" and t["ci"][1] == pytest.approx(cp_upper(5, 600, 0.95))
    assert t["level"] == pytest.approx(0.90) and t["n"] == 600 and t["n_nonzero"] == 5
    assert t["estimate"] == pytest.approx(2.5 / 600)


def test_tost_bootstrap_path_uses_two_sided_level(monkeypatch):
    calls = []
    real = e2p2.interval

    def spy(v, level, *a, **k):
        calls.append((level, k.get("seed", a[1] if len(a) > 1 else None)))
        return real(v, level, *a, **k)

    monkeypatch.setattr(e2p2, "interval", spy)
    v = np.random.default_rng(0).normal(0.001, 0.002, 300)
    t = wp2eval.tost(v, 0.01, 0.05 / 3, n_boot=200)
    assert t["method"] == "bootstrap" and calls == [(1 - 2 * (0.05 / 3), 0)]
    assert t["equivalent"] == (-0.01 < t["ci"][0] and t["ci"][1] < 0.01)


def test_tost_is_strict():
    v = np.full(600, 0.0)  # bound path: ci = +-q, strictly inside only if q < margin
    t = wp2eval.tost(v, cp_upper(0, 600, 0.95), 0.05)
    assert t["ci"][1] == cp_upper(0, 600, 0.95) and t["equivalent"] is False


def test_tost_drops_nan_and_empty_is_not_equivalent(monkeypatch):
    t = wp2eval.tost({"a": float("nan"), "b": 0.0, "c": 0.001}, 0.03, 0.05)
    assert t["n"] == 2 and t["n_dropped_nan"] == 1
    monkeypatch.setattr(e2p2, "interval", lambda *a, **k: pytest.fail("interval called"))
    t = wp2eval.tost(np.full(600, np.nan), 0.01, 0.05)
    assert t["n"] == 0 and t["equivalent"] is False and t["ci"] is None and t["method"] is None
    assert t["n_dropped_nan"] == 600


# ---------------------------------------------------------------- contrast

def test_contrast_matches_summarize2_family():
    ref = e2p2.summarize2(_toy_out(), n_boot=200)["contrasts"]
    for c in ("theta2", "theta_comp"):
        got = wp2eval.contrast(e2p2.puzzle_values(_toy_out(), c, "frequency"), primary=True, n_boot=200)
        assert got["family"] == ref[c]["frequency"]["family"]
        assert {k: v for k, v in got["ci95"].items() if k != "level"} == ref[c]["frequency"]["ci95"]
        assert got["ci95"]["level"] == 0.95 and got["estimate"] == ref[c]["frequency"]["estimate"]


def test_contrast_secondary_has_no_family():
    c = wp2eval.contrast({"a": 0.1, "b": 0.2}, primary=False, n_boot=100)
    assert c["family"] is None and c["ci95"]["level"] == 0.95


def test_contrast_drops_nan_and_counts():
    c = wp2eval.contrast({"a": 0.1, "b": float("nan"), "c": 0.0}, primary=True)
    assert c["n"] == 2 and c["n_dropped_nan"] == 1
    assert c["estimate"] == pytest.approx(0.05) and c["family"]["level"] == e2p2.FAMILY_LEVEL


def test_contrast_discordance_ignores_float_noise():
    c = wp2eval.contrast({"a": 1e-16, "b": -1e-16, "c": 0.5}, primary=False)
    assert c["discordance"] == {"positive": 1, "negative": 0} and c["n_nonzero"] == 1


def test_contrast_uses_boot_seed(monkeypatch):
    seen = []
    monkeypatch.setattr(e2p2, "interval", lambda v, level, n_boot=0, seed=None, **k: seen.append(
        (level, n_boot, seed)) or {"method": "bound", "estimate": 0.0, "ci": (-1.0, 1.0), "n": len(v),
                                   "n_nonzero": 0})
    wp2eval.contrast({"a": 0.0}, primary=True, n_boot=123)
    assert seen == [(0.95, 123, 0), (e2p2.FAMILY_LEVEL, 123, 0)]


# ---------------------------------------------------------------- paired_diff, h1_block

def test_paired_diff():
    assert wp2eval.paired_diff([0.3, 0.2], [0.1, 0.25], ["x", "y"]) == pytest.approx({"x": 0.2, "y": -0.05})
    with pytest.raises(ValueError):
        wp2eval.paired_diff([0.3], [0.1, 0.2], ["x", "y"])


def test_h1_block():
    rng = np.random.default_rng(0)
    gen = rng.uniform(0.1, 0.2, 200)
    perm = gen + rng.normal(0.003, 0.002, 200)
    ids = [f"p{i}" for i in range(200)]
    b = wp2eval.h1_block(list(perm), list(gen), ids, perm_seeds=[list(perm), list(perm + 0.001)],
                         gen_seeds=[list(gen), list(gen)], n_boot=300)
    c = wp2eval.contrast(wp2eval.paired_diff(list(perm), list(gen), ids), primary=True, n_boot=300)
    for k in c:
        assert b[k] == c[k]
    t = wp2eval.tost(wp2eval.paired_diff(list(perm), list(gen), ids), 0.01, 0.05 / 3, n_boot=300)
    assert b["tost"] == t
    assert b["relative_improvement"] == pytest.approx(np.mean(perm - gen) / np.mean(perm))
    assert b["per_seed"] == pytest.approx([np.mean(perm - gen), np.mean(perm - gen) + 0.001])
    assert wp2eval.h1_block(list(perm), list(gen), ids, n_boot=100)["per_seed"] is None


# ---------------------------------------------------------------- e2_descriptive

def test_e2_descriptive_tables_equal_summarize2_and_call_no_statistics(monkeypatch):
    out = _toy_out()
    out["code_mismatch"] = {"level1_B1": 0, "levels_B": {"2": 0, "6": 0, "11": 0}, "level1_noop_D": 0}
    ref = e2p2.summarize2(out, n_boot=200)  # computed first, with the real functions
    for name in ("interval", "auc_pair", "summarize2"):
        monkeypatch.setattr(e2p2, name, lambda *a, _n=name, **k: pytest.fail(f"{_n} called"))
    monkeypatch.setattr(ncm_sudoku.e2, "cluster_bootstrap", lambda *a, **k: pytest.fail("cluster_bootstrap called"))
    monkeypatch.setattr(wp2eval, "tost", lambda *a, **k: pytest.fail("tost called"))
    d = wp2eval.e2_descriptive(out)
    assert d["configurations"] == ref["configurations"] and d["level1"] == ref["level1"]
    assert d["sham_mismatch"] == ref["sham_mismatch"] and "downstream_changes_D" in d
    assert d["level1_noop_mismatch"] is None and d["code_mismatch"] == out["code_mismatch"]
    dc = d["downstream_changes_D"]
    assert [(r["level"], r["policy"], r["dose"]) for r in dc["configurations"]] == \
        [(r["level"], r["policy"], r["dose"]) for r in ref["configurations"]]
    assert dc["configurations"][0]["quantiles"] == [0.0] * 5 and set(dc["level1"]) == {"frequency", "uniform"}


def test_e2_descriptive_downstream_quantiles():
    out = _toy_out()
    for i, r in enumerate(out["records"]):
        r["downstream_changes_D"] = i
    out["level1"][0]["downstream_changes_D"] = 4  # p1: weights 0.75 / 0.25 -> 3 + 0.25 * 0 = 3
    d = wp2eval.e2_descriptive(out)["downstream_changes_D"]
    l11 = [r["downstream_changes_D"] for r in out["records"] if r["level"] == 11]
    assert d["configurations"][-1]["level"] == 11
    assert d["configurations"][-1]["quantiles"] == pytest.approx(np.quantile(l11, e2p2.QUANTILES).tolist())
    assert d["level1"]["frequency"] == pytest.approx(np.quantile([3.0, 0.0], e2p2.QUANTILES).tolist())


# ---------------------------------------------------------------- auc_frozen

NODES_A = [(0.0, 0.0), (1.0, -0.2), (1.0, -0.4)]  # merged: (0, 0), (1, -0.3)
NODES_B = [(0.0, 0.1), (2.0, 0.1)]
NARROW_A = [(0.2, 0.0), (0.4, -0.1)]


def test_auc_frozen_cases():
    r = wp2eval.auc_frozen(NODES_A, NODES_B, None)
    assert r["auc_a"] is None and r["auc_b"] is None and r["range"] is None
    assert r["reason"] == "no frozen range (§12.2)" and r["covered"] is False
    assert r["coverage"] == {"a": [0.0, 1.0], "b": [0.0, 2.0]}
    assert r["nodes"]["a"] == [[0.0, 0.0], [1.0, pytest.approx(-0.3)]]
    n = wp2eval.auc_frozen(NARROW_A, NODES_B, (0.1, 0.5))
    assert n["covered"] is False and n["auc_a"] is None and n["auc_b"] is None
    assert n["reason"] == "TEST nodes do not cover the frozen range" and n["range"] == (0.1, 0.5)
    c = wp2eval.auc_frozen(NODES_A, NODES_B, (0.1, 0.5))
    assert c["covered"] is True and c["reason"] is None
    assert c["auc_a"] == pytest.approx(-0.3 * 0.3) and c["auc_b"] == pytest.approx(0.1)  # mean height on [0.1, 0.5]


def test_auc_frozen_needs_two_distinct_damage_values():
    r = wp2eval.auc_frozen([(0.3, 0.0), (0.3, 1.0)], NODES_B, (0.1, 0.5))
    assert r["coverage"]["a"] is None and r["covered"] is False and r["auc_a"] is None
    r = wp2eval.auc_frozen([(0.0, 0.0), (0.3, 0.0)], NODES_B, (0.3, 0.3 + 1e-9))  # boundary: max < hi
    assert r["covered"] is False


def test_auc_frozen_never_calls_auc_pair(monkeypatch):
    monkeypatch.setattr(e2p2, "auc_pair", lambda *a: pytest.fail("no TEST-derived range"))
    wp2eval.auc_frozen(NODES_A, NODES_B, None)
    wp2eval.auc_frozen(NODES_A, NODES_B, (0.1, 0.5))


# ---------------------------------------------------------------- S13 and readings

S13_IDS = {"early_sensitivity", "d_better_than_c", "positive_compensation", "probe_beats_null", "raw_ceiling",
           "levels_2_11_equiv", "h1_small_positive", "h1_no_practical", "h1_negative", "h1_readable_not_equiv",
           "l12_solution_content", "equiv_accurate_not_equivariant", "equivariance_succeeds", "non_significant"}


def test_s13_rows_are_verbatim_from_the_plan():
    text = (ROOT / "research_plan_v3.7.md").read_text(encoding="utf-8")
    assert set(wp2eval.S13) == S13_IDS
    for row in wp2eval.S13.values():
        assert f"| {row['result']} | {row['claim']} | {row['does_not_follow']} |" in text


def _block(fam=(-0.01, 0.01), ci95=(-0.01, 0.01), eq=None):
    src = fam if fam is not None else ci95
    b = {"estimate": (src[0] + src[1]) / 2, "family": {"ci": fam}, "ci95": {"ci": ci95}}
    if eq is not None:
        b["tost"] = {"equivalent": eq}
    return b


R = {"H1": _block((0.002, 0.006), (0.0025, 0.0055), True), "H2": _block((-0.12, -0.05)),
     "H3": _block((-0.01, 0.02)), "theta2_prime": _block(None, (-0.01, 0.01), True),
     "theta_T": _block(None, (-0.004, 0.004), True), "theta1_L12_wl": _block(None, (0.04, 0.06)),
     "equivariance": {"mean_deviation": 0.08, "share_within": 0.0}}


def _rows(readings, hyp):
    return {x["row"] for x in readings if x["hypothesis"] == hyp}


def _one(readings, hyp):
    (x,) = [x for x in readings if x["hypothesis"] == hyp]
    return x


@pytest.mark.parametrize("fam,tost_eq,rows", [
    ((0.002, 0.006), True, {"h1_small_positive", "probe_beats_null"}),
    ((-0.002, 0.004), True, {"h1_no_practical"}),
    ((-0.02, -0.005), False, {"h1_negative"}),
    ((-0.008, -0.002), True, {"h1_negative"}),
    ((0.004, 0.015), False, {"h1_readable_not_equiv", "probe_beats_null"}),
    ((-0.004, 0.012), False, {"non_significant"}),
    ((0.0, 0.006), True, {"h1_no_practical"}),  # boundaries: fl == 0 contains 0
    ((1e-12, 0.006), True, {"h1_small_positive", "probe_beats_null"}),
    ((0.0, 0.015), False, {"non_significant"}),
    ((-0.004, 0.0), False, {"non_significant"}),  # fh == 0 is not < 0
    ((-0.004, 0.0), True, {"h1_no_practical"})])
def test_select_readings_h1(fam, tost_eq, rows):
    readings = wp2eval.select_readings({**R, "H1": _block(fam, fam, tost_eq)})
    assert _rows(readings, "H1") == rows


def test_reading_shape_copies_s13_row():
    readings = wp2eval.select_readings(R)
    for x in readings:
        assert set(x) == {"hypothesis", "row", "result", "claim", "does_not_follow", "note", "inputs"}
        if x["row"] is not None:
            s = wp2eval.S13[x["row"]]
            assert (x["result"], x["claim"], x["does_not_follow"]) == (s["result"], s["claim"], s["does_not_follow"])
        else:
            assert x["claim"] is None and x["does_not_follow"] is None
    h1 = [x for x in readings if x["hypothesis"] == "H1"][0]
    assert h1["inputs"]["family_ci"] == (0.002, 0.006) and h1["inputs"]["tost_equivalent"] is True


def test_select_readings_h2_h3_and_unlisted_directions():
    r = wp2eval.select_readings({**R, "H2": _block((-0.12, -0.05)), "H3": _block((0.01, 0.03))})
    assert _rows(r, "H2") == {"early_sensitivity"}
    assert _rows(r, "H3") == {"d_better_than_c", "positive_compensation"}
    r = wp2eval.select_readings({**R, "H2": _block((-0.02, 0.01)), "H3": _block((-0.02, 0.0))})
    assert _rows(r, "H2") == {"non_significant"} and _rows(r, "H3") == {"non_significant"}
    r = wp2eval.select_readings({**R, "H2": _block((0.01, 0.05)), "H3": _block((-0.05, -0.01))})
    h2, h3 = _one(r, "H2"), _one(r, "H3")
    assert h2["row"] is None and h2["note"] == f"{wp2eval.NO_ROW} (late level more sensitive)"
    assert h3["row"] is None and h3["note"] == f"{wp2eval.NO_ROW} (negative compensation)"
    assert h2["inputs"]["family_ci"] == (0.01, 0.05) and h2["inputs"]["estimate"] == pytest.approx(0.03)


def test_raw_ceiling_is_never_selected():
    for fam in ((0.002, 0.006), (-0.02, -0.005), (0.004, 0.015)):
        r = wp2eval.select_readings({**R, "H1": _block(fam, fam, False), "H3": _block(fam)})
        assert all(x["row"] != "raw_ceiling" for x in r)


def test_select_readings_theta2_prime_and_level12_fallbacks():
    r = wp2eval.select_readings(R)
    assert _rows(r, "theta2_prime") == {"levels_2_11_equiv"} and _rows(r, "level12") == {"l12_solution_content"}
    r = wp2eval.select_readings({**R, "theta2_prime": _block(None, (-0.02, 0.05), False)})
    assert _rows(r, "theta2_prime") == {"non_significant"}
    r = wp2eval.select_readings({**R, "theta2_prime": _block(None, (0.01, 0.05), False)})
    x = _one(r, "theta2_prime")
    assert x["row"] is None and x["note"].startswith(wp2eval.NO_ROW)
    assert "θ₂′ not equivalent; 95% interval excludes 0" in x["note"]
    r = wp2eval.select_readings({**R, "theta_T": _block(None, (-0.02, 0.0), False)})
    x = _one(r, "level12")
    assert x["row"] is None and x["note"].startswith(wp2eval.NO_ROW) and "level-12 criterion not met" in x["note"]
    assert "theta_T" in x["note"] and "theta1_L12_wl" not in x["note"]
    r = wp2eval.select_readings({**R, "theta1_L12_wl": _block(None, (0.0, 0.02))})
    x = _one(r, "level12")
    assert x["row"] is None and "theta1_L12_wl" in x["note"] and "theta_T" not in x["note"]


def test_select_readings_e2_identity_failure():
    fail = {"status": "identity-failure"}
    rows = wp2eval.select_readings({**R, "H2": fail, "H3": fail, "theta2_prime": fail})
    assert not any(x["hypothesis"] in ("H2", "H3", "theta2_prime") for x in rows)
    (e2,) = [x for x in rows if x["hypothesis"] == "E2"]
    assert e2["row"] is None and "deviation" in e2["note"] and e2["claim"] is None
    assert _rows(rows, "H1") == {"h1_small_positive", "probe_beats_null"}


def test_equivariance_reading_constant():
    eq = [x for x in wp2eval.select_readings(R) if x["hypothesis"] == "equivariance"][0]
    assert eq["row"] is None and eq["note"] == wp2eval.EQUIV_READING
    assert eq["inputs"] == R["equivariance"]


@pytest.mark.parametrize("fam,row", [((-0.05, 0.0), "non_significant"), ((0.0, 0.05), "non_significant"),
                                     ((-0.05, -1e-12), "early_sensitivity"), ((1e-12, 0.05), None)])
def test_select_readings_h2_boundaries(fam, row):
    assert _rows(wp2eval.select_readings({**R, "H2": _block(fam)}), "H2") == {row}


@pytest.mark.parametrize("fam,rows", [((0.0, 0.05), {"non_significant"}), ((-0.05, 0.0), {"non_significant"}),
                                      ((1e-12, 0.05), {"d_better_than_c", "positive_compensation"}),
                                      ((-0.05, -1e-12), {None})])
def test_select_readings_h3_boundaries(fam, rows):
    assert _rows(wp2eval.select_readings({**R, "H3": _block(fam)}), "H3") == rows


def test_tost_at_exact_margin_is_not_equivalent(monkeypatch):
    for ci in ((-0.01, 0.005), (-0.005, 0.01), (-0.01, 0.01)):
        monkeypatch.setattr(e2p2, "interval", lambda v, level, _ci=ci, **k: {
            "method": "bootstrap", "estimate": 0.0, "ci": _ci, "n": len(v), "n_nonzero": len(v)})
        assert wp2eval.tost(np.ones(50), 0.01, 0.05)["equivalent"] is False
    monkeypatch.setattr(e2p2, "interval", lambda v, level, **k: {
        "method": "bootstrap", "estimate": 0.0, "ci": (-0.0099, 0.0099), "n": len(v), "n_nonzero": len(v)})
    assert wp2eval.tost(np.ones(50), 0.01, 0.05)["equivalent"] is True


def test_select_readings_single_e2_failure_with_none_block():
    fail = {"status": "identity-failure"}
    rows = wp2eval.select_readings({**R, "H2": None, "H3": fail, "theta2_prime": None})
    assert not any(x["hypothesis"] in ("H2", "H3", "theta2_prime") for x in rows)
    (e2,) = [x for x in rows if x["hypothesis"] == "E2"]
    assert e2["row"] is None and e2["note"] == wp2eval.E2_IDENTITY_NOTE
    assert e2["inputs"] == {"H2": None, "H3": "identity-failure", "theta2_prime": None}
