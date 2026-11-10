"""Damage and diagnostic measures for comparing a perturbed branch against the
clean branch (plan E2, global-constraints.md: TV damage definition; and the
brief's `requantize`, mirroring upstream `quant.py` `z_to_idx`, lines 573-625).
"""

import torch

from ncm_sudoku.grid import CELL_TOKEN_INDICES

_CELL_IDX = torch.as_tensor(CELL_TOKEN_INDICES)


@torch.no_grad()
def tv_damage(
    logits_c: torch.Tensor,
    logits_a: torch.Tensor,
    cell_mask: torch.Tensor | None = None,
) -> torch.Tensor:
    """Mean total-variation distance (T=1 softmax) over the 81 cell positions,
    or over the cells selected by `cell_mask` ([B, 81] bool).
    """
    pc = torch.softmax(logits_c[:, _CELL_IDX, :], dim=-1)
    pa = torch.softmax(logits_a[:, _CELL_IDX, :], dim=-1)
    tv = 0.5 * (pc - pa).abs().sum(dim=-1)  # [B, 81]
    if cell_mask is None:
        return tv.mean(dim=-1)
    mask = cell_mask.to(tv.dtype)
    count = mask.sum(dim=-1).clamp(min=1)
    return (tv * mask).sum(dim=-1) / count


def latent_distance(z_c: torch.Tensor, z_a: torch.Tensor) -> torch.Tensor:
    """‖z_c − z_a‖₂ / ‖z_a‖₂ per batch row."""
    diff = (z_c - z_a).flatten(1).norm(dim=-1)
    denom = z_a.flatten(1).norm(dim=-1)
    return diff / denom


def codebook_rms(m, level: int, old: torch.Tensor, new: torch.Tensor) -> torch.Tensor:
    """RMS over changed positions of ‖E[new] − E[old]‖₂ in `level`'s (1-based)
    embedding table; 0.0 per row where nothing changed.
    """
    E = m.vqvae.vq.embeddings[level - 1].weight
    diff_norm = (E[new] - E[old]).norm(dim=-1)  # [B, n]
    changed = old != new
    counts = changed.sum(dim=-1).clamp(min=1)
    rms = torch.sqrt((diff_norm * changed).pow(2).sum(dim=-1) / counts)
    return torch.where(changed.any(dim=-1), rms, torch.zeros_like(rms))


@torch.no_grad()
def requantize(m, residual: torch.Tensor, from_level: int) -> tuple[torch.Tensor, torch.Tensor]:
    """Quantize `residual` with levels `from_level..len(m.levels)` (1-based),
    mirroring the argmin path of upstream `z_to_idx`
    (third_party/ncm/models/quant.py:573-625) started at `from_level`.

    Returns the concatenated codes for the remaining levels and, per row, the
    ratio ‖remaining residual‖ / ‖residual‖ (0.0 when ‖residual‖ = 0).
    """
    vq = m.vqvae.vq
    levels = m.levels
    num_levels = len(levels)
    L = levels[-1]
    B, _, C = residual.shape

    z_rest = residual.clone()
    codes = []
    for i in range(from_level - 1, num_levels):
        emb_i = vq.embeddings[i]
        last = i == num_levels - 1

        flat_input = (vq._down_for_quant(z_rest, i, levels[i]) if not last else z_rest).reshape(-1, C)
        distances = vq._distances(flat_input, emb_i.weight)
        indices = torch.argmin(distances, dim=1).view(B, levels[i])
        codes.append(indices)

        quantized = vq._up_to_full(emb_i(indices), i, L) if not last else emb_i(indices)
        quantized = vq._apply_quant_resi(quantized, i)
        z_rest = z_rest - quantized

    codes = torch.cat(codes, dim=-1)
    residual_norm = residual.flatten(1).norm(dim=-1)
    rest_norm = z_rest.flatten(1).norm(dim=-1)
    ratio = torch.where(residual_norm == 0, torch.zeros_like(residual_norm), rest_norm / residual_norm)
    return codes, ratio
