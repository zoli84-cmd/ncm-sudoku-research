"""E2 and E3-H1 sample-size and lock power simulation (plan v3.6 §11.4; D60, D70). Non-confirmatory planning from pilot puzzle-level values.

Each simulated sample resamples n puzzle-level values (in [-1, 1]) from the pilot with replacement,
applies the scenario transform per drawn value, and runs the real interval rule (`e2p2.interval`).
"""

import numpy as np

from ncm_sudoku.e2p2 import FAMILY_LEVEL, TOST_MARGIN, interval

H2_EFFECT = 0.05
H3_HALF_WIDTH = 0.03
NS = range(100, 3001, 100)


def _draw(x, rng, size):
    return x if size is None else x[rng.integers(0, len(x), size)]


def thin(x: np.ndarray, target: float, rng, size: int | None = None) -> np.ndarray:
    """Keep each nonzero value with probability |target| / |mean(x)|, else zero; `size` resamples x first."""
    x = np.asarray(x, dtype=float)
    p = abs(target) / abs(x.mean())
    y = _draw(x, rng, size)
    return np.where(rng.random(len(y)) < p, y, 0.0)


def sign_mix(x: np.ndarray, target: float, rng, size: int | None = None) -> np.ndarray:
    """Keep |x|; each nonzero value gets sign(target) with p = (1 + |target| / mean|x|) / 2."""
    x = np.asarray(x, dtype=float)
    m = np.abs(x).mean()
    if m < abs(target):
        raise ValueError(f"mean|x| = {m:.4f} < |target| = {abs(target):.4f}")
    p = (1 + abs(target) / m) / 2
    y = np.abs(_draw(x, rng, size))
    return np.where(rng.random(len(y)) < p, np.sign(target), -np.sign(target)) * y


def inject(x: np.ndarray, target: float, rng, size: int | None = None) -> np.ndarray:
    """D70(1): resample x (`size` draws, or x itself), then set each drawn zero to sign(target)
    with p = (target - mean(x)) / (zero share(x) * sign(target)), so the expected mean is target.
    Nonzero values are unchanged; ValueError when z = 0 or p is outside [0, 1]."""
    x = np.asarray(x, dtype=float)
    z, s = float(np.mean(x == 0)), float(np.sign(target))
    if z == 0 or s == 0:
        raise ValueError(f"injection infeasible: zero share {z:.4f}, target {target}")
    p = (target - float(x.mean())) / (z * s)
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"injection infeasible: p = {p:.4f} outside [0, 1] (mean {x.mean():.4f}, zero share {z:.4f})")
    y = _draw(x, rng, size).copy()
    hit = (y == 0) & (rng.random(len(y)) < p)
    y[hit] = s
    return y


def sign_flip(x: np.ndarray, rng) -> np.ndarray:
    """Multiply each value by an independent random sign (zeros stay zero)."""
    x = np.asarray(x, dtype=float)
    return x * rng.choice((-1.0, 1.0), len(x))


def _share(sampler, criterion, n, reps, rng) -> float:
    return float(np.mean([criterion(sampler(n, rng)) for _ in range(reps)]))


def required_n(sampler, criterion, ns=NS, reps=500, seed=0, target: float = 0.80) -> int | None:
    """Smallest n whose criterion success share over `reps` simulated samples is >= target; None if none."""
    rng = np.random.default_rng(seed)
    for n in ns:  # ponytail: linear scan stopping at the first hit; bisect if the grid grows
        if _share(sampler, criterion, n, reps, rng) >= target:
            return int(n)
    return None


def equivalence_ok(a: np.ndarray, n_boot_sim: int) -> bool:
    """E2 levels 2 vs. 11 TOST rule: the 90% interval (the one-sided 0.95 bound on the rare-event
    path, mirroring summarize2) lies inside +-TOST_MARGIN."""
    r = interval(a, 0.90, n_boot_sim)
    if r["method"] == "bound":  # TOST at 5% per side: mirror summarize2
        r = interval(a, 0.95, n_boot_sim)
    lo, hi = r["ci"]
    return -TOST_MARGIN < lo and hi < TOST_MARGIN


