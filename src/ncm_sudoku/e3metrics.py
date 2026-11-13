"""E3 secondary readability metrics (plan §5.1, §5.2, §8.3; spec ambiguities 15, 16).

Thresholded and ranking metrics are computed on the seed-averaged predictions
(§8.1), at the fixed probability threshold 0.5 (`THRESHOLD`) for every thresholded
metric. Brier-based endpoints (the primary metric, depth breakdown) average the
three seed models' per-puzzle Briers instead (`probes.brier_per_puzzle`,
`depth_breakdown_seeds`); this module reports `brier_ensemble` (the Brier of the
seed-averaged prediction) alongside, matching `e3controls.unit_metrics`.

Row-shaped arguments (`pred`, `y` in `f1_scores`, `pr_auc`, `mask_exact_match`,
`count_mae`, `naked_single_f1`, `ranking_metrics`) are flat (N, 9) examples, one
row per (puzzle, empty cell), in the row-major `np.nonzero(empty)` order used
throughout the package (`probes.build_inputs`). `hidden_single_f1` and
`secondary_metrics` instead take the full per-puzzle grids ([n, 81, 9] /
[n, 81]), because a hidden single is a property of a whole unit (27 cells), not
of one row.

§8.3: "If the positive or negative class is missing, the affected metric is not
interpretable, not zero." `f1_scores` (per digit), `pr_auc` and `e3controls.roc_auc`
follow this. `hidden_single_f1` and `naked_single_f1` instead report 0.0 when one
side of the match is empty but the other is not (a true item with no matching
prediction is a real miss, not an uninterpretable quantity, per spec ambiguity
16); both are None only when truth and prediction are both empty.
"""

import numpy as np

from ncm_sudoku.e3controls import roc_auc
from ncm_sudoku.grid import UNITS
from ncm_sudoku.labels import CENSORED, STUCK, candidate_mask, hidden_singles
from ncm_sudoku.probes import brier_per_puzzle

THRESHOLD = 0.5

DEPTH_CLASSES = {
    "1": lambda d: d == 1,
    "2": lambda d: d == 2,
    "3": lambda d: d == 3,
    ">=4": lambda d: d >= 4,
    "stuck": lambda d: d == STUCK,
    "censored": lambda d: d == CENSORED,
}


def depth_breakdown(preds: np.ndarray, mask: np.ndarray, empty: np.ndarray, depth: np.ndarray) -> dict:
    """Brier per depth class over PROBE-VAL empty cells (rows of `preds` in row-major
    (puzzle, cell) order): per puzzle over its cells of the class, then over the
    puzzles that have such cells (§8.3 aggregation)."""
    empty = np.asarray(empty, bool)
    pz, _ = np.nonzero(empty)
    d, y = np.asarray(depth)[empty], np.asarray(mask)[empty]
    out = {}
    for name, rule in DEPTH_CLASSES.items():
        sel = rule(d)
        pb = brier_per_puzzle(np.asarray(preds)[sel], y[sel], pz[sel], len(empty))
        n_cells = int(sel.sum())
        out[name] = {
            "brier": float(np.nanmean(pb)) if n_cells else None,
            "n_cells": n_cells,
            "n_puzzles": int(len(np.unique(pz[sel]))),
        }
    return out


def depth_breakdown_seeds(preds: list, mask: np.ndarray, empty: np.ndarray, depth: np.ndarray) -> dict:
    """`depth_breakdown` per seed model, then the mean of the per-seed Briers (the scale of
    every headline Brier: mean over seeds, not the Brier of the seed-averaged prediction)."""
    per = [depth_breakdown(p, mask, empty, depth) for p in preds]
    out = {}
    for c in DEPTH_CLASSES:
        b = [x[c]["brier"] for x in per]
        out[c] = {"brier": None if None in b else float(np.mean(b)), "brier_per_seed": b,
                  "n_cells": per[0][c]["n_cells"], "n_puzzles": per[0][c]["n_puzzles"]}
    return out


def depth_label_rates(mask: np.ndarray, empty: np.ndarray, depth: np.ndarray) -> dict:
    """Per `DEPTH_CLASSES` class (all six keys, including "censored"): sample sizes
    `n_cells`/`n_puzzles` and the label proportion over the class's empty cells
    (`positive_rate`, mean candidate bit; `positive_rate_per_digit`, 9 floats).
    Rates are None for an empty class (no cells of that depth)."""
    empty = np.asarray(empty, bool)
    pz, _ = np.nonzero(empty)
    d = np.asarray(depth)[empty]
    y = np.asarray(mask, np.float64)[empty]
    out = {}
    for name, rule in DEPTH_CLASSES.items():
        sel = rule(d)
        n_cells = int(sel.sum())
        if n_cells:
            out[name] = {
                "n_cells": n_cells,
                "n_puzzles": int(len(np.unique(pz[sel]))),
                "positive_rate": float(y[sel].mean()),
                "positive_rate_per_digit": y[sel].mean(axis=0).tolist(),
            }
        else:
            out[name] = {"n_cells": 0, "n_puzzles": 0, "positive_rate": None, "positive_rate_per_digit": None}
    return out


