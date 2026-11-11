import numpy as np
import pytest
import torch

from ncm_sudoku.probes import (
    GRID,
    SEEDS,
    brier_per_puzzle,
    build_inputs,
    fit_selected,
    select,
    train_probe,
)


def test_brier_ignores_given_cells():
    empty = np.zeros((1, 81), bool)
    empty[0, :2] = True
    X, pz, cell = build_inputs(np.zeros((1, 81, 3)), empty)
    assert X.shape == (2, 3 + 81) and cell.tolist() == [0, 1]
    pred = np.array([[1.0] * 9, [0.0] * 9])
    y = np.array([[1] * 9, [1] * 9])
    assert brier_per_puzzle(pred, y, np.array([0, 0]), 1)[0] == pytest.approx(0.5)


def test_build_inputs_n_positions_for_unit_probe():
    """D62: the unit-level probe (Task 4) reuses build_inputs with 27 positions."""
    feats = np.zeros((2, 27, 5))
    empty = np.ones((2, 27), bool)
    X, pz, pos = build_inputs(feats, empty, n_positions=27)
    assert X.shape == (54, 5 + 27)
    assert pos.tolist() == list(range(27)) * 2
    assert pz.tolist() == [0] * 27 + [1] * 27
    # position one-hot block is a proper identity pattern
    onehot = X[:, 5:].numpy()
    assert np.array_equal(onehot[:27], np.eye(27, dtype=np.float32))


def test_brier_per_puzzle_keeps_trailing_empty_puzzles_as_nan():
    """D63 review fix: n_puzzles is always an explicit argument, never inferred from
    max(puzzle_idx) + 1, so a puzzle with zero empty cells still gets a (NaN) row
    instead of silently shrinking the output length."""
    pred = np.full((6, 9), 0.5)
    y = np.zeros((6, 9))
    puzzle_idx = np.array([0, 0, 1, 1, 2, 2])  # puzzle 3 and 4 have no rows at all
    out = brier_per_puzzle(pred, y, puzzle_idx, n_puzzles=5)
    assert out.shape == (5,)
    assert np.isfinite(out[:3]).all()
    assert np.isnan(out[3]) and np.isnan(out[4])


def test_select_uses_mean_val_brier_over_seeds():
    res = {(0, 1e-3): [0.10, 0.30, 0.30], (1e-4, 1e-3): [0.20, 0.20, 0.20]}
    assert select(res) == (1e-4, 1e-3)


def test_select_raises_on_no_usable_configuration():
    with pytest.raises(ValueError):
        select({})
    with pytest.raises(ValueError):
        select({(0, 1e-3): [], (1e-4, 1e-3): [float("nan"), float("nan")]})


def test_linear_probe_learns_separable_toy():
    """Deviation from the brief's literal `epochs=30`: with the mandated default
    `batch=4096` (D55) and only 2,000 training rows here, every epoch is exactly one
    full-batch AdamW step (2,000 < 4,096). AdamW's per-step displacement is bounded
    by ~lr regardless of gradient size, so reaching the weight magnitude (~3, for
    standard-normal features) a perfectly separable target needs for Brier < 0.05
    takes on the order of 1,900 such steps at lr = 3e-3, not 30 (verified empirically
    and by a closed-form population-Brier check for sigmoid(w*x) vs. 1{x>0}). D63's
    `min_steps=2000` default now covers this: `epochs` is left low (1) and the
    realized budget comes entirely from `min_steps`, which this test also checks via
    the returned info dict.
    """
    rng = np.random.default_rng(0)
    n = 40
    feats = rng.normal(size=(n, 81, 4))
    empty = np.ones((n, 81), bool)
    y = (feats[..., :1] > 0).repeat(9, axis=2).astype(np.float32)
    X, pz, _ = build_inputs(feats, empty)
    Y = torch.tensor(y.reshape(-1, 9))
    _, b, info = train_probe(X[:2000], Y[:2000], X[2000:], Y[2000:], pz[2000:], n, "linear", 0.0, 3e-3, 0, epochs=1)
    assert b < 0.05
    assert info["n_steps"] >= 2000  # min_steps default, not the explicit epochs=1
    assert info["epochs_run"] * 1 == info["n_steps"]  # steps_per_epoch is 1 here (2000 rows < batch 4096)


