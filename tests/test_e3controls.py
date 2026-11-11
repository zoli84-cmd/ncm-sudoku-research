import numpy as np
import pytest

from ncm_sudoku import e3controls
from ncm_sudoku.e3controls import (
    marginal_brier,
    permute_labels,
    permute_puzzles,
    random_features,
    roc_auc,
    run_controls,
    run_unit_digit,
    unit_digit_labels,
    unit_metrics,
    unit_readout,
)
from ncm_sudoku.e3data import labels
from ncm_sudoku.grid import UNITS
from sudoku_cases import P

FAST = dict(epochs=1, min_steps=1)


def test_permuted_control_independent_and_eval_unpermuted():
    a = np.arange(10)[:, None, None] * np.ones((10, 81, 2))
    tr, va = permute_puzzles(a, 11), permute_puzzles(a, 12)
    assert not np.array_equal(tr, va)  # independent permutations
    assert all((tr[i] == tr[i, 0, 0]).all() for i in range(10))  # whole grid moved together
    # evaluation helper must score the permuted probe on UNPERMUTED val pairs:
    assert e3controls.EVAL_ON_UNPERMUTED_VAL is True


def test_permute_labels_keeps_multiset():
    m = np.random.default_rng(0).integers(0, 2, (5, 81, 9)).astype(np.uint8)
    e = np.ones((5, 81), bool)
    p = permute_labels(m, e, 0)
    assert sorted(map(tuple, p.reshape(-1, 9))) == sorted(map(tuple, m.reshape(-1, 9)))
    assert not np.array_equal(p, m)


def test_permute_labels_leaves_given_cells():
    m = np.random.default_rng(1).integers(0, 2, (3, 81, 9)).astype(np.uint8)
    e = np.zeros((3, 81), bool)
    e[:, ::2] = True
    p = permute_labels(m, e, 0)
    assert np.array_equal(p[~e], m[~e])


def test_random_features_shape_and_determinism():
    r = random_features(3, seed=0, dim=7)
    assert r.shape == (3, 81, 7) and r.dtype == np.float32
    assert np.array_equal(r, random_features(3, seed=0, dim=7))


def test_marginal_brier_constant_labels_is_zero():
    m = np.ones((4, 81, 9), np.uint8)
    e = np.ones((4, 81), bool)
    assert np.allclose(marginal_brier(m, e, m, e), 0.0)


def test_marginal_brier_half_rate():
    # Train: position bits are 1 in half the puzzles -> p = 0.5; val Brier = 0.25.
    m_tr = np.zeros((2, 81, 9), np.uint8)
    m_tr[0] = 1
    e = np.ones((2, 81), bool)
    out = marginal_brier(m_tr, e, np.ones((3, 81, 9), np.uint8), np.ones((3, 81), bool))
    assert out.shape == (3,) and np.allclose(out, 0.25)


def test_unit_digit_labels_shape_and_definition():
    u = unit_digit_labels(np.asarray([P]))
    assert u.shape == (1, 27, 9)
    p = np.asarray(P)
    row0 = set(p[:9]) - {0}
    assert [d + 1 for d in range(9) if u[0, 0, d]] == sorted(row0)  # unit 0 = row 0: placed digits
    box0 = set(p[UNITS[18]]) - {0}
    assert [d + 1 for d in range(9) if u[0, 18, d]] == sorted(box0)


def test_unit_readout_is_mean_over_unit_cells():
    f = np.arange(2 * 81 * 3, dtype=np.float32).reshape(2, 81, 3)
    r = unit_readout(f)
    assert r.shape == (2, 27, 3)
    assert np.allclose(r[1, 9], f[1, UNITS[9]].mean(axis=0))  # column 0


def test_roc_auc_rank_formula():
    assert roc_auc(np.array([0.1, 0.2, 0.8, 0.9]), np.array([0, 0, 1, 1])) == 1.0
    assert roc_auc(np.array([0.9, 0.8, 0.2, 0.1]), np.array([0, 0, 1, 1])) == 0.0
    assert roc_auc(np.full(4, 0.5), np.array([0, 1, 0, 1])) == 0.5  # ties count half
    # one pos/neg pair tied, one correctly ordered: (1 + 0.5 + 1 + 1) / 4
    assert roc_auc(np.array([0.1, 0.5, 0.5, 0.9]), np.array([0, 0, 1, 1])) == pytest.approx(0.875)
    assert np.isnan(roc_auc(np.array([0.1, 0.2]), np.array([1, 1])))  # missing class


