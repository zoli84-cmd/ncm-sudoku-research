"""E2 pilot 2: level-1 enumeration, v3.6 dose grid, damage measures (plan v3.6 §7).

Non-confirmatory. Branches: A clean, B sham restart from level l with A's codes,
C level l perturbed with A's suffix replayed, D level l perturbed with the suffix
regenerated. Damage measures compare C against A on the final cumulative state.
"""

import math
from collections import defaultdict

import numpy as np
import torch

from ncm_sudoku.damage import codebook_rms, latent_distance, requantize, tv_damage
from ncm_sudoku.e2 import POLICIES, _chunked, _eval
from ncm_sudoku.intervene import continue_generation
from ncm_sudoku.model import NcmModel, level_slices
from ncm_sudoku.perturb import (
    DOSE_FRACTIONS_V36, N_CODES, code_frequencies, dose_grid, level1_weights, perturb_level, run_seed,
)
from ncm_sudoku.runner import generate_codes, puzzle_tensor
from ncm_sudoku.states import cumulative_states, decode_state_logits
from ncm_sudoku.validate import cell_hamming

LEVELS_P2 = (2, 6, 11)
SEEDS_P2 = (0, 1, 2)
FAMILY_LEVEL = 1 - 0.05 / 3  # Bonferroni over the three E2 contrasts
TOST_MARGIN = 0.03
QUANTILES = (0.0, 0.25, 0.5, 0.75, 1.0)
DAMAGE_KEYS = ("tv", "tv_empty", "hamming_CA", "latent", "codebook_rms", "requant_ratio")


@torch.no_grad()
def run_pilot2(m: NcmModel, puzzles: np.ndarray, solutions: np.ndarray, puzzle_ids: list[str],
               chunk: int = 50) -> dict:
    n = len(puzzles)
    prefix = puzzle_tensor(puzzles)
    slices = level_slices(m.levels)
    empty = torch.as_tensor(np.asarray(puzzles) == 0)
    A = _chunked(lambda s: generate_codes(m, puzzles[s], batch_size=chunk), n, chunk)
    parsed_A, met_A = _eval(puzzles, solutions, A, m)
    z_A = _chunked(lambda s: cumulative_states(m, A[s])[-1], n, chunk)
    logits_A = _chunked(lambda s: decode_state_logits(m, z_A[s]), n, chunk)
    freqs1 = code_frequencies(A, m.levels)[0]

    def compare(idx: torch.Tensor, C: torch.Tensor, level: int) -> list[dict]:
        """Branches C (given) and D (regenerated) for puzzle rows `idx`; one dict per row."""
        k, end = len(idx), slices[level - 1].stop
        D = _chunked(lambda s: continue_generation(m, prefix[idx[s]], C[s, :end], level), k, chunk)
        p_sub, s_sub = puzzles[idx.numpy()], solutions[idx.numpy()]
        parsed_C, met_C = _eval(p_sub, s_sub, C, m)
        _, met_D = _eval(p_sub, s_sub, D, m)
        tv, tv_e, lat, ratio = [], [], [], []
        for i in range(0, k, chunk):
            s = slice(i, min(i + chunk, k))
            rows = idx[s]
            states = cumulative_states(m, C[s])
            logits_C = decode_state_logits(m, states[-1])
            tv.append(tv_damage(logits_C, logits_A[rows]))
            tv_e.append(tv_damage(logits_C, logits_A[rows], empty[rows]))
            lat.append(latent_distance(states[-1], z_A[rows]))
            ratio.append(requantize(m, z_A[rows] - states[level - 1], level + 1)[1])
        tv, tv_e, lat, ratio = (torch.cat(t).tolist() for t in (tv, tv_e, lat, ratio))
        sl = slices[level - 1]
        rms = codebook_rms(m, level, A[idx][:, sl], C[:, sl]).tolist()
        changes = (D[:, end:] != A[idx][:, end:]).sum(dim=1).tolist()
        out = []
        for j, i in enumerate(idx.tolist()):
            both_ok = met_C[j].well_formed and met_A[i].well_formed
            out.append({
                "solve_C": int(met_C[j].solve), "solve_D": int(met_D[j].solve),
                "well_formed_C": bool(met_C[j].well_formed), "well_formed_D": bool(met_D[j].well_formed),
                "tv": tv[j], "tv_empty": tv_e[j],
                "hamming_CA": cell_hamming(parsed_C[j].cells, parsed_A[i].cells) if both_ok else None,
                "latent": lat[j], "codebook_rms": rms[j], "requant_ratio": ratio[j],
                "downstream_changes_D": int(changes[j]),
            })
        return out

    B1 = _chunked(lambda s: continue_generation(m, prefix[s], A[s, :1], 1), n, chunk)
    _, met_B1 = _eval(puzzles, solutions, B1, m)
    base = [{"puzzle_id": puzzle_ids[i], "solve_A": int(met_A[i].solve), "solve_B1": int(met_B1[i].solve)}
            for i in range(n)]

    a1 = A[:, slices[0]].squeeze(1)  # level 1 has a single code
    w = {p: level1_weights(a1, freqs1, p) for p in POLICIES}
    level1 = []
    for v in range(N_CODES):
        idx = torch.nonzero(a1 != v).squeeze(1)
        if len(idx) == 0:
            continue
        C = A[idx].clone()
        C[:, 0] = v
        for i, rec in zip(idx.tolist(), compare(idx, C, 1)):
            level1.append({"puzzle_id": puzzle_ids[i], "value": v,
                           "w_frequency": float(w["frequency"][i, v]), "w_uniform": float(w["uniform"][i, v]),
                           **rec})

    records = []
    all_rows = torch.arange(n)
    for level in LEVELS_P2:
        sl, end = slices[level - 1], slices[level - 1].stop
        B = _chunked(lambda s: continue_generation(m, prefix[s], A[s, :end], level), n, chunk)
        _, met_B = _eval(puzzles, solutions, B, m)
        freqs = code_frequencies(A, m.levels)[level - 1]
        for policy in POLICIES:
            for dose in dose_grid(sl.stop - sl.start, DOSE_FRACTIONS_V36):
                for seed in SEEDS_P2:
                    gen = torch.Generator().manual_seed(run_seed(level, policy, dose, seed))
                    new_level, eligible = perturb_level(A[:, sl], dose, policy, freqs, gen)
                    C = A.clone()
                    C[:, sl] = new_level
                    for i, rec in enumerate(compare(all_rows, C, level)):
                        records.append({"puzzle_id": puzzle_ids[i], "level": level, "policy": policy,
                                        "dose": dose, "seed": seed, "eligible": bool(eligible[i]),
                                        "solve_A": int(met_A[i].solve), "solve_B": int(met_B[i].solve), **rec})

    return {"freqs_level1": freqs1.tolist(), "base": base, "level1": level1, "records": records}


