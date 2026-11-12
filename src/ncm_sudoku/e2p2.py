"""E2 pilot 2: level-1 enumeration, v3.6 dose grid, damage measures (plan v3.6 §7).

Non-confirmatory. Branches: A clean, B sham restart from level l with A's codes,
C level l perturbed with A's suffix replayed, D level l perturbed with the suffix
regenerated. Damage measures compare C against A on the final cumulative state.
"""

import json
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
DAMAGE_KEYS = ("tv", "tv_empty", "hamming_CA", "hamming_CA_empty", "latent", "codebook_rms", "requant_ratio")


FROZEN_LEVELS = (1, *LEVELS_P2)  # levels whose frequencies the pilot uses


@torch.no_grad()
def clean_codes(m: NcmModel, puzzles: np.ndarray, chunk: int = 50) -> torch.Tensor:
    """Clean generated codes A (branch A), generated in chunks of `chunk` puzzles."""
    return _chunked(lambda s: generate_codes(m, puzzles[s], batch_size=chunk), len(puzzles), chunk)


def pilot_freqs(A: torch.Tensor, levels, frozen_freqs: dict | None = None) -> tuple[dict[int, torch.Tensor], str]:
    """Per-level code frequencies {level: float32 [16]} and their source. Default: estimated
    from the input codes A (`code_frequencies`, source "input"); with `frozen_freqs` (e.g.
    `load_frozen_freqs` of the CAL file) the given vectors are used (source "frozen"); levels
    1, 2, 6 and 11 are required, each a length-16 nonnegative vector summing to 1."""
    if frozen_freqs is None:
        return {lv: f for lv, f in enumerate(code_frequencies(A, levels), start=1)}, "input"
    missing = [lv for lv in FROZEN_LEVELS if lv not in frozen_freqs]
    if missing:
        raise ValueError(f"frozen_freqs lacks levels {missing}")
    out = {}
    for lv, f in frozen_freqs.items():
        t = torch.as_tensor(np.asarray(f, dtype=np.float32))
        if t.shape != (N_CODES,) or (t < 0).any() or abs(float(t.double().sum()) - 1.0) > 1e-6:
            raise ValueError(f"frozen frequencies for level {lv} are not a length-{N_CODES} distribution")
        out[int(lv)] = t
    return out, "frozen"


def load_frozen_freqs(path) -> dict[int, np.ndarray]:
    """Reads `experiments/lock/cal_freqs.json` ({"levels": {"1": {"counts", "frequencies"}, ...}})
    into {level: float32 [16]}; raises ValueError if a frequency vector differs from the one
    its counts give (counts / sum in float64, then float32, as `code_frequencies`)."""
    obj = json.loads(open(path, encoding="utf-8").read())
    out = {}
    for key, entry in obj["levels"].items():
        f = np.asarray(entry["frequencies"], dtype=np.float32)
        c = np.asarray(entry["counts"], dtype=np.float64)
        if f.shape != (N_CODES,) or c.shape != (N_CODES,) or not np.array_equal(f, (c / c.sum()).astype(np.float32)):
            raise ValueError(f"{path}: level {key} frequencies do not match their counts")
        out[int(key)] = f
    return out


@torch.no_grad()
def branch_context(m: NcmModel, puzzles: np.ndarray, solutions: np.ndarray, A: torch.Tensor,
                   chunk: int = 50) -> dict:
    """What `compare` needs about branch A: prefixes, level slices, empty mask, parsed and
    evaluated A, and A's final cumulative state and decoded logits (in A's chunks)."""
    n = len(puzzles)
    parsed_A, met_A = _eval(puzzles, solutions, A, m)
    z_A = _chunked(lambda s: cumulative_states(m, A[s])[-1], n, chunk)
    return {
        "m": m, "puzzles": puzzles, "solutions": solutions, "A": A, "chunk": chunk,
        "prefix": puzzle_tensor(puzzles), "slices": level_slices(m.levels),
        "empty": torch.as_tensor(np.asarray(puzzles) == 0),
        "parsed_A": parsed_A, "met_A": met_A, "z_A": z_A,
        "logits_A": _chunked(lambda s: decode_state_logits(m, z_A[s]), n, chunk),
    }