def test_min_steps_raises_effective_epochs_for_small_n_and_reports_consistent_budget():
    """D63: every probe trains for at least `min_steps` gradient steps regardless of
    `epochs`, so small training sets (N < batch) are not silently under-trained
    relative to large ones; the realized budget is recorded and internally
    consistent."""
    rng = np.random.default_rng(3)
    n_puzzles = 5
    feats_tr = rng.normal(size=(n_puzzles, 81, 4))  # 405 rows, well under batch=4096
    feats_va = rng.normal(size=(n_puzzles, 81, 4))
    empty = np.ones((n_puzzles, 81), bool)
    y_tr = (feats_tr[..., :1] > 0).repeat(9, axis=2).astype(np.float32)
    y_va = (feats_va[..., :1] > 0).repeat(9, axis=2).astype(np.float32)
    Xtr, _, _ = build_inputs(feats_tr, empty)
    Ytr = torch.tensor(y_tr.reshape(-1, 9))
    Xva, pz_va, _ = build_inputs(feats_va, empty)
    Yva = torch.tensor(y_va.reshape(-1, 9))

    _, _, info = train_probe(Xtr, Ytr, Xva, Yva, pz_va, n_puzzles, "linear", 0.0, 1e-3, 0, epochs=1, min_steps=2000)
    assert info["n_steps"] >= 2000
    assert info["epochs_run"] >= 2000  # steps_per_epoch == 1 since 405 rows < batch 4096
    assert 0 <= info["best_epoch"] < info["epochs_run"]
    assert info["hit_cap"] == (info["best_epoch"] == info["epochs_run"] - 1)
    assert info["n_params"] == (4 + 81 + 1) * 9  # Linear(85, 9): weight + bias


def test_grid_and_seeds_match_plan():
    assert GRID == [(wd, lr) for wd in (0, 1e-4, 1e-3, 1e-2, 1e-1) for lr in (1e-3, 3e-3)]
    assert SEEDS == (0, 1, 2)


def test_fit_selected_recovers_separable_toy_and_reports_shapes():
    """Small, fast grid run (small min_steps) on the same separable toy task used
    above; checks shapes/types of every returned field, not just the selected
    Brier, including the per-(config, seed) training budget."""
    rng = np.random.default_rng(1)
    n_tr, n_va = 30, 10
    feats_tr = rng.normal(size=(n_tr, 81, 4))
    feats_va = rng.normal(size=(n_va, 81, 4))
    empty_tr = np.ones((n_tr, 81), bool)
    empty_va = np.ones((n_va, 81), bool)
    y_tr = (feats_tr[..., :1] > 0).repeat(9, axis=2).astype(np.float32)
    y_va = (feats_va[..., :1] > 0).repeat(9, axis=2).astype(np.float32)

    Xtr, _, _ = build_inputs(feats_tr, empty_tr)
    Ytr = torch.tensor(y_tr.reshape(-1, 9))
    Xva, pz_va, _ = build_inputs(feats_va, empty_va)
    Yva = torch.tensor(y_va.reshape(-1, 9))

    out = fit_selected(Xtr, Ytr, Xva, Yva, pz_va, n_va, "linear", epochs=3, batch=512, min_steps=10)
    assert out["config"] in GRID
    assert isinstance(out["val_brier_mean"], float)
    assert out["per_puzzle"].shape == (n_va,)
    assert out["preds"].shape == (Xva.shape[0], 9)
    assert out["val_brier_mean"] < 0.3  # loose: tiny min_steps, just checks it learns something
    assert set(out["budget"].keys()) == {(wd, lr, seed) for wd, lr in GRID for seed in SEEDS}
    for info in out["budget"].values():
        assert info["n_params"] > 0 and info["n_steps"] > 0


