"""Full-length cumulative latent states Z_{<=l} (plan §2.2 items 6 and 7, D22).

Upstream idx_to_zhats appends one in-place tensor per level, so all returned
entries alias the final state. This loop mirrors its arithmetic (embedding lookup,
_up_to_full for levels < 12, _apply_quant_resi, accumulate) but creates a new
tensor at every level.
"""

import torch

from ncm_sudoku.grid import CELL_TOKEN_INDICES
from ncm_sudoku.model import NcmModel


@torch.no_grad()
def cumulative_states(m: NcmModel, codes: torch.Tensor, upto: int = 12) -> list[torch.Tensor]:
    vq = m.vqvae.vq
    levels = m.levels
    assert codes.shape[1] >= sum(levels[:upto]), "codes do not cover the requested levels"
    z = torch.zeros(codes.shape[0], levels[-1], m.vqvae.embed_dim, device=codes.device)
    states, start = [], 0
    for i in range(upto):
        emb = vq.embeddings[i](codes[:, start : start + levels[i]])
        zq = vq._up_to_full(emb, i, levels[-1]) if i != len(levels) - 1 else emb
        z = z + vq._apply_quant_resi(zq, i)
        states.append(z.clone())
        start += levels[i]
    return states


@torch.no_grad()
def decode_state_logits(m: NcmModel, z: torch.Tensor) -> torch.Tensor:
    return m.vqvae.decoder(z)


def decode_state(m: NcmModel, z: torch.Tensor) -> torch.Tensor:
    return decode_state_logits(m, z).argmax(-1)


def cell_states(z: torch.Tensor) -> torch.Tensor:
    return z[:, torch.as_tensor(CELL_TOKEN_INDICES), :]