def f1_scores(pred: np.ndarray, y: np.ndarray) -> dict:
    """Per-digit and macro F1 at `THRESHOLD` (§8.3). `per_digit[d]` is None when
    digit d has no positive or no negative label in `y` ("not interpretable, not
    zero"); `macro` is None if any digit is None."""
    pred_bits = np.asarray(pred) >= THRESHOLD
    y_bits = np.asarray(y) >= THRESHOLD
    per_digit: list = []
    for d in range(y_bits.shape[1]):
        yd = y_bits[:, d]
        n_pos, n_neg = int(yd.sum()), int((~yd).sum())
        if n_pos == 0 or n_neg == 0:
            per_digit.append(None)
            continue
        pd = pred_bits[:, d]
        tp = int((pd & yd).sum())
        fp = int((pd & ~yd).sum())
        fn = int((~pd & yd).sum())
        per_digit.append(float(2 * tp / (2 * tp + fp + fn)))
    macro = None if any(v is None for v in per_digit) else float(np.mean(per_digit))
    return {"per_digit": per_digit, "macro": macro}


def pr_auc(scores: np.ndarray, y: np.ndarray) -> float | None:
    """Step-wise average precision for the positive class (tied scores grouped
    into one threshold step, same convention as `e3controls.roc_auc`); None if a
    class (positive or negative) is missing."""
    s = np.asarray(scores, np.float64).ravel()
    yb = np.asarray(y).ravel().astype(bool)
    n_pos = int(yb.sum())
    n_neg = len(yb) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    order = np.argsort(-s, kind="stable")
    s_sorted, y_sorted = s[order], yb[order]
    tp_cum = np.cumsum(y_sorted)
    fp_cum = np.cumsum(~y_sorted)
    boundary = np.r_[np.flatnonzero(np.diff(s_sorted)), len(s_sorted) - 1]
    tp, fp = tp_cum[boundary], fp_cum[boundary]
    precision = tp / (tp + fp)
    recall = tp / n_pos
    recall_prev = np.r_[0.0, recall[:-1]]
    return float(np.sum((recall - recall_prev) * precision))


def ranking_metrics(pred: np.ndarray, y: np.ndarray) -> dict:
    """Per-digit and macro PR-AUC, the per-digit and pooled positive rate, and the
    pooled ROC-AUC (`e3controls.roc_auc`)."""
    pred, y = np.asarray(pred), np.asarray(y)
    per_digit = [pr_auc(pred[:, d], y[:, d]) for d in range(y.shape[1])]
    macro = None if any(v is None for v in per_digit) else float(np.mean(per_digit))
    return {
        "pr_auc_per_digit": per_digit,
        "pr_auc_macro": macro,
        "positive_rate_per_digit": np.asarray(y, np.float64).mean(axis=0).tolist(),
        "positive_rate": float(np.asarray(y, np.float64).mean()),
        "roc_auc": roc_auc(pred, y),
    }


def mask_exact_match(pred: np.ndarray, y: np.ndarray) -> float:
    """Share of cells where the thresholded 9-bit prediction equals the label exactly."""
    pred_bits = np.asarray(pred) >= THRESHOLD
    y_bits = np.asarray(y) >= THRESHOLD
    return float((pred_bits == y_bits).all(axis=1).mean())


def count_mae(pred: np.ndarray, y: np.ndarray) -> float:
    """Mean absolute error of the thresholded candidate count per cell (spec
    ambiguity 15)."""
    pred_count = (np.asarray(pred) >= THRESHOLD).sum(axis=1)
    y_count = (np.asarray(y) >= THRESHOLD).sum(axis=1)
    return float(np.abs(pred_count - y_count).mean())


def naked_single_f1(pred: np.ndarray, y: np.ndarray) -> float | None:
    """F1 of the naked-single event (candidate count exactly 1) over cells, a true
    positive requiring the same digit on both sides (not merely "both naked"), on
    the same 2 tp / (n_true + n_pred) scale as `hidden_single_f1` (spec ambiguity
    16's revised convention extended to naked singles): None only when neither
    side has a naked single."""
    pred_bits = np.asarray(pred) >= THRESHOLD
    y_bits = np.asarray(y) >= THRESHOLD
    pred_naked = pred_bits.sum(axis=1) == 1
    true_naked = y_bits.sum(axis=1) == 1
    pred_digit = np.argmax(pred_bits, axis=1)
    true_digit = np.argmax(y_bits, axis=1)
    tp = int(np.sum(pred_naked & true_naked & (pred_digit == true_digit)))
    n_pred, n_true = int(pred_naked.sum()), int(true_naked.sum())
    if n_pred == 0 and n_true == 0:
        return None
    return float(2 * tp / (n_true + n_pred))


