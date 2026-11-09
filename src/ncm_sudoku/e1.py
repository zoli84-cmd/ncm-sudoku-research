"""E1: tokenizer reconstruction vs generator output, with per-level decodings (plan §6, D37)."""

import numpy as np
import torch

from ncm_sudoku.grid import encode_solution_tokens
from ncm_sudoku.model import NcmModel, level_slices
from ncm_sudoku.runner import decode_codes, generate_codes, teacher_codes
from ncm_sudoku.states import cumulative_states, decode_state
from ncm_sudoku.validate import cell_hamming, evaluate, parse_output_tokens

_OWN_FIELDS = ("well_formed", "solve", "valid_grid", "all_clues_preserved", "cell_acc_all", "cell_acc_empty")


def _metrics(puzzles, tokens, solutions):
    return [evaluate(p, parse_output_tokens(t.tolist()), s) for p, t, s in zip(puzzles, tokens, solutions)]


@torch.no_grad()
def e1_summary(m: NcmModel, puzzles: np.ndarray, solutions: np.ndarray, batch_size: int = 128) -> dict:
    n_levels = len(m.levels)
    slices = level_slices(m.levels)
    agree = [[] for _ in range(n_levels)]
    level_metrics = [[] for _ in range(n_levels)]
    gen_metrics, teacher_exact, teacher_cell, tok_ham, cell_ham = [], [], [], [], []
    for i in range(0, len(puzzles), batch_size):
        p, s = puzzles[i : i + batch_size], solutions[i : i + batch_size]
        gen = generate_codes(m, p, batch_size=batch_size)
        tch = teacher_codes(m, s)
        gen_tok, tch_tok = decode_codes(m, gen), decode_codes(m, tch)
        ref_tok = torch.tensor(np.array([encode_solution_tokens(x) for x in s]))
        teacher_exact += (tch_tok == ref_tok).all(dim=1).tolist()
        teacher_cell += [e.cell_acc_all for e in _metrics(p, tch_tok, s)]
        gen_metrics += _metrics(p, gen_tok, s)
        tok_ham += (gen_tok != tch_tok).float().mean(dim=1).tolist()
        cell_ham += [cell_hamming(parse_output_tokens(a.tolist()).cells, parse_output_tokens(b.tolist()).cells)
                     for a, b in zip(gen_tok, tch_tok)]
        states = cumulative_states(m, gen)
        for lv in range(n_levels):
            sl = slices[lv]
            agree[lv] += (gen[:, sl] == tch[:, sl]).float().mean(dim=1).tolist()
            level_metrics[lv] += _metrics(p, decode_state(m, states[lv]), s)
    per_level = []
    for lv in range(n_levels):
        ms = level_metrics[lv]
        per_level.append({
            "level": lv + 1,
            "code_agreement": float(np.mean(agree[lv])),
            "cell_acc_all": float(np.mean([x.cell_acc_all for x in ms])),
            "cell_acc_empty": float(np.mean([x.cell_acc_empty for x in ms])),
            "solve": float(np.mean([x.solve for x in ms])),
            "format_error": float(np.mean([not x.well_formed for x in ms])),
        })
    return {
        "n": len(puzzles),
        "teacher": {"exact_share": float(np.mean(teacher_exact)), "cell_acc_all": float(np.mean(teacher_cell))},
        "generated": {f: float(np.mean([float(getattr(x, f)) for x in gen_metrics])) for f in _OWN_FIELDS},
        "per_level": per_level,
        "hamming": {"token_mean": float(np.mean(tok_ham)), "cell_mean": float(np.mean(cell_ham))},
    }
