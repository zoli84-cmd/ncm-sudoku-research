"""WP2 decision statistics and the mechanical §13 readings (plan v3.7 §7.3, §8.3, §11, §12.2, §13).

Confirmatory intervals follow §11: percentile cluster bootstrap over puzzles (10,000 resamples,
seed 0) or the §11.2 rare-event bound, both from `e2p2.interval`. Every statistic is called through
the `e2p2` module so that monkeypatched tests see each call. No AUC is computed over a TEST-derived
range (`auc_frozen`); `e2_descriptive` computes no statistic at all.
"""

import math

import numpy as np

import ncm_sudoku.e2p2 as e2p2
from ncm_sudoku.e2 import POLICIES

N_BOOT = 10000
BOOT_SEED = 0
H1_MARGIN = 0.01  # §8.3, D60
THETA2P_MARGIN = 0.03  # §11.4
THETA_T_MARGIN = 0.01  # §8.3
ALPHA_FAMILY = 0.05 / 3  # Bonferroni per side over the primary family (§11.1)
# §12.2 frozen common damage ranges (mean TV); 2 vs. 11 has no positive-width range (D53)
AUC_RANGES = {"6-11": (3.291773618630916e-05, 7.930234551597304e-05), "2-11": None}
EQUIV_TOLERANCE = 0.0116  # §8.4, D71
EQUIV_READING = "descriptive (no pre-specified criterion)"  # spec ambiguity 7
NONZERO_EPS = 1e-12  # as e2p2.interval's nonzero count
NO_ROW = "no pre-specified §13 reading"
E2_IDENTITY_NOTE = "E2 identity failure: a logged deviation is required before any E2 inference"


# ---------------------------------------------------------------- statistics

def _clean(values) -> tuple[np.ndarray, int]:
    """Values in input order (dict values or array) without NaNs, and the number of NaNs dropped."""
    v = np.asarray(list(values.values()) if isinstance(values, dict) else values, dtype=float)
    keep = ~np.isnan(v)
    return v[keep], int(np.sum(~keep))


def contrast(values: dict[str, float], primary: bool, n_boot: int = N_BOOT) -> dict:
    """Estimate, 95% interval and (primary contrasts only) the 98.33% family interval (§11.1),
    NaNs dropped and counted; discordance counts use the same |v| > NONZERO_EPS rule as `interval`."""
    v, dropped = _clean(values)
    ci95 = e2p2.interval(v, 0.95, n_boot=n_boot, seed=BOOT_SEED)
    family = None
    if primary:  # as summarize2 builds it
        family = {"level": e2p2.FAMILY_LEVEL, **e2p2.interval(v, e2p2.FAMILY_LEVEL, n_boot=n_boot, seed=BOOT_SEED)}
    return {
        "estimate": ci95["estimate"], "n": len(v), "n_dropped_nan": dropped,
        "ci95": {"level": 0.95, **ci95}, "family": family, "n_nonzero": ci95["n_nonzero"],
        "discordance": {"positive": int(np.sum(v > NONZERO_EPS)), "negative": int(np.sum(v < -NONZERO_EPS))},
    }


def tost(values: dict[str, float] | np.ndarray, margin: float, alpha: float, n_boot: int = N_BOOT) -> dict:
    """Two one-sided tests at `alpha` per side: the two-sided 1 - 2 alpha interval, or on the
    rare-event path the one-sided 1 - alpha bound (as `power._h1_tost_ok` and `power.equivalence_ok`),
    strictly inside (-margin, margin). NaNs are dropped; n = 0 is never equivalent."""
    v, dropped = _clean(values)
    level = 1 - 2 * alpha
    base = {"level": level, "n": len(v), "n_dropped_nan": dropped}
    if len(v) == 0:
        return {**base, "method": None, "ci": None, "estimate": None, "n_nonzero": 0, "equivalent": False}
    r = e2p2.interval(v, level, n_boot=n_boot, seed=BOOT_SEED)
    if r["method"] == "bound":
        r = e2p2.interval(v, 1 - alpha, n_boot=n_boot, seed=BOOT_SEED)
    lo, hi = r["ci"]
    return {**base, "method": r["method"], "ci": r["ci"], "estimate": r["estimate"], "n_nonzero": r["n_nonzero"],
            "equivalent": bool(-margin < lo and hi < margin)}


