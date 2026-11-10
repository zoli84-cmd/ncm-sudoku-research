"""E2 pilot 2: level-1 enumeration, v3.6 dose grid, damage measures (plan v3.6 §7).

Non-confirmatory. Branches: A clean, B sham restart from level l with A's codes,
C level l perturbed with A's suffix replayed, D level l perturbed with the suffix
regenerated. Damage measures compare C against A on the final cumulative state.
"""

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