def _predicted_hidden_singles(pred_bits: np.ndarray, puzzle: np.ndarray) -> list[tuple[int, int, int]]:
    """(unit, digit, cell) triples: for each digit missing from unit u's clues, the
    one empty cell of u (if exactly one) with `pred_bits[cell, digit - 1]` set."""
    out = []
    puzzle = np.asarray(puzzle)
    for u, cells in enumerate(UNITS):
        present = set(puzzle[cells].tolist())
        for d in range(1, 10):
            if d in present:
                continue
            where = [int(c) for c in cells if puzzle[c] == 0 and pred_bits[c, d - 1]]
            if len(where) == 1:
                out.append((u, d, where[0]))
    return out


def _f1_from_items(truth_items: list, pred_items: list) -> dict:
    truth_set, pred_set = set(truth_items), set(pred_items)
    tp = len(truth_set & pred_set)
    n_true, n_pred = len(truth_set), len(pred_set)
    f1 = None if (n_true + n_pred) == 0 else float(2 * tp / (n_true + n_pred))
    return {"f1": f1, "n_true": n_true, "n_pred": n_pred, "tp": tp}


def hidden_single_f1(pred_grid: np.ndarray, puzzles: np.ndarray) -> dict:
    """F1 over (puzzle, unit, digit, cell) hidden-single items (spec ambiguity 16).
    `pred_grid` is [n, 81, 9] (given cells ignored); `puzzles` is [n, 81]. A
    prediction matches a truth item only with the same cell. `hidden_only` drops,
    on each side, items whose cell is a naked single on that side (truth: in
    `labels.candidate_mask`; prediction: `(pred_grid[cell] >= THRESHOLD).sum() != 1`
    is kept, i.e. a predicted naked single is dropped)."""
    pred_grid = np.asarray(pred_grid)
    puzzles = np.asarray(puzzles)
    truth_all, pred_all, truth_hidden, pred_hidden = [], [], [], []
    for i in range(len(puzzles)):
        p = puzzles[i]
        cm = candidate_mask(p)
        truth = hidden_singles(p)
        pred_bits = pred_grid[i] >= THRESHOLD
        pred_bits = pred_bits & (p == 0)[:, None]  # given cells ignored
        pred = _predicted_hidden_singles(pred_bits, p)
        truth_all.extend((i, u, d, c) for u, d, c in truth)
        pred_all.extend((i, u, d, c) for u, d, c in pred)
        truth_hidden.extend((i, u, d, c) for u, d, c in truth if cm[c].sum() != 1)
        pred_hidden.extend((i, u, d, c) for u, d, c in pred if pred_bits[c].sum() != 1)
    return {"all": _f1_from_items(truth_all, pred_all), "hidden_only": _f1_from_items(truth_hidden, pred_hidden)}


def secondary_metrics(
    pred_rows: np.ndarray,
    y_rows: np.ndarray,
    puzzle_idx: np.ndarray,
    n_puzzles: int,
    empty: np.ndarray,
    puzzles: np.ndarray,
) -> dict:
    """Bundles every row-shaped secondary metric (`f1_scores`, `ranking_metrics`,
    `mask_exact_match`, `count_mae`, `naked_single_f1`), the grid-shaped
    `hidden_single_f1` (`pred_rows` scattered back to [n_puzzles, 81, 9] at the
    `empty` positions), and `brier_ensemble` (the Brier of the seed-averaged
    prediction, §8.3 aggregation; the primary Brier endpoint instead averages
    per-seed Briers, `depth_breakdown_seeds`)."""
    empty = np.asarray(empty, bool)
    pred_rows = np.asarray(pred_rows, np.float64)
    y_rows = np.asarray(y_rows, np.float64)
    pred_grid = np.zeros((n_puzzles, 81, 9), dtype=np.float64)
    pred_grid[empty] = pred_rows
    return {
        "f1": f1_scores(pred_rows, y_rows),
        "ranking": ranking_metrics(pred_rows, y_rows),
        "mask_exact_match": mask_exact_match(pred_rows, y_rows),
        "count_mae": count_mae(pred_rows, y_rows),
        "naked_single_f1": naked_single_f1(pred_rows, y_rows),
        "hidden_single_f1": hidden_single_f1(pred_grid, puzzles),
        "brier_ensemble": float(np.nanmean(brier_per_puzzle(pred_rows, y_rows, puzzle_idx, n_puzzles))),
    }