@torch.no_grad()
def compare(ctx: dict, idx: torch.Tensor, C: torch.Tensor, level: int) -> list[dict]:
    """Branches C (given) and D (regenerated from C's levels <= `level`) for puzzle rows `idx`,
    in chunks of `ctx["chunk"]`; one dict per row."""
    m, puzzles, solutions, A, chunk = (ctx[k] for k in ("m", "puzzles", "solutions", "A", "chunk"))
    prefix, slices, empty = ctx["prefix"], ctx["slices"], ctx["empty"]
    parsed_A, met_A, z_A, logits_A = (ctx[k] for k in ("parsed_A", "met_A", "z_A", "logits_A"))
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
        empty_cells = np.flatnonzero(np.asarray(puzzles[i]).reshape(-1) == 0)
        out.append({
            "solve_C": int(met_C[j].solve), "solve_D": int(met_D[j].solve),
            "well_formed_C": bool(met_C[j].well_formed), "well_formed_D": bool(met_D[j].well_formed),
            "tv": tv[j], "tv_empty": tv_e[j],
            "hamming_CA": cell_hamming(parsed_C[j].cells, parsed_A[i].cells) if both_ok else None,
            "hamming_CA_empty": (cell_hamming(parsed_C[j].cells, parsed_A[i].cells, empty_cells)
                                 if both_ok else None),
            "latent": lat[j], "codebook_rms": rms[j], "requant_ratio": ratio[j],
            "downstream_changes_D": int(changes[j]),
        })
    return out


@torch.no_grad()
def baseline_b1(m: NcmModel, puzzles: np.ndarray, solutions: np.ndarray, puzzle_ids: list[str],
                ctx: dict) -> list[dict]:
    """Sham B1 (restart from A's level-1 code) on the full batch: per puzzle solve_A and solve_B1."""
    n, chunk, A, prefix = len(puzzles), ctx["chunk"], ctx["A"], ctx["prefix"]
    B1 = _chunked(lambda s: continue_generation(m, prefix[s], A[s, :1], 1), n, chunk)
    _, met_B1 = _eval(puzzles, solutions, B1, m)
    return [{"puzzle_id": puzzle_ids[i], "solve_A": int(ctx["met_A"][i].solve), "solve_B1": int(met_B1[i].solve)}
            for i in range(n)]


@torch.no_grad()
def level1_enumeration(m: NcmModel, puzzles: np.ndarray, solutions: np.ndarray, puzzle_ids: list[str],
                       A: torch.Tensor, freqs1: torch.Tensor, chunk: int = 50,
                       ctx: dict | None = None) -> list[dict]:
    """Level-1 enumeration on the full ordered batch (plan §2.2 item 5; v3.7 Final ASTRA-1): for
    every value v = 0..15, C = A with every row's level-1 code set to v; C and D run on all n rows
    in the original order with A's chunking. Rows whose own level-1 code is v are no-op rows
    (C equals A): kept with `noop` True and weight 0 under both policies as an in-batch sham
    check (`level1_noop_mismatch`); every estimate ignores them (`_active`)."""
    ctx = branch_context(m, puzzles, solutions, A, chunk) if ctx is None else ctx
    a1 = A[:, ctx["slices"][0]].squeeze(1)  # level 1 has a single code
    w = {p: level1_weights(a1, freqs1, p) for p in POLICIES}
    all_rows = torch.arange(len(puzzles))
    level1 = []
    for v in range(N_CODES):
        C = A.clone()
        C[:, 0] = v
        for i, rec in enumerate(compare(ctx, all_rows, C, 1)):
            noop = int(a1[i]) == v
            level1.append({"puzzle_id": puzzle_ids[i], "value": v, "noop": noop,
                           "w_frequency": 0.0 if noop else float(w["frequency"][i, v]),
                           "w_uniform": 0.0 if noop else float(w["uniform"][i, v]),
                           **rec})
    return level1


def level1_noop_mismatch(level1: list[dict], base: list[dict]) -> int:
    """No-op records that violate the in-batch sham: solve_C != solve_A, solve_D != solve_B1,
    tv != 0 or tv_empty != 0 (exact comparisons)."""
    b = {r["puzzle_id"]: r for r in base}
    return sum(1 for r in level1 if r.get("noop") and (
        r["solve_C"] != b[r["puzzle_id"]]["solve_A"] or r["solve_D"] != b[r["puzzle_id"]]["solve_B1"]
        or r["tv"] != 0 or r["tv_empty"] != 0))


def level1_noop_max_tv(level1: list[dict]) -> dict:
    """Largest `tv` and `tv_empty` over the no-op records (None if there are none); 0 when C equals A."""
    noop = [r for r in level1 if r.get("noop")]
    return {k: (max(r[k] for r in noop) if noop else None) for k in ("tv", "tv_empty")}