def test_unit_metrics():
    y = np.array([[1, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 0, 0, 0, 0, 0, 0, 0]], dtype=float)
    pred = np.array([[0.9] + [0.1] * 8, [0.9, 0.4] + [0.1] * 7])  # row 1 misses one digit
    out = unit_metrics(pred, y, np.array([0, 0]), 1)
    assert out["exact_match"] == 0.5
    assert out["roc_auc"] == pytest.approx(roc_auc(pred, y))
    assert out["brier"] == pytest.approx(((pred - y) ** 2).mean())


def _subset(n, seed, dim=4):
    """Digit-relabelled copies of P (all 30 clues), with their true labels."""
    rng = np.random.default_rng(seed)
    p = np.asarray(P)
    puzzles = np.stack([np.concatenate([[0], rng.permutation(9) + 1])[p] for _ in range(n)])
    lab = labels(puzzles)
    return {
        "puzzles": puzzles,
        "mask": lab["mask"],
        "empty": lab["empty"],
        "rep": rng.standard_normal((n, 81, dim)).astype(np.float32),
        "teacher": {lv: rng.standard_normal((n, 81, dim)).astype(np.float32) for lv in (2, 6, 12)},
    }


CONTROLS = {
    "raw_linear",
    "raw_mlp",
    "peer_counts_linear",
    "rule",
    "surface_linear",
    "permuted_linear",
    "random_linear",
    "label_permuted_linear",
    "teacher_L02_linear",
    "teacher_L06_linear",
    "teacher_L12_linear",
    "marginal",
}


def test_run_controls_outputs():
    tr, va = _subset(4, 0), _subset(3, 1)
    out = run_controls(tr, va, **FAST)
    assert set(out) == CONTROLS
    for name, r in out.items():
        assert len(r["per_puzzle"]) == 3 and isinstance(r["per_puzzle"], list), name
    assert out["rule"]["val_brier_mean"] == 0.0  # exact candidate_mask rule = ceiling
    assert np.isfinite(out["permuted_linear"]["val_brier_mean"])
    assert out["permuted_linear"]["budget"]["n_params"] == (4 + 81) * 9 + 9
    assert len(out["permuted_linear"]["budget"]["selected"]) == 3


def test_permuted_control_tunes_on_permuted_and_reports_on_unpermuted(monkeypatch):
    tr, va = _subset(4, 0), _subset(3, 1)
    calls = []

    def fake_fit(Xtr, Ytr, Xva, Yva, va_puzzle, n_va, kind, train_va=None, **kw):
        calls.append((Xtr, Xva, train_va))
        return {"config": (0, 1e-3), "val_brier_mean": 0.1, "per_puzzle": np.zeros(n_va), "preds": None, "budget": {}}

    monkeypatch.setattr(e3controls, "fit_selected", fake_fit)
    run_controls(tr, va, **FAST)
    perm = [c for c in calls if c[2] is not None]
    assert len(perm) == 1
    Xtr, Xva, train_va = perm[0]
    e = va["empty"]
    rep_va = np.asarray(Xva[:, :4])
    assert np.array_equal(rep_va, va["rep"][e])  # reported on unpermuted val
    assert np.array_equal(np.asarray(train_va[0][:, :4]), permute_puzzles(va["rep"], 12)[e])
    assert np.array_equal(np.asarray(Xtr[:, :4]), permute_puzzles(tr["rep"], 11)[tr["empty"]])


def test_run_controls_rejects_mixed_clue_counts():
    tr, va = _subset(4, 0), _subset(3, 1)
    tr["puzzles"][0, np.nonzero(tr["puzzles"][0])[0][0]] = 0
    with pytest.raises(ValueError):
        run_controls(tr, va, **FAST)


def test_run_unit_digit_outputs():
    tr, va = _subset(4, 0), _subset(3, 1)
    out = run_unit_digit(tr, va, **FAST)
    assert set(out) == {"generated", "raw"}
    for r in out.values():
        assert {"config", "val_brier_mean", "per_puzzle", "budget", "exact_match", "roc_auc", "brier"} <= set(r)
        assert len(r["per_puzzle"]) == 3
        assert 0.0 <= r["exact_match"] <= 1.0
