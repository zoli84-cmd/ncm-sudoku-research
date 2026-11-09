import math

import numpy as np
import pytest

from ncm_sudoku.gate import (
    BENCHMARK_PCT,
    CI_LEVEL,
    GATE_N,
    INITIAL_SINGLES_MAX,
    MARGIN_PP,
    STUCK_SHARE_MAX_PP,
    TVD_MAX,
    depth_profile,
    model_free_gate,
    model_gate,
    wilson_interval,
)
from ncm_sudoku.grid import grid_from_string
from sudoku_cases import P

INKALA = grid_from_string(
    "800000000003600000070090200050007000000045700000100030001000068008500010090000400"
)


def test_constants_match_decisions():
    assert (TVD_MAX, STUCK_SHARE_MAX_PP, INITIAL_SINGLES_MAX) == (0.05, 5.0, 1.0)
    assert (BENCHMARK_PCT, MARGIN_PP, CI_LEVEL, GATE_N) == (86.3, 5.0, 0.90, 1000)


def test_depth_profile_categories():
    prof = depth_profile([P, INKALA])
    dist = prof["cell_depth_dist"]
    assert set(dist) == {"1", "2", "3", ">=4", "stuck"}
    assert sum(dist.values()) == pytest.approx(1.0)
    assert prof["stuck_puzzle_share"] == 0.5
    assert prof["mean_initial_singles"] > 0


def test_model_free_gate():
    prof = depth_profile([P, INKALA])
    assert model_free_gate(prof, prof)["passed"]
    shifted = {**prof, "cell_depth_dist": dict(prof["cell_depth_dist"])}
    shifted["cell_depth_dist"]["stuck"] += 0.12
    shifted["cell_depth_dist"]["1"] -= 0.12
    r = model_free_gate(shifted, prof)
    assert r["tvd"] == pytest.approx(0.12) and not r["passed"]


def test_wilson_interval():
    lo, hi = wilson_interval(50, 100, 0.90)
    assert lo == pytest.approx(0.4188, abs=1e-3) and hi == pytest.approx(0.5812, abs=1e-3)


def _solves(k, n=1000):
    return np.array([True] * k + [False] * (n - k))


def test_model_gate_outcomes():
    assert model_gate(_solves(863))["outcome"] == "equivalent"
    assert model_gate(_solves(780))["outcome"] == "not_equivalent"  # CI about (-10.5, -6.2) pp
    # smallest k whose interval crosses the lower margin (inconclusive)
    lower = (BENCHMARK_PCT - MARGIN_PP) / 100
    k = next(k for k in range(700, 900) if wilson_interval(k, 1000, CI_LEVEL)[1] > lower)
    r = model_gate(_solves(k))
    assert r["outcome"] == "inconclusive"
    assert r["ci_pp"][0] < -MARGIN_PP < r["ci_pp"][1]
    assert r["diff_pp"] == pytest.approx(100 * k / 1000 - BENCHMARK_PCT)
    assert not math.isnan(r["fresh_pct"])
