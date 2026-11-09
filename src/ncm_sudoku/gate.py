"""Terminal distribution gate (plan §4.1; D27, D34, D35). Constants are fixed before the run."""

from statistics import NormalDist

import numpy as np

from ncm_sudoku.labels import STUCK, hidden_singles, inference_waves, naked_singles

TVD_MAX = 0.05
STUCK_SHARE_MAX_PP = 5.0
INITIAL_SINGLES_MAX = 1.0
BENCHMARK_PCT = 86.3  # released hard benchmark, fixed (D31)
MARGIN_PP = 5.0
CI_LEVEL = 0.90  # TOST at alpha 0.05 per side
GATE_N = 1000
CATEGORIES = ("1", "2", "3", ">=4", "stuck")


def depth_profile(puzzles) -> dict:
    counts = dict.fromkeys(CATEGORIES, 0)
    stuck_puzzles, singles = 0, []
    for p in puzzles:
        depth = inference_waves(p).depth[np.asarray(p) == 0]
        for d in depth.tolist():
            counts["stuck" if d == STUCK else (">=4" if d >= 4 else str(d))] += 1
        stuck_puzzles += bool((depth == STUCK).any())
        singles.append(len(set(naked_singles(p)) | {c for _, _, c in hidden_singles(p)}))
    total = sum(counts.values())
    return {
        "n": len(puzzles),
        "cell_depth_dist": {k: v / total for k, v in counts.items()},
        "stuck_puzzle_share": stuck_puzzles / len(puzzles),
        "mean_initial_singles": float(np.mean(singles)),
    }


def model_free_gate(fresh: dict, released: dict) -> dict:
    tvd = 0.5 * sum(abs(fresh["cell_depth_dist"][k] - released["cell_depth_dist"][k]) for k in CATEGORIES)
    stuck_pp = 100 * (fresh["stuck_puzzle_share"] - released["stuck_puzzle_share"])
    singles = fresh["mean_initial_singles"] - released["mean_initial_singles"]
    checks = {
        "tvd_ok": tvd <= TVD_MAX,
        "stuck_share_ok": abs(stuck_pp) <= STUCK_SHARE_MAX_PP,
        "initial_singles_ok": abs(singles) <= INITIAL_SINGLES_MAX,
    }
    thresholds = {"tvd": TVD_MAX, "stuck_pp": STUCK_SHARE_MAX_PP, "initial_singles": INITIAL_SINGLES_MAX}
    return {"tvd": tvd, "stuck_share_diff_pp": stuck_pp, "initial_singles_diff": singles, **checks,
            "thresholds": thresholds, "passed": all(checks.values())}


def wilson_interval(k: int, n: int, level: float) -> tuple[float, float]:
    z = NormalDist().inv_cdf(0.5 + level / 2)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return float(centre - half), float(centre + half)


def model_gate(solves: np.ndarray) -> dict:
    solves = np.asarray(solves, dtype=bool)
    k, n = int(solves.sum()), len(solves)
    lo, hi = wilson_interval(k, n, CI_LEVEL)
    ci = (100 * lo - BENCHMARK_PCT, 100 * hi - BENCHMARK_PCT)
    if -MARGIN_PP < ci[0] and ci[1] < MARGIN_PP:
        outcome = "equivalent"
    elif ci[0] >= MARGIN_PP or ci[1] <= -MARGIN_PP:
        outcome = "not_equivalent"
    else:
        outcome = "inconclusive"
    return {"n": n, "solved": k, "fresh_pct": 100 * k / n, "benchmark_pct": BENCHMARK_PCT,
            "diff_pp": 100 * k / n - BENCHMARK_PCT, "ci_pp": ci, "ci_level": CI_LEVEL,
            "margin_pp": MARGIN_PP, "outcome": outcome}