# ---------------------------------------------------------------- statistics (plan v3.6 §7.2, §11.2)

def _level1_terms(out: dict, policy: str) -> dict[str, tuple[float, float]]:
    """Per eligible puzzle: (sum_v w (D - A), sum_v w (D - C)) at level 1; ineligible = weights sum to 0."""
    A = {b["puzzle_id"]: b["solve_A"] for b in out["base"]}
    acc = defaultdict(lambda: [0.0, 0.0, 0.0])
    for r in out["level1"]:
        w, t = r[f"w_{policy}"], acc[r["puzzle_id"]]
        t[0] += w
        t[1] += w * (r["solve_D"] - A[r["puzzle_id"]])
        t[2] += w * (r["solve_D"] - r["solve_C"])
    return {pid: (da, dc) for pid, (ws, da, dc) in acc.items() if ws > 0}


def _seed_means(out: dict, level: int, policy: str, dose: int = 1, all_seeds: bool = True) -> dict:
    """Per puzzle: (mean tv, mean (D - A)) over seeds. all_seeds=True drops puzzles with any ineligible
    seed; otherwise ineligible seeds are skipped."""
    acc, bad = defaultdict(list), set()
    for r in out["records"]:
        if r["level"] == level and r["policy"] == policy and r["dose"] == dose:
            if r["eligible"]:
                acc[r["puzzle_id"]].append((r["tv"], r["solve_D"] - r["solve_A"]))
            else:
                bad.add(r["puzzle_id"])
    return {pid: tuple(np.mean(v, axis=0)) for pid, v in acc.items() if not (all_seeds and pid in bad)}