def test_fit_selected_train_va_tunes_separately_from_reported_va():
    """train_va (e.g. the permuted control's own permuted PROBE-VAL) drives model
    selection; per_puzzle/preds must still be computed on the primary (features_va,
    lab_va, va_puzzle, n_va_puzzles) quadruple, which can differ from train_va,
    including in its puzzle count."""
    rng = np.random.default_rng(2)
    n_tr, n_va = 20, 8
    feats_tr = rng.normal(size=(n_tr, 81, 4))
    feats_va = rng.normal(size=(n_va, 81, 4))
    empty = np.ones((n_va, 81), bool)
    y_tr = (feats_tr[..., :1] > 0).repeat(9, axis=2).astype(np.float32)
    y_va = (feats_va[..., :1] > 0).repeat(9, axis=2).astype(np.float32)

    Xtr, _, _ = build_inputs(feats_tr, np.ones((n_tr, 81), bool))
    Ytr = torch.tensor(y_tr.reshape(-1, 9))
    Xva, pz_va, _ = build_inputs(feats_va, empty)
    Yva = torch.tensor(y_va.reshape(-1, 9))

    # A separate tuning quadruple with a different puzzle count, standing in for a
    # permuted PROBE-VAL.
    n_tune = 5
    feats_tune = rng.normal(size=(n_tune, 81, 4))
    y_tune = (feats_tune[..., :1] > 0).repeat(9, axis=2).astype(np.float32)
    Xtune, pz_tune, _ = build_inputs(feats_tune, np.ones((n_tune, 81), bool))
    Ytune = torch.tensor(y_tune.reshape(-1, 9))

    out = fit_selected(
        Xtr,
        Ytr,
        Xva,
        Yva,
        pz_va,
        n_va,
        "linear",
        train_va=(Xtune, Ytune, pz_tune, n_tune),
        epochs=3,
        batch=512,
        min_steps=10,
    )
    assert out["per_puzzle"].shape == (n_va,)  # shaped against the primary va set, not train_va
    assert out["preds"].shape == (Xva.shape[0], 9)


def test_fit_selected_explicit_puzzle_count_keeps_trailing_empty_puzzle():
    """D63 review fix: a trailing PROBE-VAL puzzle with no empty cells (e.g. would be
    dropped by max(puzzle_idx) + 1 inference) still gets a row in `per_puzzle` when
    `n_va_puzzles` is passed explicitly."""
    rng = np.random.default_rng(4)
    n_tr = 20
    feats_tr = rng.normal(size=(n_tr, 81, 4))
    y_tr = (feats_tr[..., :1] > 0).repeat(9, axis=2).astype(np.float32)
    Xtr, _, _ = build_inputs(feats_tr, np.ones((n_tr, 81), bool))
    Ytr = torch.tensor(y_tr.reshape(-1, 9))

    n_va = 4
    feats_va = rng.normal(size=(n_va, 81, 4))
    y_va = (feats_va[..., :1] > 0).repeat(9, axis=2).astype(np.float32)
    empty_va = np.ones((n_va, 81), bool)
    empty_va[-1] = False  # last PROBE-VAL puzzle is fully given: no rows at all
    Xva, pz_va, _ = build_inputs(feats_va, empty_va)
    Yva = torch.tensor(y_va[empty_va].reshape(-1, 9))

    out = fit_selected(Xtr, Ytr, Xva, Yva, pz_va, n_va, "linear", epochs=1, batch=512, min_steps=10)
    assert out["per_puzzle"].shape == (n_va,)
    assert np.isnan(out["per_puzzle"][-1])  # the fully-given puzzle contributes no rows
    assert np.isfinite(out["per_puzzle"][:-1]).all()