@torch.no_grad()
def run_pilot2(m: NcmModel, puzzles: np.ndarray, solutions: np.ndarray, puzzle_ids: list[str],
               chunk: int = 50, frozen_freqs: dict[int, np.ndarray] | None = None) -> dict:
    """`frozen_freqs` (optional): per-level code frequencies used for the level-1 weights and
    the level 2/6/11 frequency-policy draws instead of the input's own (`pilot_freqs`);
    the output records `freq_source` ("input" or "frozen"). Level 1 runs on the full ordered
    batch (`level1_enumeration`); `level1_noop_mismatch` counts in-batch sham violations."""
    n = len(puzzles)
    A = clean_codes(m, puzzles, chunk)
    ctx = branch_context(m, puzzles, solutions, A, chunk)
    slices, prefix, met_A = ctx["slices"], ctx["prefix"], ctx["met_A"]
    level_freqs, freq_source = pilot_freqs(A, m.levels, frozen_freqs)
    freqs1 = level_freqs[1]

    base = baseline_b1(m, puzzles, solutions, puzzle_ids, ctx)
    level1 = level1_enumeration(m, puzzles, solutions, puzzle_ids, A, freqs1, chunk, ctx)

    records = []
    all_rows = torch.arange(n)
    for level in LEVELS_P2:
        sl, end = slices[level - 1], slices[level - 1].stop
        B = _chunked(lambda s: continue_generation(m, prefix[s], A[s, :end], level), n, chunk)
        _, met_B = _eval(puzzles, solutions, B, m)
        freqs = level_freqs[level]
        for policy in POLICIES:
            for dose in dose_grid(sl.stop - sl.start, DOSE_FRACTIONS_V36):
                for seed in SEEDS_P2:
                    gen = torch.Generator().manual_seed(run_seed(level, policy, dose, seed))
                    new_level, eligible = perturb_level(A[:, sl], dose, policy, freqs, gen)
                    C = A.clone()
                    C[:, sl] = new_level
                    for i, rec in enumerate(compare(ctx, all_rows, C, level)):
                        records.append({"puzzle_id": puzzle_ids[i], "level": level, "policy": policy,
                                        "dose": dose, "seed": seed, "eligible": bool(eligible[i]),
                                        "solve_A": int(met_A[i].solve), "solve_B": int(met_B[i].solve), **rec})

    return {"freqs_level1": freqs1.tolist(), "freq_source": freq_source, "base": base, "level1": level1,
            "level1_noop_mismatch": level1_noop_mismatch(level1, base),
            "level1_noop_max_tv": level1_noop_max_tv(level1), "records": records}


# ---------------------------------------------------------------- statistics (plan v3.6 §7.2, §11.2)

def _active(level1: list[dict]) -> list[dict]:
    """Level-1 records without the no-op rows (`noop` True: C equals A, the in-batch sham)."""
    return [r for r in level1 if not r.get("noop", False)]


def _level1_terms(out: dict, policy: str) -> dict[str, tuple[float, float]]:
    """Per eligible puzzle: (sum_v w (D - A), sum_v w (D - C)) at level 1; ineligible = weights sum
    to 0. No-op rows are ignored."""
    A = {b["puzzle_id"]: b["solve_A"] for b in out["base"]}
    acc = defaultdict(lambda: [0.0, 0.0, 0.0])
    for r in _active(out["level1"]):
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
    n, nz = len(v), int(np.sum(np.abs(v) > 1e-12))  # weights summing to 1 +- eps leave ~1e-16 noise
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
    """Per eligible puzzle: {key: sum_v w d / sum_v w} over non-no-op records with a non-None value
    (plan §7.2 weights)."""
    acc = defaultdict(lambda: [0.0, 0.0])
    for r in _active(level1):
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
        for r in _active(out["level1"]):
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

    # Instrumentation check: the sham B must reproduce A; otherwise theta_comp can leave [-1, 1]
    sham = {
        "level1_B1": sum(b["solve_B1"] != b["solve_A"] for b in out["base"]),
        "levels_B": {str(level): len({r["puzzle_id"] for r in out["records"]
                                      if r["level"] == level and r["solve_B"] != r["solve_A"]})
                     for level in sorted({r["level"] for r in out["records"]})},
    }

    return {
        "non_confirmatory": True,
        "sham_mismatch": sham,
        # in-batch level-1 sham (no-op rows); None for outputs from before the full-batch enumeration
        "level1_noop_mismatch": out.get("level1_noop_mismatch"),
        "level1_noop_max_tv": out.get("level1_noop_max_tv"),
        "freqs_level1": out["freqs_level1"],
        "contrasts": contrasts,
        "equivalence_tost": bool(-TOST_MARGIN < tost["ci"][0] and tost["ci"][1] < TOST_MARGIN),
        "configurations": configurations,
        "level1": level1,
        "auc": {f"{a}-{b}": auc_pair(dose_nodes(out, a), dose_nodes(out, b)) for a, b in ((6, 11), (2, 11))},
    }