def paired_diff(a: list, b: list, ids: list) -> dict[str, float]:
    """Per puzzle a - b, keyed by id in `ids` order."""
    if not len(a) == len(b) == len(ids):
        raise ValueError(f"length mismatch: {len(a)}, {len(b)}, {len(ids)} ids")
    return {pid: float(x) - float(y) for pid, x, y in zip(ids, a, b)}


def h1_block(perm: list, gen: list, ids: list, perm_seeds: list[list] | None = None,
             gen_seeds: list[list] | None = None, n_boot: int = N_BOOT) -> dict:
    """H1 (§8.3): theta1 = B_permuted - B_generated per puzzle as a primary contrast, its family-level
    TOST (±H1_MARGIN, alpha 0.05/3 per side), the relative improvement theta1 / E[B_permuted] over
    the same puzzles, and per-seed theta1 means without intervals (§11.1, spec ambiguity 18)."""
    d = paired_diff(perm, gen, ids)
    out = contrast(d, primary=True, n_boot=n_boot)
    out["tost"] = tost(d, H1_MARGIN, ALPHA_FAMILY, n_boot=n_boot)
    keep = [not math.isnan(x) for x in d.values()]
    p = np.asarray(perm, dtype=float)[keep]
    out["relative_improvement"] = (out["estimate"] / float(p.mean())
                                   if out["estimate"] is not None and p.mean() != 0 else None)
    out["per_seed"] = None
    if perm_seeds is not None and gen_seeds is not None:
        out["per_seed"] = [float(np.nanmean(np.asarray(ps, dtype=float) - np.asarray(gs, dtype=float)))
                           for ps, gs in zip(perm_seeds, gen_seeds, strict=True)]
    return out


# ---------------------------------------------------------------- E2 descriptive summary

def e2_descriptive(out: dict) -> dict:
    """Statistics-free E2 summary (no interval, TOST, bootstrap or AUC): the shared e2p2 tables,
    the identity counts (spec ambiguity 23) and downstream D code-change quantiles."""
    base_ids = {b["puzzle_id"] for b in out["base"]}
    table = e2p2.configuration_table(out)
    configs = []
    for c in table:
        ok = [r for r in out["records"] if (r["level"], r["policy"], r["dose"]) == (c["level"], c["policy"], c["dose"])
              and r["eligible"]]
        configs.append({"level": c["level"], "policy": c["policy"], "dose": c["dose"],
                        "quantiles": e2p2._quantiles(ok, "downstream_changes_D")})
    level1 = {}
    for policy in POLICIES:
        rows = e2p2._level1_weighted(out["level1"], policy, "downstream_changes_D", base_ids)
        level1[policy] = e2p2._quantiles(rows, "downstream_changes_D")
    return {
        "configurations": table,
        "level1": e2p2.level1_table(out),
        "sham_mismatch": e2p2.sham_mismatch_counts(out),
        "level1_noop_mismatch": out.get("level1_noop_mismatch"),
        "level1_noop_max_tv": out.get("level1_noop_max_tv"),
        "code_mismatch": out.get("code_mismatch"),
        "downstream_changes_D": {"configurations": configs, "level1": level1},
    }


# ---------------------------------------------------------------- AUC over the frozen range

def auc_frozen(nodes_a, nodes_b, rng: tuple[float, float] | None) -> dict:
    """Mean heights of the two merged damage-outcome curves over the §12.2 frozen range, only if
    the TEST nodes of both curves cover it (§7.3); never over a TEST-derived range."""
    merged = {"a": e2p2._merge(nodes_a), "b": e2p2._merge(nodes_b)}
    coverage = {k: ([float(xs[0]), float(xs[-1])] if len(xs) >= 2 else None) for k, (xs, _) in merged.items()}
    covered = rng is not None and all(c is not None and c[0] <= rng[0] and c[1] >= rng[1]
                                      for c in coverage.values())
    res = {"auc_a": None, "auc_b": None, "range": rng, "covered": bool(covered), "reason": None,
           "nodes": {k: [[float(x), float(y)] for x, y in zip(xs, ys)] for k, (xs, ys) in merged.items()},
           "coverage": coverage}
    if rng is None:
        res["reason"] = "no frozen range (§12.2)"
    elif not covered:
        res["reason"] = "TEST nodes do not cover the frozen range"
    else:
        lo, hi = rng
        res["auc_a"] = e2p2._mean_on(*merged["a"], lo, hi)
        res["auc_b"] = e2p2._mean_on(*merged["b"], lo, hi)
    return res


