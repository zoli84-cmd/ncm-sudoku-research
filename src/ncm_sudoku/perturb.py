"""Discrete code perturbations for E2 (plan §7.2-§7.3, D38)."""

import hashlib
import math

import torch

from ncm_sudoku.model import level_slices

N_CODES = 16

DOSE_FRACTIONS_V35 = (0.05, 0.15, 0.30)
DOSE_FRACTIONS_V36 = (0.05, 0.15, 0.30, 0.60, 1.0)


def dose_grid(n_level: int, fractions=DOSE_FRACTIONS_V35) -> list[int]:
    """Distinct values of {1, ceil(f*n) for f in fractions} within 1..n."""
    vals = {1}
    for f in fractions:
        vals.add(math.ceil(f * n_level))
    return sorted(v for v in vals if 1 <= v <= n_level)


def run_seed(level: int, policy: str, dose: int, seed: int) -> int:
    """SHA-256 of f"{level}|{policy}|{dose}|{seed}", first 8 bytes as little-endian int, shifted right by 1."""
    msg = f"{level}|{policy}|{dose}|{seed}"
    hash_bytes = hashlib.sha256(msg.encode()).digest()[:8]
    # Convert first 8 bytes to little-endian int
    val = int.from_bytes(hash_bytes, byteorder='little')
    return val >> 1


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


def level1_weights(a: torch.Tensor, freqs: torch.Tensor, policy: str) -> torch.Tensor:
    """Weights for perturbing level-1 codes, or all zeros if ineligible.

    For frequency policy:
    - If a[i] == 0: remove freqs[0] mass and renormalize; ineligible if remaining sum is 0.
    - If a[i] > 0: remove freqs[a[i]] mass and renormalize; ineligible if remaining sum is 0.

    For uniform policy:
    - If a[i] == 0: uniform over indices 1..15 (skip 0).
    - If a[i] > 0: uniform over all indices except a[i].
    """
    B = a.shape[0]
    weights = torch.zeros(B, N_CODES, dtype=torch.double)

    for b in range(B):
        orig_idx = int(a[b])

        if policy == "frequency":
            w = freqs.clone().double()
            w[orig_idx] = 0.0
            if w.sum() > 0:
                weights[b] = w / w.sum()
            # else: all zeros (ineligible)
        elif policy == "uniform":
            w = torch.ones(N_CODES, dtype=torch.double)
            w[orig_idx] = 0.0
            weights[b] = w / w.sum()  # Always eligible: 15 non-zero entries
        else:
            raise ValueError(f"Unknown policy: {policy}")

    return weights