def puzzle_values(out: dict, contrast: str, policy: str = "frequency") -> dict[str, float]:
    """Puzzle-level values of theta2, theta_comp or theta2_prime; only puzzles eligible for every term."""
    if contrast == "theta_comp":
        B = {b["puzzle_id"]: b["solve_B1"] - b["solve_A"] for b in out["base"]}
        return {pid: dc - B[pid] for pid, (_, dc) in _level1_terms(out, policy).items()}
    l11 = _seed_means(out, 11, policy)
    if contrast == "theta2":
        first = {pid: da for pid, (da, _) in _level1_terms(out, policy).items()}
    elif contrast == "theta2_prime":
        first = {pid: y for pid, (_, y) in _seed_means(out, 2, policy).items()}
    else:
        raise ValueError(f"unknown contrast {contrast!r}")
    return {pid: first[pid] - l11[pid][1] for pid in first if pid in l11}


def _binom_cdf(k: int, n: int, p: float) -> float:
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 1.0 if k >= n else 0.0
    lp, lq, c = math.log(p), math.log1p(-p), math.lgamma(n + 1)
    logs = [c - math.lgamma(j + 1) - math.lgamma(n - j + 1) + j * lp + (n - j) * lq for j in range(k + 1)]
    top = max(logs)
    return math.exp(top) * math.fsum(math.exp(x - top) for x in logs)


def cp_upper(k: int, n: int, level: float) -> float:
    """One-sided Clopper-Pearson upper limit: the p with P(X <= k | n, p) = 1 - level."""
    if k >= n:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(100):  # the CDF decreases in p
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if _binom_cdf(k, n, mid) > 1 - level else (lo, mid)
    return hi


def interval(values: np.ndarray, level: float, n_boot: int = 10000, seed: int = 0,
             min_nonzero: int = 20) -> dict:
    """Percentile cluster bootstrap over puzzles, or the rare-event bound |delta| <= q (plan §11.2)."""
    v = np.asarray(values, dtype=float)
    n, nz = len(v), int(np.count_nonzero(v))
    est = float(v.mean()) if n else None
    if nz < min_nonzero:
        q = cp_upper(nz, n, level)
        return {"method": "bound", "estimate": est, "ci": (-q, q), "n": n, "n_nonzero": nz}
    means = v[np.random.default_rng(seed).integers(0, n, (n_boot, n))].mean(axis=1)
    lo, hi = np.quantile(means, [(1 - level) / 2, (1 + level) / 2])
    return {"method": "bootstrap", "estimate": est, "ci": (float(lo), float(hi)), "n": n, "n_nonzero": nz}


def dose_nodes(out: dict, level: int, policy: str = "frequency") -> list[tuple[float, float]]:
    """One (mean tv, mean (D - A)) node per dose; seeds averaged within puzzle (eligible only), then puzzles."""
    doses = sorted({r["dose"] for r in out["records"] if r["level"] == level and r["policy"] == policy})
    nodes = []
    for dose in doses:
        per = _seed_means(out, level, policy, dose, all_seeds=False)
        if per:
            x, y = np.mean(list(per.values()), axis=0)
            nodes.append((float(x), float(y)))
    return nodes


def _merge(nodes) -> tuple[np.ndarray, np.ndarray]:
    """Sort nodes by damage and average the outcomes of nodes with equal damage."""
    acc = defaultdict(list)
    for x, y in nodes:
        acc[x].append(y)
    xs = np.array(sorted(acc))
    return xs, np.array([np.mean(acc[x]) for x in xs])


def _mean_on(xs, ys, lo, hi) -> float:
    """Exact mean of the piecewise-linear curve (xs, ys) over [lo, hi]."""
    grid = np.r_[lo, xs[(xs > lo) & (xs < hi)], hi]
    g = np.interp(grid, xs, ys)
    return float(np.sum(np.diff(grid) * (g[1:] + g[:-1]) / 2) / (hi - lo))


def auc_pair(nodes_a, nodes_b) -> dict:
    """Mean height of two damage-outcome curves over their common damage range."""
    (xa, ya), (xb, yb) = _merge(nodes_a), _merge(nodes_b)
    if len(xa) < 2 or len(xb) < 2:
        return {"auc_a": None, "auc_b": None, "range": None, "reason": "fewer than two distinct damage values"}
    lo, hi = float(max(xa[0], xb[0])), float(min(xa[-1], xb[-1]))
    if hi <= lo:
        return {"auc_a": None, "auc_b": None, "range": (lo, hi), "reason": "no positive-width common range"}
    return {"auc_a": _mean_on(xa, ya, lo, hi), "auc_b": _mean_on(xb, yb, lo, hi), "range": (lo, hi),
            "reason": None}


