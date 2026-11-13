"""E3 secondary readability metrics (plan v3.7 §5.1, §5.2, §8.3; spec ambiguities 15, 16)."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from ncm_sudoku.e3metrics import (
    THRESHOLD,
    count_mae,
    depth_label_rates,
    f1_scores,
    hidden_single_f1,
    mask_exact_match,
    naked_single_f1,
    pr_auc,
    ranking_metrics,
    secondary_metrics,
)
from ncm_sudoku.labels import candidate_mask, hidden_singles
from sudoku_cases import P, S

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_threshold_is_half():
    assert THRESHOLD == 0.5


def test_f1_scores_hand_case_and_missing_class():
    assert f1_scores(np.array([[.9] * 9, [.1] * 9]), np.array([[1] * 9, [0] * 9]))["macro"] == 1.0
    assert f1_scores(np.array([[.9] * 9]), np.array([[1] * 9]))["per_digit"][0] is None  # no negatives


def test_pr_auc_known_value_and_ties():
    assert pr_auc(np.array([.9, .8, .7, .6]), np.array([1, 0, 1, 0])) == pytest.approx(5 / 6)
    assert pr_auc(np.array([.5, .5]), np.array([1, 0])) == pytest.approx(0.5)
    assert pr_auc(np.array([.5, .5]), np.array([1, 1])) is None


def test_mask_exact_match_and_count_mae():
    assert mask_exact_match(np.array([[.6] * 9]), np.array([[1] * 8 + [0]])) == 0.0
    assert count_mae(np.array([[.6] * 9]), np.array([[1] * 8 + [0]])) == 1.0


def test_naked_single_f1_hand_case():
    # row0: predicted naked single digit 1, matches truth (tp); row1: truth naked single
    # digit 1, but prediction has two active bits (not naked) -> false negative; row2:
    # neither true nor predicted naked. n_true=2, n_pred=1, tp=1 -> F1 = 2*1/(2+1).
    pred = np.array(
        [[.9, .1, .1, .1, .1, .1, .1, .1, .1],
         [.9, .9, .1, .1, .1, .1, .1, .1, .1],
         [.1] * 9]
    )
    y = np.array(
        [[1, 0, 0, 0, 0, 0, 0, 0, 0],
         [1, 0, 0, 0, 0, 0, 0, 0, 0],
         [0] * 9]
    )
    assert naked_single_f1(pred, y) == pytest.approx(2 / 3)
    assert naked_single_f1(np.zeros((1, 9)), np.zeros((1, 9))) is None


def test_hidden_single_f1_perfect_prediction_on_real_puzzle():
    truth = candidate_mask(P).astype(float)
    r = hidden_single_f1(truth[None], P[None])
    assert r["all"]["f1"] == 1.0 and r["all"]["n_true"] == len(hidden_singles(P))
    assert r["hidden_only"]["f1"] == 1.0  # predicted naked singles are excluded on the prediction side too
    assert r["hidden_only"]["n_true"] == sum(1 for u, d, c in hidden_singles(P) if candidate_mask(P)[c].sum() != 1)


def test_hidden_single_f1_wrong_cell_and_no_prediction():
    # truth has (2, 5, 24); predict the same unit/digit but a different cell of row 2 (18
    # is empty in P) -> that pair is a miss (tp 0), and tp 0 forces f1 0.0 regardless of
    # how many other truth items are unmatched.
    wrong = np.zeros((1, 81, 9))
    wrong[0, 18, 4] = 0.9
    r = hidden_single_f1(wrong, P[None])
    assert r["all"]["tp"] == 0 and r["all"]["f1"] == 0.0

    # all-zero predictions with n_true > 0 -> n_pred 0, f1 0.0 (not None, no division error)
    r0 = hidden_single_f1(np.zeros((1, 81, 9)), P[None])
    assert r0["all"]["n_true"] > 0 and r0["all"]["n_pred"] == 0 and r0["all"]["f1"] == 0.0

    # puzzle with no hidden singles (fully solved) and no predictions -> f1 None
    rnone = hidden_single_f1(np.zeros((1, 81, 9)), S[None])
    assert rnone["all"]["n_true"] == 0 and rnone["all"]["n_pred"] == 0 and rnone["all"]["f1"] is None


def test_hidden_single_f1_digits_are_one_based():
    # cell 24 is a hidden single for digit 5 (column index 4) in both its row (unit 2)
    # and its box (unit 20) -> 2 true matches; an off-by-one column (3, digit 4) must
    # not match any truth item, so a 0/1-based indexing bug would show up as a false tp.
    right = np.zeros((1, 81, 9))
    right[0, 24, 4] = 0.9
    wrong = np.zeros((1, 81, 9))
    wrong[0, 24, 3] = 0.9
    assert hidden_single_f1(right, P[None])["all"]["tp"] == 2
    assert hidden_single_f1(wrong, P[None])["all"]["tp"] == 0


def test_depth_label_rates_hand_case():
    empty = np.zeros((1, 81), bool)
    empty[0, :2] = True
    depth = np.zeros((1, 81), np.int16)
    depth[0, :2] = 1
    mask = np.zeros((1, 81, 9), np.uint8)
    mask[0, 0, :3] = 1  # 3 positive bits
    mask[0, 1, 0] = 1  # 1 positive bit
    out = depth_label_rates(mask, empty, depth)
    assert out["1"]["n_cells"] == 2 and out["1"]["n_puzzles"] == 1
    assert out["1"]["positive_rate"] == pytest.approx((3 + 1) / 18)
    assert out["stuck"]["positive_rate"] is None and out["stuck"]["n_cells"] == 0


def test_ranking_metrics_bundles_pr_auc_rates_and_roc_auc():
    pred = np.array([[.9] * 9, [.1] * 9])
    y = np.array([[1] * 9, [0] * 9])
    out = ranking_metrics(pred, y)
    assert out["pr_auc_per_digit"] == pytest.approx([1.0] * 9)
    assert out["pr_auc_macro"] == pytest.approx(1.0)
    assert out["positive_rate_per_digit"] == pytest.approx([0.5] * 9)
    assert out["positive_rate"] == pytest.approx(0.5)
    assert out["roc_auc"] == pytest.approx(1.0)


def test_secondary_metrics_perfect_prediction_bundles_everything():
    empty = (P == 0)[None, :]
    mask = candidate_mask(P)[None].astype(np.float64)
    pred_rows = mask[empty]
    y_rows = mask[empty]
    puzzle_idx = np.zeros(pred_rows.shape[0], dtype=np.int64)
    out = secondary_metrics(pred_rows, y_rows, puzzle_idx, 1, empty, P[None])
    assert out["mask_exact_match"] == 1.0
    assert out["count_mae"] == 0.0
    assert out["brier_ensemble"] == pytest.approx(0.0)
    assert out["naked_single_f1"] == 1.0
    assert out["hidden_single_f1"]["all"]["f1"] == 1.0
    assert out["hidden_single_f1"]["all"]["n_true"] == len(hidden_singles(P))
    assert out["ranking"]["roc_auc"] == pytest.approx(1.0)


def test_depth_breakdown_per_class():
    """Moved verbatim from e3_probes.py (D64 dry comparison unchanged)."""
    from ncm_sudoku.e3metrics import depth_breakdown

    empty = np.zeros((2, 81), bool)
    empty[:, :3] = True
    depth = np.zeros((2, 81), np.int16)
    depth[:, :3] = [1, 2, -1]
    mask = np.zeros((2, 81, 9), np.uint8)
    preds = np.zeros((6, 9))
    preds[0] = 1.0  # puzzle 0, cell 0 (depth 1): Brier 1
    out = depth_breakdown(preds, mask, empty, depth)
    assert out["1"] == {"brier": pytest.approx(0.5), "n_cells": 2, "n_puzzles": 2}
    assert out["2"]["brier"] == 0.0 and out["stuck"]["n_cells"] == 2
    assert out[">=4"] == {"brier": None, "n_cells": 0, "n_puzzles": 0}


def test_e3_probes_reexports_depth_functions():
    import ncm_sudoku.e3metrics as e3metrics

    mod = _load("e3_probes")
    assert mod.depth_breakdown is e3metrics.depth_breakdown
    assert mod.depth_breakdown_seeds is e3metrics.depth_breakdown_seeds
    assert mod.DEPTH_CLASSES is e3metrics.DEPTH_CLASSES