# ---------------------------------------------------------------- §13 readings

def _row(result: str, claim: str, does_not_follow: str) -> dict:
    return {"result": result, "claim": claim, "does_not_follow": does_not_follow}


# Verbatim from research_plan_v3.7.md §13 (tests/test_wp2eval.py checks each table row)
S13: dict[str, dict] = {
    "early_sensitivity": _row(
        "Early single-code replacement causes greater degradation",
        "Greater level sensitivity under the given policy",
        "The coarse code explicitly plans an algorithm; a level 1 vs. 11 difference implies a graded "
        "sensitivity along the early levels or is independent of level 1's single-code size and learned upsampler"),
    "d_better_than_c": _row(
        "D better than C, corrected for sham",
        "Later generation attenuates the intervention effect",
        "The improvement is certainly logical error correction"),
    "positive_compensation": _row(
        "Positive compensation in a checkpoint trained with level corruption",
        "Robustness consistent with the training objective",
        "The model spontaneously detects and repairs logical errors"),
    "probe_beats_null": _row(
        "Generated probe beats the null control",
        "The label is readable with the examined readout",
        "The model contains more information than the input, or the generator uses the read-out feature"),
    "raw_ceiling": _row(
        "Raw-input baseline reaches the ceiling",
        "The initial label is directly accessible from the input",
        "There is no logical information in the latent space"),
    "levels_2_11_equiv": _row(
        "Levels 2 vs. 11 interval inside ±3 pp with adequate precision",
        "No practically relevant solve difference between levels 2 and 11 under the given policy",
        "Level 2 carries no information or has no causal role"),
    "h1_small_positive": _row(
        "H1: 98.33% lower limit > 0 and the 96.67% interval inside ±0.01",
        "The candidate mask is readable from the level-6 state above the permuted null control, but by less "
        "than the practical threshold, with the examined probe family and budget",
        "The representation computes candidates, or carries no candidate information; another readout could "
        "not do better"),
    "h1_no_practical": _row(
        "H1: 96.67% interval inside ±0.01 and the 98.33% interval contains 0",
        "No practically relevant level-6 readability under the examined probe family and budget",
        "Candidate information is absent from the model"),
    "h1_negative": _row(
        "H1: 98.33% upper limit < 0",
        "The generated-representation probe reads the label worse than the permuted null control",
        "Readability; a harmful representation in general"),
    "h1_readable_not_equiv": _row(
        "H1: 98.33% lower limit > 0 and the 96.67% interval not inside ±0.01",
        "The label is readable above the null control; practical relevance is not shown to be below the threshold",
        "Explicit candidate computation"),
    "l12_solution_content": _row(
        "Level-12 readout clearly above the null control and teacher − generated inside ±0.01",
        "The level-12 readability is consistent with solution content",
        "The generated representation computes candidates or encodes inference steps"),
    "equiv_accurate_not_equivariant": _row(
        "Level-12 readout accurate on transformed puzzles but not equivariant at the seed-noise tolerance "
        "(exploratory)",
        "Per-cell predictions change under symmetry while accuracy does not",
        "The model lacks symmetry-consistent representations in general"),
    "equivariance_succeeds": _row(
        "Equivariance succeeds",
        "More stable readout under symmetry",
        "General reasoning ability is proven"),
    "non_significant": _row(
        "Non-significant result",
        "The given design provides insufficient evidence for the designated effect",
        "The effect or the logical representation is certainly absent"),
}


def _reading(hypothesis: str, row: str | None, inputs: dict, note: str | None = None) -> dict:
    if row is None:
        return {"hypothesis": hypothesis, "row": None, "result": None, "claim": None, "does_not_follow": None,
                "note": note, "inputs": inputs}
    return {"hypothesis": hypothesis, "row": row, **S13[row], "note": note, "inputs": inputs}


