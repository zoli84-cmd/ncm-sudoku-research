"""Deterministic fakes for the model pieces `ncm_sudoku.e2p2` uses (fast E2 tests)."""

from types import SimpleNamespace

import numpy as np
import torch

from ncm_sudoku import e2p2


N_TOY = 5
TOY_LEVELS = (1, 2)  # 3 codes per row: level 1 = code 0, level 2 = codes 1-2


def toy_puzzles():
    pz = np.zeros((N_TOY, 81), dtype=np.int8)
    pz[:, 0] = np.arange(1, N_TOY + 1)        # row identity, visible in the puzzle prefix
    pz[:, 1] = [3, 3, 5, 3, 7]                 # level-1 code of A (3 repeats: several no-op rows)
    pz[:, 2] = [1, 2, 1, 4, 2]
    pz[:, 3] = [0, 1, 1, 0, 1]
    return pz


def install_fakes(monkeypatch, calls, tv_value=None, flip_noop_solve=False):
    """Deterministic fakes for the model pieces e2p2 uses; solve = first code is even."""
    def gen(m, puzzles, batch_size=32):
        return torch.as_tensor(np.asarray(puzzles)[:, 1:4].astype(np.int64))

    def cont(m, prefix, codes_prefix, level):
        calls.append(("D", level, prefix[:, 1].tolist(), codes_prefix[:, 0].tolist()))
        k = len(prefix)
        suffix = torch.as_tensor(np.tile([[1, 1]], (k, 1)), dtype=torch.long)[:, : 3 - codes_prefix.shape[1]]
        return torch.cat([codes_prefix, suffix], dim=1)

    flipped = []

    def ev(puzzles, solutions, codes, m):
        calls.append(("eval", len(codes)))
        solve = [int(int(c[0]) % 2 == 0) for c in codes]
        # first full-batch eval with every level-1 code 3 is branch C of value 3 (D comes next)
        if flip_noop_solve and not flipped and len(codes) == N_TOY and bool((codes[:, 0] == 3).all()):
            flipped.append(True)
            solve[0] = 1 - solve[0]
        return ([SimpleNamespace(cells=None)] * len(codes),
                [SimpleNamespace(solve=s, well_formed=True) for s in solve])

    def tv(a, b, mask=None):
        d = (a - b).abs().sum(dim=1)
        return d if tv_value is None else torch.full_like(d, tv_value)

    monkeypatch.setattr(e2p2, "generate_codes", gen)
    monkeypatch.setattr(e2p2, "continue_generation", cont)
    monkeypatch.setattr(e2p2, "_eval", ev)
    monkeypatch.setattr(e2p2, "cumulative_states", lambda m, codes, upto=None: [codes.float(), codes.float()])
    monkeypatch.setattr(e2p2, "decode_state_logits", lambda m, z: z)
    monkeypatch.setattr(e2p2, "tv_damage", tv)
    monkeypatch.setattr(e2p2, "latent_distance", lambda a, b: (a - b).abs().sum(dim=1))
    monkeypatch.setattr(e2p2, "requantize", lambda m, x, level: (None, torch.zeros(len(x))))
    monkeypatch.setattr(e2p2, "codebook_rms", lambda m, level, a, b: torch.zeros(len(a)))
    monkeypatch.setattr(e2p2, "cell_hamming", lambda a, b, cells=None: 0)
    monkeypatch.setattr(e2p2, "LEVELS_P2", (2,))
    monkeypatch.setattr(e2p2, "SEEDS_P2", (0,))
