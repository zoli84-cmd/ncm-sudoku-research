"""Discrete code perturbations for E2 (plan §7.2-§7.3, D38)."""

import math

import torch

from ncm_sudoku.model import level_slices

N_CODES = 16


def dose_grid(n_level: int) -> list[int]:
    """Distinct values of {1, ceil(.05n), ceil(.15n), ceil(.30n)} within 1..n."""
    vals = {1, math.ceil(0.05 * n_level), math.ceil(0.15 * n_level), math.ceil(0.30 * n_level)}
    return sorted(v for v in vals if 1 <= v <= n_level)


def code_frequencies(codes: torch.Tensor, levels) -> list[torch.Tensor]:
    out = []
    for sl in level_slices(levels):
        counts = torch.bincount(codes[:, sl].reshape(-1), minlength=N_CODES).double()
        out.append((counts / counts.sum()).float())
    return out


def perturb_level(
    level_codes: torch.Tensor, dose: int, policy: str, freqs: torch.Tensor, gen: torch.Generator
) -> tuple[torch.Tensor, torch.Tensor]:
    """Replace `dose` uniformly chosen positions per row; the new value never equals the original.

    frequency: draw from `freqs` with the original value's mass removed; a row is
    ineligible (left unchanged) if any chosen position has no remaining mass.
    uniform: draw uniformly from the other 15 values.
    """
    if policy not in ("frequency", "uniform"):
        raise ValueError(policy)
    B, n = level_codes.shape
    if not 1 <= dose <= n:
        raise ValueError("dose must be in 1..n_level")
    new = level_codes.clone()
    eligible = torch.ones(B, dtype=torch.bool)
    for b in range(B):
        positions = torch.randperm(n, generator=gen)[:dose]
        values = []
        for pos in positions.tolist():
            orig = int(level_codes[b, pos])
            weights = freqs.clone().double() if policy == "frequency" else torch.ones(N_CODES, dtype=torch.double)
            weights[orig] = 0.0
            if weights.sum() <= 0:
                eligible[b] = False
                break
            values.append((pos, int(torch.multinomial(weights, 1, generator=gen))))
        if eligible[b]:
            for pos, v in values:
                new[b, pos] = v
    return new, eligible
