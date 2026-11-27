"""E5 TEST-size simulation (D105(4)-(6); planning model, not a TEST calibration).

Usage: uv run --locked python scripts/e5_power.py [--force]

Generating model: whole PROBE-VAL pair rows (pilot per-pair W(P2), W(Z<=6) and the
causal directed effects of Q, the random-subspace mean, the high-variance and the
shuffled-digit controls and the both-empty full-swap reference, both orders averaged),
resampled with replacement under scenario weights; Delta and the contrasts are always
recomputed. Decisions: `ncm_sudoku.e5stats.claim_a` / `claim_b` (one-sided betting tests,
alpha 0.025 per claim). Scenarios (D105(6)): W(Z) by exponential reweighting keeping the
total weight of the exact-0.5 rows; W(P) = 0.5 + kappa (W_P2 − 0.5); causal effects
scaled jointly; B2–B4 nulls by mixing the control towards the full-swap reference.

N_power = smallest N on 250..1000 (step 50) with power >= 0.9 for both claims under the
chosen planning model (b), 2,000 replications per point (seed GRID_SEED); re-check at
N_power with RECHECK_SEED; then N = max(N_power, 250). Also: pilot-model power, the
same-mean heterogeneous case, and null-boundary false-positive rates at N (10,000
replications). Writes experiments/e5/power.json.
"""

import json
import sys
import time

import numpy as np

from ncm_sudoku.e5stats import ALPHA, C_TRUNC, DELTA_MIN, EPSILON, B1_MIN, claim_a, claim_b
from ncm_sudoku.g0 import code_state
from ncm_sudoku.model import ROOT

OUT = ROOT / "experiments" / "e5" / "power.json"
GRID = list(range(250, 1001, 50))
R_GRID, R_CHECK = 2000, 10000
GRID_SEED, RECHECK_SEED, CHECK_SEED = 2026112701, 2026112702, 2026112703
TARGET = 0.9


def load_rows() -> dict:
    pilot = ROOT / "experiments" / "e5" / "pilot"
    wz = np.array(json.loads((pilot / "z6__shared__none.json").read_text())["w_auc"]["per_pair"], float)
    wp = np.array(json.loads((pilot / "P2__shared__none.json").read_text())["w_auc"]["per_pair"], float)
    d = json.loads((ROOT / "experiments" / "e5" / "causal" / "primary_per_pair.json").read_text())["directed"]
    return {"wz": wz, "wp2": wp, "Q": np.array(d["Q"]), "rand": np.array(d["random_mean"]),
            "hv": np.array(d["hv"]), "shuf": np.array(d["shuf"]), "full": np.array(d["full_be"])}


def tilt_weights(wz: np.ndarray, target: float) -> np.ndarray:
    """Resampling weights with weighted mean of wz equal to target: exact-0.5 rows keep
    their total weight; the other rows get weights proportional to exp(theta * wz)."""
    tie = wz == 0.5
    base = np.full(len(wz), 1.0 / len(wz))
    other = ~tie
    mass = base[other].sum()

    def mean_for(theta):
        e = np.exp(theta * (wz[other] - wz[other].mean()))
        w = base.copy()
        w[other] = mass * e / e.sum()
        return (w * wz).sum(), w

    lo, hi = -2000.0, 2000.0
    for _ in range(200):
        mid = (lo + hi) / 2
        m, _ = mean_for(mid)
        lo, hi = (mid, hi) if m < target else (lo, mid)
    m, w = mean_for((lo + hi) / 2)
    if abs(m - target) > 1e-9:
        raise ValueError(f"cannot reach W(Z) mean {target} (got {m})")
    return w


def scenario(rows: dict, wz_target=None, kappa=1.0, scale=1.0, mix=None) -> dict:
    w = tilt_weights(rows["wz"], wz_target) if wz_target is not None else np.full(len(rows["wz"]), 1 / len(rows["wz"]))
    cols = {"wz": rows["wz"].copy(), "wp": 0.5 + kappa * (rows["wp2"] - 0.5)}
    for k in ("Q", "rand", "hv", "shuf", "full"):
        cols[k] = rows[k] * scale
    if mix is not None:
        C, F, Q = cols[mix], cols["full"], cols["Q"]
        t = ((w * Q).sum() - (w * C).sum()) / ((w * F).sum() - (w * C).sum())
        cols[mix] = (1 - t) * C + t * F
        cols["mix_t"] = float(t)
    means = {k: float((w * v).sum()) for k, v in cols.items() if isinstance(v, np.ndarray)}
    means.update({"Delta": means["wp"] - means["wz"], "Q_minus_rand": means["Q"] - means["rand"],
                  "Q_minus_hv": means["Q"] - means["hv"], "Q_minus_shuf": means["Q"] - means["shuf"]})
    return {"weights": w, "cols": cols, "means": means}


