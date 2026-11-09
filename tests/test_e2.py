import pytest

import ncm_sudoku.e2 as e2
from conftest import needs_model
from ncm_sudoku.e2 import cluster_bootstrap, run_pilot, summarize, theta2, theta_comp


def _rec(pid, level, seed, A, B, C, D, eligible=True, policy="frequency", dose=1):
    return {"puzzle_id": pid, "level": level, "policy": policy, "dose": dose, "seed": seed,
            "eligible": eligible, "solve_A": A, "solve_B": B, "solve_C": C, "solve_D": D,
            "well_formed_C": True, "well_formed_D": True, "hamming_CA": 0.1, "downstream_changes_D": 3}


def _toy():
    r = []
    # puzzle p1: level 2 D fails in seeds 0,1; level 11 D never fails
    for s, d2 in enumerate([0, 0, 1]):
        r.append(_rec("p1", 2, s, A=1, B=1, C=0, D=d2))
        r.append(_rec("p1", 11, s, A=1, B=1, C=1, D=1))
    # puzzle p2: level 2 D fails in seed 0; level 11 D fails in seed 2
    for s, (d2, d11) in enumerate([(0, 1), (1, 1), (1, 0)]):
        r.append(_rec("p2", 2, s, A=1, B=1, C=1, D=d2))
        r.append(_rec("p2", 11, s, A=1, B=1, C=1, D=d11))
    # puzzle p3: ineligible at level 11 in one seed -> excluded from theta2
    for s in range(3):
        r.append(_rec("p3", 2, s, A=1, B=1, C=0, D=0))
        r.append(_rec("p3", 11, s, A=1, B=1, C=1, D=1, eligible=(s != 1)))
    return r


def test_theta_estimators_on_toy_records():
    recs = _toy()
    # theta2 per puzzle: mean_s(D2-A) - mean_s(D11-A)
    p1 = (-2 / 3) - 0.0
    p2 = (-1 / 3) - (-1 / 3)
    assert theta2(recs) == pytest.approx((p1 + p2) / 2)
    # theta_comp level 2 per puzzle: mean_s((D-C)-(B-A)); p3 eligible at level 2 in all seeds
    c1 = ((0 - 0) + (0 - 0) + (1 - 0)) / 3
    c2 = ((0 - 1) + (1 - 1) + (1 - 1)) / 3
    c3 = 0.0
    assert theta_comp(recs, level=2) == pytest.approx((c1 + c2 + c3) / 3)


def test_cluster_bootstrap_degenerate():
    recs = [_rec(f"p{i}", lv, s, 1, 1, 0, 0) for i in range(5) for lv in (2, 11) for s in range(3)]
    lo, hi = cluster_bootstrap(recs, theta2, n_boot=200, seed=0)
    assert lo == hi == pytest.approx(theta2(recs))


def test_summarize_keys():
    s = summarize(_toy())
    assert {"theta2", "theta_comp_level2", "by_config", "dose_overlap"} <= set(s)
    assert s["theta2"]["n_puzzles"] == 2


@needs_model
@pytest.mark.slow
def test_run_pilot_small(model, released, monkeypatch):
    monkeypatch.setattr(e2, "PILOT_LEVELS", (11,))
    monkeypatch.setattr(e2, "dose_grid", lambda n: [1])
    puzzles, sols = released
    recs = run_pilot(model, puzzles[:2], sols[:2], ["r0", "r1"], chunk=2)
    assert len(recs) == 2 * 1 * 3 * 2
    assert all(r["solve_B"] == r["solve_A"] for r in recs)
    assert {r["policy"] for r in recs} == {"frequency", "uniform"}