def _no_row(hypothesis: str, reason: str, inputs: dict) -> dict:
    return _reading(hypothesis, None, inputs, f"{NO_ROW} ({reason})")


def _fam_inputs(x: dict) -> dict:
    return {"estimate": x["estimate"], "family_ci": tuple(x["family"]["ci"])}


def _h1(x: dict) -> list[dict]:
    fl, fh = x["family"]["ci"]
    eq = bool(x["tost"]["equivalent"])
    inputs = {**_fam_inputs(x), "tost_ci": x["tost"].get("ci"), "tost_equivalent": eq}
    if fl > 0 and eq:
        rows = ["h1_small_positive"]
    elif eq and fl <= 0 <= fh:
        rows = ["h1_no_practical"]
    elif fh < 0:
        rows = ["h1_negative"]
    elif fl > 0:
        rows = ["h1_readable_not_equiv"]
    else:
        rows = ["non_significant"]
    if fl > 0:
        rows.append("probe_beats_null")
    return [_reading("H1", row, inputs) for row in rows]


def _h2(x: dict) -> list[dict]:
    fl, fh = x["family"]["ci"]
    inputs = _fam_inputs(x)
    if fh < 0:
        return [_reading("H2", "early_sensitivity", inputs)]
    if fl <= 0:
        return [_reading("H2", "non_significant", inputs)]
    return [_no_row("H2", "late level more sensitive", inputs)]


def _h3(x: dict) -> list[dict]:
    fl, fh = x["family"]["ci"]
    inputs = _fam_inputs(x)
    if fl > 0:
        return [_reading("H3", row, inputs) for row in ("d_better_than_c", "positive_compensation")]
    if fh >= 0:
        return [_reading("H3", "non_significant", inputs)]
    return [_no_row("H3", "negative compensation", inputs)]


def _theta2_prime(x: dict) -> list[dict]:
    l95, h95 = x["ci95"]["ci"]
    eq = bool(x["tost"]["equivalent"])
    inputs = {"estimate": x["estimate"], "ci95": (l95, h95), "tost_ci": x["tost"].get("ci"), "tost_equivalent": eq}
    if eq:
        return [_reading("theta2_prime", "levels_2_11_equiv", inputs)]
    if l95 <= 0 <= h95:
        return [_reading("theta2_prime", "non_significant", inputs)]
    return [_no_row("theta2_prime", "θ₂′ not equivalent; 95% interval excludes 0", inputs)]


def _level12(wl: dict, theta_t: dict) -> list[dict]:
    l95 = wl["ci95"]["ci"][0]
    eq = bool(theta_t["tost"]["equivalent"])
    inputs = {"theta1_L12_wl_estimate": wl["estimate"], "theta1_L12_wl_ci95": tuple(wl["ci95"]["ci"]),
              "theta_T_estimate": theta_t["estimate"], "theta_T_tost_ci": theta_t["tost"].get("ci"),
              "theta_T_tost_equivalent": eq}
    if l95 > 0 and eq:
        return [_reading("level12", "l12_solution_content", inputs)]
    failed = ([] if l95 > 0 else ["theta1_L12_wl 95% lower limit not above 0"]) + \
        ([] if eq else ["theta_T TOST not equivalent"])
    return [_no_row("level12", "level-12 criterion not met: " + "; ".join(failed), inputs)]


def select_readings(r: dict) -> list[dict]:
    """Mechanical §13 readings for H1, H2, H3, theta2_prime, the level-12 row and the exploratory
    equivariance analysis (spec ambiguities 7-10, 23). `raw_ceiling` is never selected."""
    readings = _h1(r["H1"])
    e2 = ("H2", "H3", "theta2_prime")
    if any(isinstance(r[k], dict) and r[k].get("status") == "identity-failure" for k in e2):
        readings.append(_reading("E2", None, {k: r[k].get("status") for k in e2}, E2_IDENTITY_NOTE))
    else:
        readings += _h2(r["H2"]) + _h3(r["H3"]) + _theta2_prime(r["theta2_prime"])
    readings += _level12(r["theta1_L12_wl"], r["theta_T"])
    readings.append(_reading("equivariance", None, r["equivariance"], EQUIV_READING))
    return readings