def _quantiles(rows, key):
    vals = [r[key] for r in rows if r[key] is not None]
    return np.quantile(vals, QUANTILES).tolist() if vals else None


def _level1_weighted(level1, policy, key, pids) -> list[dict]:
    """Per eligible puzzle: {key: sum_v w d / sum_v w} over records with a non-None value (plan §7.2 weights)."""
    acc = defaultdict(lambda: [0.0, 0.0])
    for r in level1:
        if r["puzzle_id"] in pids and r[key] is not None:
            w, t = r[f"w_{policy}"], acc[r["puzzle_id"]]
            t[0] += w * r[key]
            t[1] += w
    return [{key: num / den} for num, den in acc.values() if den > 0]


def _mean(vals):
    return float(np.mean(vals)) if len(vals) else None


def summarize2(out: dict, n_boot: int = 10000) -> dict:
    """Non-confirmatory pilot-2 summary: contrasts with intervals, configuration tables, level-1 means, AUC."""
    contrasts = {}
    for c in ("theta2", "theta_comp", "theta2_prime"):
        contrasts[c] = {}
        for policy in POLICIES:
            v = np.array(list(puzzle_values(out, c, policy).values()))
            ci95 = interval(v, 0.95, n_boot)
            entry = {"estimate": ci95["estimate"], "ci95": ci95, "family": None}
            if c != "theta2_prime" and policy == "frequency":
                entry["family"] = {"level": FAMILY_LEVEL, **interval(v, FAMILY_LEVEL, n_boot)}
            if c == "theta2_prime":
                tost = interval(v, 0.90, n_boot)
                # TOST at 5% per side: the rare-event bound uses the one-sided 0.95 limit
                entry["tost90"] = ci95 if tost["method"] == "bound" else tost
            contrasts[c][policy] = entry
    tost = contrasts["theta2_prime"]["frequency"]["tost90"]

    groups = defaultdict(list)
    for r in out["records"]:
        groups[(r["level"], r["policy"], r["dose"])].append(r)
    configurations = []
    for (level, policy, dose), rows in sorted(groups.items()):
        ok = [r for r in rows if r["eligible"]]
        configurations.append({
            "level": level, "policy": policy, "dose": dose, "n_records": len(rows),
            "excluded_share": 1 - len(ok) / len(rows),
            "solve_mean": {b: _mean([r[f"solve_{b}"] for r in ok]) for b in "ABCD"},
            "format_error_share": {b: _mean([not r[f"well_formed_{b}"] for r in ok]) for b in "CD"},
            # codebook_rms scales differ between levels: compare within a configuration only
            "quantiles": {k: _quantiles(ok, k) for k in DAMAGE_KEYS},
        })

    base = {b["puzzle_id"]: b for b in out["base"]}
    level1 = {}
    for policy in POLICIES:
        acc = defaultdict(lambda: np.zeros(5))
        for r in out["level1"]:
            w = r[f"w_{policy}"]
            acc[r["puzzle_id"]] += [w, w * r["solve_C"], w * r["solve_D"],
                                    w * (not r["well_formed_C"]), w * (not r["well_formed_D"])]
        elig = [t for t in acc.values() if t[0] > 0]
        pids = [p for p, t in acc.items() if t[0] > 0]
        level1[policy] = {
            "n_eligible": len(pids), "excluded_share": 1 - len(pids) / len(base),
            "solve_mean": {"A": _mean([base[p]["solve_A"] for p in pids]),
                           "B1": _mean([base[p]["solve_B1"] for p in pids]),
                           "C": _mean([t[1] for t in elig]), "D": _mean([t[2] for t in elig])},
            "format_error_share": {"C": _mean([t[3] for t in elig]), "D": _mean([t[4] for t in elig])},
            "quantiles": {k: _quantiles(_level1_weighted(out["level1"], policy, k, set(pids)), k)
                          for k in DAMAGE_KEYS},
        }

    return {
        "non_confirmatory": True,
        "freqs_level1": out["freqs_level1"],
        "contrasts": contrasts,
        "equivalence_tost": bool(-TOST_MARGIN < tost["ci"][0] and tost["ci"][1] < TOST_MARGIN),
        "configurations": configurations,
        "level1": level1,
        "auc": {f"{a}-{b}": auc_pair(dose_nodes(out, a), dose_nodes(out, b)) for a, b in ((6, 11), (2, 11))},
    }
