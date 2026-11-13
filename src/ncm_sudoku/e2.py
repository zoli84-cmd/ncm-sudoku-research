"""E2 pilot: four-branch level sensitivity, estimators, summary (plan §7, §11; D38, D39).

Non-confirmatory. Branches per configuration share one batch tensor (D20).
"""

from collections import defaultdict

import numpy as np
import torch

from ncm_sudoku.intervene import continue_generation
from ncm_sudoku.model import NcmModel, level_slices
from ncm_sudoku.perturb import code_frequencies, dose_grid, perturb_level
from ncm_sudoku.runner import decode_codes, generate_codes, puzzle_tensor
from ncm_sudoku.validate import cell_hamming, evaluate, parse_output_tokens

PILOT_LEVELS = (1, 2, 6, 11)
POLICIES = ("frequency", "uniform")
N_SEEDS = 3


def _eval_tokens(puzzles, solutions, codes, m, decode_chunk: int | None = None):
    """Decoded tokens [rows, 89], parsed outputs and metrics of `codes`. With `decode_chunk`
    None the whole tensor is decoded in one `decode_codes` call; with an int, in row blocks of
    that size (WP2, spec ambiguity 11)."""
    if decode_chunk is None:
        tokens = decode_codes(m, codes)
    else:
        tokens = _chunked(lambda s: decode_codes(m, codes[s]), len(codes), decode_chunk)
    parsed = [parse_output_tokens(t.tolist()) for t in tokens]
    return tokens, parsed, [evaluate(p, o, s) for p, o, s in zip(puzzles, parsed, solutions)]


def _eval(puzzles, solutions, codes, m, decode_chunk: int | None = None):
    return _eval_tokens(puzzles, solutions, codes, m, decode_chunk)[1:]


def _chunked(fn, n, chunk):
    return torch.cat([fn(slice(i, min(i + chunk, n))) for i in range(0, n, chunk)])


@torch.no_grad()
def run_pilot(m: NcmModel, puzzles: np.ndarray, solutions: np.ndarray, puzzle_ids: list[str],
              chunk: int = 50) -> list[dict]:
    n = len(puzzles)
    prefix = puzzle_tensor(puzzles)
    slices = level_slices(m.levels)
    A = _chunked(lambda s: generate_codes(m, puzzles[s], batch_size=chunk), n, chunk)
    parsed_A, met_A = _eval(puzzles, solutions, A, m)
    freqs = code_frequencies(A, m.levels)
    records = []
    for level in PILOT_LEVELS:
        sl, end = slices[level - 1], slices[level - 1].stop
        B = _chunked(lambda s: continue_generation(m, prefix[s], A[s, :end], level), n, chunk)
        _, met_B = _eval(puzzles, solutions, B, m)
        for policy in POLICIES:
            for dose in dose_grid(sl.stop - sl.start):
                for seed in range(N_SEEDS):
                    gen = torch.Generator().manual_seed(
                        1000 * level + 100 * dose + 10 * seed + (0 if policy == "frequency" else 1))
                    new_level, eligible = perturb_level(A[:, sl], dose, policy, freqs[level - 1], gen)
                    C = A.clone()
                    C[:, sl] = new_level
                    D = _chunked(lambda s: continue_generation(m, prefix[s], C[s, :end], level), n, chunk)
                    parsed_C, met_C = _eval(puzzles, solutions, C, m)
                    _, met_D = _eval(puzzles, solutions, D, m)
                    changes = (D[:, end:] != A[:, end:]).sum(dim=1).tolist()
                    for i in range(n):
                        both_ok = met_C[i].well_formed and met_A[i].well_formed
                        records.append({
                            "puzzle_id": puzzle_ids[i], "level": level, "policy": policy, "dose": dose,
                            "seed": seed, "eligible": bool(eligible[i]),
                            "solve_A": int(met_A[i].solve), "solve_B": int(met_B[i].solve),
                            "solve_C": int(met_C[i].solve), "solve_D": int(met_D[i].solve),
                            "well_formed_C": bool(met_C[i].well_formed), "well_formed_D": bool(met_D[i].well_formed),
                            "hamming_CA": cell_hamming(parsed_C[i].cells, parsed_A[i].cells) if both_ok else None,
                            "downstream_changes_D": int(changes[i]),
                        })
    return records


def _per_puzzle(records, level, policy="frequency", dose=1):
    """puzzle_id -> list of records for this configuration (all seeds), only if eligible in every seed."""
    groups = defaultdict(list)
    for r in records:
        if r["level"] == level and r["policy"] == policy and r["dose"] == dose:
            groups[r["puzzle_id"]].append(r)
    return {pid: rs for pid, rs in groups.items() if all(r["eligible"] for r in rs)}


