"""E1: tokenizer reconstruction vs generator output, with per-level decodings (plan §6, §10, D37).

`e1_records` is the per-puzzle breakdown used by the WP2 E1 runner; `e1_table` is the
statistics-free §10 aggregation of those records, agreeing with `e1_summary` on every
quantity the two share.
"""

from dataclasses import asdict

import numpy as np
import torch

from ncm_sudoku.grid import encode_solution_tokens
from ncm_sudoku.model import NcmModel, level_slices
from ncm_sudoku.official import decode_string
from ncm_sudoku.runner import decode_codes, generate_codes, teacher_codes
from ncm_sudoku.states import cumulative_states, decode_state
from ncm_sudoku.validate import cell_hamming, evaluate, parse_output_tokens

_OWN_FIELDS = ("well_formed", "solve", "valid_grid", "all_clues_preserved", "cell_acc_all", "cell_acc_empty")
_GENERATED_FIELDS = ("well_formed", "solve", "valid_grid", "all_clues_preserved", "clue_preservation",
                     "cell_acc_all", "cell_acc_empty", "reference_match", "format_error")


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


@torch.no_grad()
def e1_records(m: NcmModel, puzzles: np.ndarray, solutions: np.ndarray, ids: list[str],
               batch_size: int = 50) -> list[dict]:
    """Per-puzzle E1 breakdown (plan §6, §10): the official reproduction metric, every
    `Metrics` field of the generated output, token and cell Hamming against the teacher
    reconstruction, the teacher's own quality, and the per-level decodings. `cell_hamming` and
    `cell_hamming_empty` are both None when either the generated or the teacher output has a
    format error, since unparsed slots are not comparable."""
    n_levels = len(m.levels)
    slices = level_slices(m.levels)
    records = []
    for i in range(0, len(puzzles), batch_size):
        p, s, pid = puzzles[i : i + batch_size], solutions[i : i + batch_size], ids[i : i + batch_size]
        gen = generate_codes(m, p, batch_size=batch_size)
        tch = teacher_codes(m, s)
        gen_tok, tch_tok = decode_codes(m, gen), decode_codes(m, tch)
        gen_parsed = [parse_output_tokens(t.tolist()) for t in gen_tok]
        tch_parsed = [parse_output_tokens(t.tolist()) for t in tch_tok]
        gen_metrics = [evaluate(pp, o, ss) for pp, o, ss in zip(p, gen_parsed, s)]
        tch_metrics = [evaluate(pp, o, ss) for pp, o, ss in zip(p, tch_parsed, s)]
        states = cumulative_states(m, gen)
        level_agree, level_metrics = [], []
        for lv in range(n_levels):
            sl = slices[lv]
            level_agree.append((gen[:, sl] == tch[:, sl]).float().mean(dim=1).tolist())
            level_metrics.append([evaluate(pp, parse_output_tokens(t.tolist()), ss)
                                  for pp, t, ss in zip(p, decode_state(m, states[lv]), s)])
        for j in range(len(p)):
            gm, tm, gp, tp = gen_metrics[j], tch_metrics[j], gen_parsed[j], tch_parsed[j]
            if gp.format_error or tp.format_error:
                cell_ham_all = cell_ham_empty = None
            else:
                empty_idx = np.flatnonzero(p[j] == 0)
                cell_ham_all = cell_hamming(gp.cells, tp.cells)
                cell_ham_empty = cell_hamming(gp.cells, tp.cells, empty_idx) if empty_idx.size else 0.0
            records.append({
                "puzzle_id": pid[j],
                "official_exact": decode_string(gen_tok[j].tolist()) == decode_string(encode_solution_tokens(s[j])),
                **asdict(gm),
                "format_error": not gm.well_formed,
                "token_hamming": float((gen_tok[j] != tch_tok[j]).float().mean()),
                "cell_hamming": cell_ham_all,
                "cell_hamming_empty": cell_ham_empty,
                "teacher_exact": tch_tok[j].tolist() == encode_solution_tokens(s[j]),
                "teacher_cell_acc_all": tm.cell_acc_all,
                "teacher_solve": bool(tm.solve),
                "per_level": [{
                    "level": lv + 1,
                    "code_agreement": float(level_agree[lv][j]),
                    "solve": bool(level_metrics[lv][j].solve),
                    "cell_acc_all": level_metrics[lv][j].cell_acc_all,
                    "cell_acc_empty": level_metrics[lv][j].cell_acc_empty,
                    "format_error": not level_metrics[lv][j].well_formed,
                } for lv in range(n_levels)],
            })
    return records


def e1_table(records: list[dict]) -> dict:
    """Statistics-free §10 aggregation of `e1_records`: means and per-level breakdown that
    agree with `e1_summary` on every shared quantity, plus the official-exact share, the
    well-formed-only mean constraint violations, and the Hamming means over well-formed pairs."""
    n = len(records)
    generated = {f: float(np.mean([float(r[f]) for r in records])) for f in _GENERATED_FIELDS}
    violations = [r["constraint_violations"] for r in records if r["constraint_violations"] is not None]
    generated["mean_constraint_violations_well_formed"] = float(np.mean(violations)) if violations else None
    teacher = {"exact_share": float(np.mean([float(r["teacher_exact"]) for r in records])),
              "cell_acc_all": float(np.mean([r["teacher_cell_acc_all"] for r in records]))}
    n_levels = len(records[0]["per_level"]) if records else 0
    per_level = []
    for lv in range(n_levels):
        rows = [r["per_level"][lv] for r in records]
        per_level.append({
            "level": rows[0]["level"],
            "code_agreement": float(np.mean([x["code_agreement"] for x in rows])),
            "solve": float(np.mean([float(x["solve"]) for x in rows])),
            "cell_acc_all": float(np.mean([x["cell_acc_all"] for x in rows])),
            "cell_acc_empty": float(np.mean([x["cell_acc_empty"] for x in rows])),
            "format_error": float(np.mean([float(x["format_error"]) for x in rows])),
        })
    cell_all = [r["cell_hamming"] for r in records if r["cell_hamming"] is not None]
    cell_empty = [r["cell_hamming_empty"] for r in records if r["cell_hamming_empty"] is not None]
    hamming = {"token_mean": float(np.mean([r["token_hamming"] for r in records])),
              "cell_mean": float(np.mean(cell_all)) if cell_all else None,
              "cell_empty_mean": float(np.mean(cell_empty)) if cell_empty else None,
              "n_cell_hamming": len(cell_all)}
    return {
        "n": n,
        "official_exact_share": float(np.mean([float(r["official_exact"]) for r in records])),
        "generated": generated,
        "teacher": teacher,
        "per_level": per_level,
        "hamming": hamming,
    }
