"""E5 confirmatory decision statistics (D105): one-sided betting tests for bounded means.

One function, `betting_logk`, is shared by the simulation and the TEST evaluation.
For values X in [0, 1] and a null boundary m0, the unhedged positive-branch capital
process (Waudby-Smith & Ramdas 2024) with fixed-n predictable plug-in bets is

    K_N(m0) = prod_{i=1..N} (1 + lambda_i (X_i - m0)),
    lambda_{i+1} = min( sqrt(2 log(1/alpha) / (N_plan v_i)), c / m0 ),
    mu_i = (0.5 + sum_{j<=i} X_j) / (i + 1),
    v_i  = (0.25 + sum_{j<=i} (X_j - mu_j)^2) / (i + 1),     (mu_0 = 1/2, v_0 = 1/4)

and the test of H0: E[X] <= m0 rejects when log K_N > log(1/alpha) after the last
observation (terminal decision). With c < 1 the bets keep the capital positive, and
under H0 the capital is a nonnegative supermartingale, so the level is at most alpha.
Arrays may carry leading replicate dimensions; the last axis is the observation order.
"""

import numpy as np

ALPHA = 0.025
C_TRUNC = 0.75
# Transformed null boundaries on [0, 1] (D105(2)); quantities on [-1, 1] use (x + 1) / 2.
EPSILON = 0.03
DELTA_MIN = 0.25
B1_MIN = 0.01


def to_unit(x):
    """[-1, 1] -> [0, 1]."""
    return (np.asarray(x, np.float64) + 1.0) / 2.0


def betting_logk(x, m0: float, n_plan: int | None = None, alpha: float = ALPHA, c: float = C_TRUNC) -> np.ndarray:
    """Terminal log-capital of the one-sided test of E[X] <= m0 (X in [0, 1])."""
    x = np.asarray(x, np.float64)
    if np.any(~np.isfinite(x)) or np.any(x < 0) or np.any(x > 1):
        raise ValueError("betting_logk needs finite values in [0, 1]")
    if not 0 < m0 < 1:
        raise ValueError("m0 must lie in (0, 1)")
    n = x.shape[-1]
    n_plan = n if n_plan is None else n_plan
    idx = np.arange(1, n + 1)
    mu = (0.5 + np.cumsum(x, axis=-1)) / (idx + 1)  # mu_i, i = 1..n
    v = (0.25 + np.cumsum((x - mu) ** 2, axis=-1)) / (idx + 1)  # v_i, i = 1..n
    v_prev = np.concatenate([np.full(x.shape[:-1] + (1,), 0.25), v[..., :-1]], axis=-1)  # v_{i-1} for pair i
    lam = np.minimum(np.sqrt(2.0 * np.log(1.0 / alpha) / (n_plan * v_prev)), c / m0)
    return np.log1p(lam * (x - m0)).sum(axis=-1)


def rejects(x, m0: float, **kw) -> np.ndarray:
    return betting_logk(x, m0, **kw) > np.log(1.0 / ALPHA if "alpha" not in kw else 1.0 / kw["alpha"])


def claim_a(w_p, w_z, n_plan: int | None = None) -> dict:
    """Claim A conditions (D105(3)) on per-pair W-AUCs (last axis = pairs in order)."""
    w_p, w_z = np.asarray(w_p, np.float64), np.asarray(w_z, np.float64)
    a1_lo = rejects(w_z, 0.5 - EPSILON, n_plan=n_plan)
    a1_hi = rejects(1.0 - w_z, 0.5 - EPSILON, n_plan=n_plan)
    a2 = rejects(to_unit(w_p - w_z), to_unit(DELTA_MIN), n_plan=n_plan)
    return {"A1_lower": a1_lo, "A1_upper": a1_hi, "A2": a2, "A": a1_lo & a1_hi & a2}


def claim_b(q, rand, hv, shuf, n_plan: int | None = None) -> dict:
    """Claim B conditions (D105(4)) on per-pair directed effects (TV movement, in [-1, 1])."""
    q, rand, hv, shuf = (np.asarray(a, np.float64) for a in (q, rand, hv, shuf))
    b1 = rejects(to_unit(q), to_unit(B1_MIN), n_plan=n_plan)
    b2 = rejects(to_unit(q - rand), 0.5, n_plan=n_plan)
    b3 = rejects(to_unit(q - hv), 0.5, n_plan=n_plan)
    b4 = rejects(to_unit(q - shuf), 0.5, n_plan=n_plan)
    return {"B1": b1, "B2": b2, "B3": b3, "B4": b4, "B": b1 & b2 & b3 & b4}