def theta2(records) -> float:
    """E[(Y_D2 - Y_A) - (Y_D11 - Y_A)]: seeds averaged within puzzle, then puzzles (§7.2)."""
    g2, g11 = _per_puzzle(records, 2), _per_puzzle(records, 11)
    common = sorted(set(g2) & set(g11))
    vals = [np.mean([r["solve_D"] - r["solve_A"] for r in g2[p]]) - np.mean([r["solve_D"] - r["solve_A"] for r in g11[p]])
            for p in common]
    return float(np.mean(vals)) if vals else float("nan")


def theta_comp(records, level: int = 2) -> float:
    """E[(Y_D - Y_C) - (Y_B - Y_A)] at `level`: seeds within puzzle, then puzzles (§7.1)."""
    g = _per_puzzle(records, level)
    vals = [np.mean([(r["solve_D"] - r["solve_C"]) - (r["solve_B"] - r["solve_A"]) for r in rs]) for rs in g.values()]
    return float(np.mean(vals)) if vals else float("nan")


def cluster_bootstrap(records, estimator, n_boot: int = 2000, seed: int = 0) -> tuple[float, float]:
    by_puzzle = defaultdict(list)
    for r in records:
        by_puzzle[r["puzzle_id"]].append(r)
    ids = sorted(by_puzzle)
    rng = np.random.default_rng(seed)
    stats = []
    for _ in range(n_boot):
        sample = []
        for k, pid in enumerate(rng.choice(ids, size=len(ids), replace=True)):
            sample += [{**r, "puzzle_id": f"{pid}#{k}"} for r in by_puzzle[pid]]
        stats.append(estimator(sample))
    lo, hi = np.nanpercentile(stats, [2.5, 97.5])
    return float(lo), float(hi)


def dose_overlap(ranges: dict):
    """Overlap of median C–A damage ranges at levels 2 and 11; "degenerate" when all medians are zero."""
    if 2 not in ranges or 11 not in ranges:
        return None
    if ranges[2] == ranges[11] == (0.0, 0.0):
        return "degenerate"
    return ranges[2][0] <= ranges[11][1] and ranges[11][0] <= ranges[2][1]


def summarize(records, n_boot: int = 2000) -> dict:
    by_config = {}
    configs = sorted({(r["level"], r["policy"], r["dose"]) for r in records})
    medians = defaultdict(list)
    for level, policy, dose in configs:
        rs = [r for r in records if (r["level"], r["policy"], r["dose"]) == (level, policy, dose)]
        el = [r for r in rs if r["eligible"]]
        ham = [r["hamming_CA"] for r in el if r["hamming_CA"] is not None]
        disc = defaultdict(lambda: {"b": 0, "c": 0})
        for r in el:
            disc[r["seed"]]["b"] += int(r["solve_A"] == 1 and r["solve_D"] == 0)
            disc[r["seed"]]["c"] += int(r["solve_A"] == 0 and r["solve_D"] == 1)
        q = np.quantile(ham, [0, 0.25, 0.5, 0.75, 1]).tolist() if ham else None
        if q and policy == "frequency":
            medians[level].append(q[2])
        by_config[f"L{level}-{policy}-d{dose}"] = {
            "n_records": len(rs),
            "exclusion_share": 1 - len(el) / len(rs),
            "solve_mean": {k: float(np.mean([r[f"solve_{k}"] for r in el])) if el else None for k in "ABCD"},
            "format_error_share": {"C": float(np.mean([not r["well_formed_C"] for r in el])) if el else None,
                                   "D": float(np.mean([not r["well_formed_D"] for r in el])) if el else None},
            "discordance_by_seed": dict(disc),
            "hamming_CA_quantiles": q,
            "mean_downstream_changes_D": float(np.mean([r["downstream_changes_D"] for r in el])) if el else None,
        }
    ranges = {lv: (min(v), max(v)) for lv, v in medians.items()}
    overlap = dose_overlap(ranges)
    t2, tc = theta2(records), theta_comp(records, 2)
    return {
        "non_confirmatory": True,
        "theta2": {"estimate": t2, "ci95": cluster_bootstrap(records, theta2, n_boot),
                   "n_puzzles": len(set(_per_puzzle(records, 2)) & set(_per_puzzle(records, 11)))},
        "theta_comp_level2": {"estimate": tc, "ci95": cluster_bootstrap(records, lambda r: theta_comp(r, 2), n_boot),
                              "n_puzzles": len(_per_puzzle(records, 2))},
        "by_config": by_config,
        "dose_overlap": {"median_hamming_range_by_level_frequency": ranges, "levels_2_11_overlap": overlap},
    }