def e2_sample_size(values: dict[str, np.ndarray], reps=500, n_boot_sim=1000, seed=0, ns=NS) -> dict:
    """Smallest n per E2 target (H2 two scenarios, H3, equivalence) and their maximum rounded up to 100."""
    x2, xc, xp = (np.asarray(values[k], dtype=float) for k in ("theta2", "theta_comp", "theta2_prime"))
    notes = {}

    def h2_ok(a):
        lo, hi = interval(a, FAMILY_LEVEL, n_boot_sim)["ci"]
        return lo > 0 or hi < 0

    def h3_ok(a):
        lo, hi = interval(a, FAMILY_LEVEL, n_boot_sim)["ci"]
        return (hi - lo) / 2 <= H3_HALF_WIDTH

    def eq_ok(a):
        return equivalence_ok(a, n_boot_sim)

    def resample(x):
        return lambda n, rng: _draw(x, rng, n)

    mean2 = float(x2.mean())
    h2_target = H2_EFFECT * float(np.sign(mean2))
    shortfall = abs(mean2) <= H2_EFFECT
    if shortfall:
        notes["h2"] = f"|mean theta2| = {abs(mean2):.4f} <= {H2_EFFECT}: observed values used unchanged"
        h2_thin_sampler = h2_mix_sampler = resample(x2)
    else:
        h2_thin_sampler = lambda n, rng: thin(x2, h2_target, rng, n)
        # feasible: mean|x| >= |mean x| > 0.05, so sign_mix cannot raise here
        h2_mix_sampler = lambda n, rng: sign_mix(x2, h2_target, rng, n)

    out = {
        "h2_target": h2_target,
        "h2_shortfall": shortfall,
        "h2_thinning": required_n(h2_thin_sampler, h2_ok, ns, reps, seed, target=0.90),
        "h2_sign_mix": required_n(h2_mix_sampler, h2_ok, ns, reps, seed, target=0.90),
        "h3": required_n(resample(xc), h3_ok, ns, reps, seed),
        "equivalence": required_n(lambda n, rng: sign_flip(_draw(xp, rng, n), rng), eq_ok, ns, reps, seed),
    }

    err = {}
    for key, t in (("+0.03", TOST_MARGIN), ("-0.03", -TOST_MARGIN)):
        if out["equivalence"] is None:
            err[key] = None
            continue
        try:
            sign_mix(xp, t, np.random.default_rng(0))
        except ValueError as e:
            notes[f"equivalence_error_{key}"] = f"infeasible: {e}"
            err[key] = None
            continue
        rng = np.random.default_rng(seed)
        err[key] = _share(lambda n, r: sign_mix(xp, t, r, n), eq_ok, out["equivalence"], reps, rng)
    if out["equivalence"] is None:
        notes["equivalence_error"] = "not computed: no n met the equivalence target"
    out["equivalence_error_at_boundary"] = err

    ns_req = [out[k] for k in ("h2_thinning", "h2_sign_mix", "h3", "equivalence")]
    out["max_rounded"] = None if None in ns_req else -(-max(ns_req) // 100) * 100
    out["notes"] = notes
    out["planning_parameters"] = {
        "reps": reps, "n_boot_sim": n_boot_sim, "seed": seed, "ns": [int(n) for n in ns],
        "h2_power_target": 0.90, "h2_level": FAMILY_LEVEL, "h3_half_width": H3_HALF_WIDTH,
        "h3_level": FAMILY_LEVEL, "h3_share_target": 0.80, "equivalence_margin": TOST_MARGIN,
        "equivalence_level": 0.90, "equivalence_power_target": 0.80,
        "resampling": "per simulated sample: n draws with replacement from pilot values, transform per draw",
        "non_confirmatory": True,
    }
    return out


H1_TARGET = 0.01


def shift_to(x: np.ndarray, target: float) -> np.ndarray:
    """y = x - mean(x) + target, clipped to [-1, 1] (D60)."""
    x = np.asarray(x, dtype=float)
    return np.clip(x - x.mean() + target, -1.0, 1.0)


def h1_sample_size(diffs, reps=500, n_boot_sim=1000, seed=0, ns=NS) -> dict:
    """Smallest TEST n at which the family-level interval of the shifted PROBE-VAL H1
    differences (B_permuted - B_generated, mean moved to 0.01) lies above 0 with 90%
    power (D60; H1 is directional). Always shifted; `shortfall` flags an observed
    mean below 0.01."""
    x = np.asarray(diffs, dtype=float)
    x = x[~np.isnan(x)]
    y = shift_to(x, H1_TARGET)

    def ok(a):
        return interval(a, FAMILY_LEVEL, n_boot_sim)["ci"][0] > 0

    observed = float(x.mean())
    return {
        "h1": required_n(lambda n, rng: _draw(y, rng, n), ok, ns, reps, seed, target=0.90),
        "shortfall": observed < H1_TARGET,
        "observed_mean": observed,
        "n_pilot": int(len(x)),
        "planning_parameters": {
            "reps": reps, "n_boot_sim": n_boot_sim, "seed": seed, "ns": [int(n) for n in ns],
            "h1_shift_target": H1_TARGET, "h1_power_target": 0.90, "h1_level": FAMILY_LEVEL,
            "resampling": "per simulated sample: n draws with replacement from the shifted pilot values",
            "non_confirmatory": True,
        },
    }


def equivalence_boundary_error(xp, n=600, reps=500, n_boot_sim=1000, seed=0) -> dict:
    """D70(1): false-equivalence share of the E2 TOST rule (`equivalence_ok`) at n when the
    pilot theta2' values are injected to an expected effect of +TOST_MARGIN and -TOST_MARGIN."""
    xp = np.asarray(xp, dtype=float)
    err, notes = {}, {}
    for key, t in (("+0.03", TOST_MARGIN), ("-0.03", -TOST_MARGIN)):
        try:
            inject(xp, t, np.random.default_rng(0))
        except ValueError as e:
            err[key], notes[key] = None, str(e)
            continue
        rng = np.random.default_rng(seed)
        err[key] = _share(lambda m, r: inject(xp, t, r, m), lambda a: equivalence_ok(a, n_boot_sim), n, reps, rng)
    return {
        "error": err,
        "pilot_mean": float(xp.mean()), "pilot_zero_share": float(np.mean(xp == 0)), "n_pilot": int(len(xp)),
        "notes": notes,
        "planning_parameters": {
            "n": int(n), "reps": reps, "n_boot_sim": n_boot_sim, "seed": seed, "margin": TOST_MARGIN,
            "level": 0.90, "bound_level": 0.95,
            "scenario": "per simulated sample: n draws with replacement from pilot values, each drawn zero "
                        "set to sign(target) with the probability that makes the expected mean equal target",
            "non_confirmatory": True,
        },
    }


H1_MARGIN = 0.01
H1_TOST_LEVEL = 1 - 2 * (0.05 / 3)


def _h1_tost_ok(a, n_boot_sim, margin) -> bool:
    """Family-level TOST (alpha 0.05/3 per side): two-sided 1 - 2 alpha bootstrap interval, or the
    one-sided 1 - alpha rare-event bound, inside +-margin."""
    r = interval(a, H1_TOST_LEVEL, n_boot_sim)
    if r["method"] == "bound":  # one-sided limit at alpha per side, as in equivalence_ok
        r = interval(a, FAMILY_LEVEL, n_boot_sim)
    lo, hi = r["ci"]
    return -margin < lo and hi < margin


def _excludes_zero(a, n_boot_sim) -> bool:
    lo, hi = interval(a, FAMILY_LEVEL, n_boot_sim)["ci"]
    return lo > 0 or hi < 0


def h1_tost(diffs, n=600, reps=500, n_boot_sim=1000, seed=0, margin=H1_MARGIN) -> dict:
    """D70(2): family-level H1 TOST at n from PROBE-VAL puzzle-level differences
    (B_permuted - B_generated): power with the diffs re-centred at 0 and unchanged (observed mean),
    false-equivalence rate with the diffs shifted to +margin and -margin, and the share of runs at
    the observed mean whose 98.33% family interval excludes 0."""
    x = np.asarray(diffs, dtype=float)
    x = x[~np.isnan(x)]
    tost = lambda a: _h1_tost_ok(a, n_boot_sim, margin)  # noqa: E731

    def share(y, crit):
        return _share(lambda m, r: _draw(y, r, m), crit, n, reps, np.random.default_rng(seed))

    rng = np.random.default_rng(seed)  # observed mean: TOST and exclusion of 0 on the same samples
    pairs = np.array([(tost(a), _excludes_zero(a, n_boot_sim)) for a in (_draw(x, rng, n) for _ in range(reps))])
    return {
        "power_at_zero": share(shift_to(x, 0.0), tost),
        "power_at_observed": float(pairs[:, 0].mean()),
        "false_equivalence": {f"+{margin}": share(shift_to(x, margin), tost),
                              f"-{margin}": share(shift_to(x, -margin), tost)},
        "excludes_zero_at_observed": float(pairs[:, 1].mean()),
        "inside_and_above_zero_at_observed": float(np.mean(pairs[:, 0] & pairs[:, 1])),
        "observed_mean": float(x.mean()), "observed_sd": float(x.std(ddof=1)) if len(x) > 1 else None,
        "n_pilot": int(len(x)),
        "planning_parameters": {
            "n": int(n), "reps": reps, "n_boot_sim": n_boot_sim, "seed": seed, "margin": margin,
            "tost_level": H1_TOST_LEVEL, "bound_level": FAMILY_LEVEL, "excludes_zero_level": FAMILY_LEVEL,
            "resampling": "per simulated sample: n draws with replacement from the (shifted) pilot values; "
                          "shifts by shift_to (clipped to [-1, 1])",
            "non_confirmatory": True,
        },
    }
