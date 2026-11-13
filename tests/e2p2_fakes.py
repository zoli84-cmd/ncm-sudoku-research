"""Deterministic fakes for the model pieces `ncm_sudoku.e2p2` uses (fast E2 tests)."""

from types import SimpleNamespace

import numpy as np
import torch

from ncm_sudoku import e2p2
from ncm_sudoku.grid import CELL_TOKEN_INDICES


N_TOY = 5
TOY_LEVELS = (1, 2)  # 3 codes per row: level 1 = code 0, level 2 = codes 1-2
N_TOKENS = 89
EMBED_DIM = 4


def toy_puzzles():
    pz = np.zeros((N_TOY, 81), dtype=np.int8)
    pz[:, 0] = np.arange(1, N_TOY + 1)        # row identity, visible in the puzzle prefix
    pz[:, 1] = [3, 3, 5, 3, 7]                 # level-1 code of A (3 repeats: several no-op rows)
    pz[:, 2] = [1, 2, 1, 4, 2]
    pz[:, 3] = [0, 1, 1, 0, 1]
    return pz


def toy_model(embeddings: list[torch.Tensor] | None = None):
    """Fake model: `levels` plus one [16, EMBED_DIM] embedding table per toy level
    (`m.vqvae.vq.embeddings[i].weight`), so `damage.codebook_rms` and the replacement norm run on it."""
    if embeddings is None:
        g = torch.Generator().manual_seed(0)
        embeddings = [torch.randn(16, EMBED_DIM, generator=g) for _ in TOY_LEVELS]
    tables = [SimpleNamespace(weight=w) for w in embeddings]
    return SimpleNamespace(levels=TOY_LEVELS, vqvae=SimpleNamespace(vq=SimpleNamespace(embeddings=tables)))


def _tokens(codes: torch.Tensor) -> torch.Tensor:
    """[rows, 89] tokens with the toy codes at the first cells' output positions."""
    tok = torch.zeros(len(codes), N_TOKENS, dtype=torch.long)
    tok[:, torch.as_tensor(CELL_TOKEN_INDICES[: codes.shape[1]])] = codes.long()
    return tok


def install_fakes(monkeypatch, calls, tv_value=None, flip_noop_solve=False, exact_restart=False):
    """Deterministic fakes for the model pieces e2p2 uses; solve = first code is even.

    The default restart appends the suffix [1, 1]; with `exact_restart` it replays A's suffix
    (row identity from the prefix), so B1 and B equal A exactly. `_eval_tokens` records
    ("eval", rows, decode_chunk)."""
    A_toy = torch.as_tensor(toy_puzzles()[:, 1:4].astype(np.int64))

    def gen(m, puzzles, batch_size=32):
        return torch.as_tensor(np.asarray(puzzles)[:, 1:4].astype(np.int64))

    def cont(m, prefix, codes_prefix, level):
        calls.append(("D", level, prefix[:, 1].tolist(), codes_prefix[:, 0].tolist()))
        k, n_given = len(prefix), codes_prefix.shape[1]
        if exact_restart:
            suffix = A_toy[prefix[:, 1] - 1, n_given:]
        else:
            suffix = torch.as_tensor(np.tile([[1, 1]], (k, 1)), dtype=torch.long)[:, : 3 - n_given]
        return torch.cat([codes_prefix, suffix], dim=1)

    flipped = []

    def ev(puzzles, solutions, codes, m, decode_chunk=None):
        calls.append(("eval", len(codes), decode_chunk))
        solve = [int(int(c[0]) % 2 == 0) for c in codes]
        # first full-batch eval with every level-1 code 3 is branch C of value 3 (D comes next)
        if flip_noop_solve and not flipped and len(codes) == N_TOY and bool((codes[:, 0] == 3).all()):
            flipped.append(True)
            solve[0] = 1 - solve[0]
        return (_tokens(codes), [SimpleNamespace(cells=None)] * len(codes),
                [SimpleNamespace(solve=s, well_formed=True) for s in solve])

    def tv(a, b, mask=None):
        d = (a - b).abs().sum(dim=1)
        return d if tv_value is None else torch.full_like(d, tv_value)

    def states(m, codes, upto=None):
        """One state per toy level: the codes of levels 1..k (later positions 0); the last is codes.float()."""
        out, end = [], 0
        for n in m.levels:
            end += n
            z = codes.float().clone()
            z[:, end:] = 0.0
            out.append(z)
        return out

    def level_logits(m, prefix, given, level):
        n = m.levels[level - 1]
        base = torch.arange(16, dtype=torch.float32) * 0.1
        return base + 0.01 * prefix[:, 1, None, None].float() + 0.001 * torch.arange(n)[None, :, None]

    monkeypatch.setattr(e2p2, "generate_codes", gen)
    monkeypatch.setattr(e2p2, "continue_generation", cont)
    monkeypatch.setattr(e2p2, "_eval_tokens", ev)
    monkeypatch.setattr(e2p2, "cumulative_states", states)
    monkeypatch.setattr(e2p2, "decode_state_logits", lambda m, z: z)
    monkeypatch.setattr(e2p2, "decode_state", lambda m, z: _tokens(z.round().long()))
    monkeypatch.setattr(e2p2, "level_logits", level_logits)
    monkeypatch.setattr(e2p2, "tv_damage", tv)
    monkeypatch.setattr(e2p2, "latent_distance", lambda a, b: (a - b).abs().sum(dim=1))
    monkeypatch.setattr(e2p2, "requantize", lambda m, x, level: (None, torch.zeros(len(x))))
    monkeypatch.setattr(e2p2, "codebook_rms", lambda m, level, a, b: torch.zeros(len(a)))
    monkeypatch.setattr(e2p2, "cell_hamming", lambda a, b, cells=None: 0)
    monkeypatch.setattr(e2p2, "LEVELS_P2", (2,))
    monkeypatch.setattr(e2p2, "SEEDS_P2", (0,))
