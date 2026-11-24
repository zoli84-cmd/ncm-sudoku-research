"""E5 NCM activation extraction for the counterfactual pairs.

`generate_capture_pass` runs the upstream greedy generation (as `runner.generate_codes`)
with forward hooks that keep the residual stream of one generation pass only: the
input of block 1 (layer 0) and the output of every block (layers 1..8). Pass p
generates plan level p + 1; pass 6 generates level 7 from the downsampled cumulative
state Z<=6, so its prefix positions are the puzzle representation the level-7 queries
read. The hooks only copy tensors; the generated codes are unchanged
(`tests/test_e5extract.py`).
"""

import numpy as np
import torch

from ncm_sudoku.grid import CELL_TOKEN_INDICES
from ncm_sudoku.model import NcmModel
from ncm_sudoku.runner import decode_codes, puzzle_tensor, teacher_codes
from ncm_sudoku.states import cell_states, cumulative_states

PREFIX_CELLS = 1 + CELL_TOKEN_INDICES  # prefix = [BOS] + 89 row tokens + [BOS]
LEVEL7_PASS = 6


@torch.no_grad()
def generate_capture_pass(net, x: torch.Tensor, pass_index: int = LEVEL7_PASS):
    """Returns (codes, layers): layers is a list of 9 tensors (B, P + L, d) for the pass."""
    count = {"pass": -1}
    layers: list[torch.Tensor] = []
    blocks = net.transformer.blocks

    def pre0(_mod, args, kwargs):
        count["pass"] += 1
        if count["pass"] == pass_index:
            layers.append(args[0].detach().clone())

    def post(_mod, _args, out):
        if count["pass"] == pass_index:
            layers.append(out.detach().clone())

    handles = [blocks[0].register_forward_pre_hook(pre0, with_kwargs=True)]
    handles += [b.register_forward_hook(post) for b in blocks]
    try:
        codes = net.generate(None, x, temperature=0.0, top_k=0, top_p=1.0, cfg_scale=0.0)
    finally:
        for h in handles:
            h.remove()
    if len(layers) != len(blocks) + 1:
        raise RuntimeError(f"pass {pass_index} not captured completely ({len(layers)} tensors)")
    return codes, layers


@torch.no_grad()
def extract_batch(m: NcmModel, puzzles: np.ndarray, solutions: np.ndarray) -> dict[str, np.ndarray]:
    """Per puzzle: prefix cell activations (9 layers x 81 x d, fp16), closing-BOS
    activations (9 x d, fp16), level-7 query activations (9 x L7 x d, fp16), generated
    Z<=6 cell states (81 x 256, fp32), teacher Z<=6 cell states (fp32), generated codes,
    and whether the decoded grid equals the solution."""
    net = m.net
    P = net.prefix_len
    codes, layers = generate_capture_pass(net, puzzle_tensor(puzzles))
    stack = torch.stack(layers, dim=1)  # (B, 9, P + L7, d)
    z6 = cell_states(cumulative_states(m, codes, upto=6)[5])
    z6_teacher = cell_states(cumulative_states(m, teacher_codes(m, solutions), upto=6)[5])
    decoded = decode_codes(m, codes)[:, torch.as_tensor(CELL_TOKEN_INDICES)].numpy()
    return {
        "prefix_cells": stack[:, :, torch.as_tensor(PREFIX_CELLS)].half().numpy(),
        "prefix_bos": stack[:, :, P - 1].half().numpy(),
        "level7_queries": stack[:, :, P:].half().numpy(),
        "z6": z6.float().numpy(),
        "z6_teacher": z6_teacher.float().numpy(),
        "codes": codes.numpy().astype(np.int8),
        "solved": (decoded == np.asarray(solutions)).all(axis=1),
    }