def simulate(sc: dict, n: int, reps: int, seed: int, hetero: bool = False) -> dict:
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(sc["weights"]), size=(reps, n), p=sc["weights"])
    c = {k: v[idx] for k, v in sc["cols"].items() if isinstance(v, np.ndarray)}
    if hetero:  # applied to an unscaled scenario: each pair keeps all causal effects with probability 1/2,
        # otherwise zero, so the means equal those of the planning model (effects halved) with a larger spread
        keep = rng.random((reps, n)) < 0.5
        for k in ("Q", "rand", "hv", "shuf", "full"):
            c[k] = c[k] * keep
    a = claim_a(c["wp"], c["wz"], n_plan=n)
    b = claim_b(c["Q"], c["rand"], c["hv"], c["shuf"], n_plan=n)
    out = {k: float(v.mean()) for k, v in {**a, **b}.items()}
    out["reps"] = reps
    return out


def se(p: float, reps: int) -> float:
    return float(np.sqrt(p * (1 - p) / reps))


def main() -> None:
    if OUT.exists() and "--force" not in sys.argv:
        sys.exit(f"{OUT.relative_to(ROOT)} exists; use --force")
    t0 = time.perf_counter()
    rows = load_rows()
    pilot = scenario(rows)
    plan = scenario(rows, wz_target=0.5 + 0.015, kappa=0.7, scale=0.5)

    grid = []
    n_power = None
    for n in GRID:
        r = simulate(plan, n, R_GRID, GRID_SEED + n)
        grid.append({"N": n, "power_A": r["A"], "power_B": r["B"], "se_A": se(r["A"], R_GRID), "se_B": se(r["B"], R_GRID)})
        print(f"N {n}: A {r['A']:.4f} B {r['B']:.4f}", flush=True)
        if n_power is None and r["A"] >= TARGET and r["B"] >= TARGET:
            n_power = n
            break
    record = {"note": "E5 TEST-size simulation (D105); planning model from PROBE-VAL pilot rows, not a TEST calibration",
              "date": time.strftime("%Y-%m-%d"), "alpha_per_claim": ALPHA, "c": C_TRUNC, "epsilon": EPSILON,
              "delta_min": DELTA_MIN, "b1_min": B1_MIN, "target_power": TARGET,
              "seeds": {"grid": GRID_SEED, "recheck": RECHECK_SEED, "checks": CHECK_SEED},
              "scenario_means": {"pilot": pilot["means"], "planning_b": plan["means"]}, "grid": grid}
    if n_power is None:
        record.update({"N_power": None, "decision": "no grid point up to 1,000 reaches 0.9: no lock and no TEST generation (D105(4))"})
    else:
        recheck = simulate(plan, n_power, R_GRID, RECHECK_SEED)
        n_final = max(n_power, 250)
        ok = recheck["A"] >= TARGET and recheck["B"] >= TARGET
        record.update({"N_power": n_power, "recheck": recheck, "recheck_passed": ok,
                       "N": n_final if ok else None,
                       "decision": f"N = {n_final}" if ok else "re-check below 0.9: no lock and no TEST generation (D105(4))"})
        if ok:
            n = n_final
            record["at_N"] = {
                "pilot_model": simulate(pilot, n, R_CHECK, CHECK_SEED),
                "planning_model": simulate(plan, n, R_CHECK, CHECK_SEED + 1),
                "heterogeneous_sensitivity": simulate(scenario(rows, wz_target=0.5 + 0.015, kappa=0.7, scale=1.0), n, R_CHECK, CHECK_SEED + 2, hetero=True),
            }
            nulls = {
                "A1_lower_wz_0.47": (scenario(rows, wz_target=0.47), "A1_lower", "A"),
                "A1_upper_wz_0.53": (scenario(rows, wz_target=0.53), "A1_upper", "A"),
                "A2_delta_0.25": (scenario(rows, kappa=2 * (DELTA_MIN + float(rows["wz"].mean()) - 0.5)), "A2", "A"),
                "B1_q_0.01": (scenario(rows, scale=B1_MIN / float(rows["Q"].mean())), "B1", "B"),
                "B2_mix_random": (scenario(rows, mix="rand"), "B2", "B"),
                "B3_mix_high_variance": (scenario(rows, mix="hv"), "B3", "B"),
                "B4_mix_shuffled": (scenario(rows, mix="shuf"), "B4", "B"),
            }
            fpr = {}
            for j, (name, (sc, cond, claim)) in enumerate(nulls.items()):
                r = simulate(sc, n, R_CHECK, CHECK_SEED + 10 + j)
                fpr[name] = {"condition": cond, "rate_condition": r[cond], "se_condition": se(r[cond], R_CHECK),
                             "claim": claim, "rate_claim": r[claim], "se_claim": se(r[claim], R_CHECK),
                             "generating_means": sc["means"], "mix_t": sc["cols"].get("mix_t")}
                print(f"null {name}: {cond} {r[cond]:.4f}  {claim} {r[claim]:.4f}", flush=True)
            record["null_boundaries_at_N"] = fpr
    record["seconds"] = round(time.perf_counter() - t0, 1)
    record["code_state"] = code_state()
    OUT.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: record.get(k) for k in ("N_power", "recheck_passed", "N", "decision")}))


if __name__ == "__main__":
    main()
