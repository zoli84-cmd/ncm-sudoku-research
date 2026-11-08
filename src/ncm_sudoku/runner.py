"""Upstream-mirroring generation and decoding (third_party/ncm scripts/eval_shard.py `run`).

Generation settings follow config/eval/sudoku-hard.yaml: temperature 0 (argmax),
top_k 0, top_p 1.0, cfg_scale 0. Decoding: idx_to_zhats -> last level -> decoder ->
argmax (no frequency penalty in this config).
"""

import numpy as np
import torch

from ncm_sudoku.grid import encode_puzzle_tokens, encode_solution_tokens
from ncm_sudoku.model import NcmModel


def puzzle_tensor(puzzles: np.ndarray) -> torch.Tensor:
    return torch.tensor(np.array([encode_puzzle_tokens(p) for p in puzzles]), dtype=torch.long)


@torch.no_grad()
def generate_codes(m: NcmModel, puzzles: np.ndarray, batch_size: int = 32) -> torch.Tensor:
    x = puzzle_tensor(puzzles)
    out = [
        m.net.generate(None, x[i : i + batch_size], temperature=0.0, top_k=0, top_p=1.0, cfg_scale=0.0)
        for i in range(0, len(x), batch_size)
    ]
    return torch.cat(out)


@torch.no_grad()
def decode_codes(m: NcmModel, codes: torch.Tensor) -> torch.Tensor:
    _, z_levels = m.vqvae.vq.idx_to_zhats(codes, return_zlevels=True)
    return m.vqvae.decoder(z_levels[-1]).argmax(-1)


@torch.no_grad()
def teacher_codes(m: NcmModel, solutions: np.ndarray) -> torch.Tensor:
    x = torch.tensor(np.array([encode_solution_tokens(s) for s in solutions]), dtype=torch.long)
    return m.vqvae.encode(x)
