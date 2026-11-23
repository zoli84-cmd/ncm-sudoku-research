import numpy as np
import torch

from ncm_sudoku.e5probes import (
    candidate_targets,
    exact_match_per_cell,
    grids_from_strings,
    masked_brier,
    train_untied,
    validation_carve,
)
from ncm_sudoku.labels import candidate_mask


def _planted(n=240, k=16, d=32, seed=0):
    """Every one of the 729 outputs copies one of k latent bits; X is a random linear
    image of the latent bits, so every output is exactly linearly decodable from X."""
    rng = np.random.default_rng(seed)
    Z = (rng.random((n, k)) < 0.5).astype(np.float32)
    Y = Z[:, np.arange(729) % k].reshape(n, 81, 9)
    R = rng.standard_normal((k, d)).astype(np.float32)
    X = ((2 * Z - 1) @ R).astype(np.float32)
    return torch.from_numpy(X), torch.from_numpy(Y)


def test_grids_from_strings_and_targets():
    s = "1" + "0" * 79 + "."
    g = grids_from_strings([s])
    assert g.shape == (1, 81) and g[0, 0] == 1 and g[0, 1:].sum() == 0
    mask, empty = candidate_targets(g)
    assert mask.shape == (1, 81, 9) and empty[0, 0] == False and empty[0, 80]  # noqa: E712
    assert np.array_equal(mask[0], candidate_mask(g[0]).astype(np.float32))


def test_validation_carve_partitions_each_cell():
    rng = np.random.default_rng(1)
    train = rng.random((50, 81)) < 0.6
    fit, val = validation_carve(train, share=0.125, seed=0)
    assert not (fit & val).any() and np.array_equal(fit | val, train)
    for c in range(81):
        n = train[:, c].sum()
        assert val[:, c].sum() == int(np.ceil(0.125 * n))
    fit2, val2 = validation_carve(train, share=0.125, seed=0)
    assert np.array_equal(val, val2)


def test_exact_match_per_cell_and_masked_brier():
    y = np.zeros((2, 81, 9), dtype=np.float32)
    y[:, :, 0] = 1
    pred = y.copy()
    pred[1, 0, 3] = 0.9  # wrong bit in puzzle 1, cell 0
    sel = np.zeros((2, 81), dtype=bool)
    sel[:, 0] = True
    sel[0, 1] = True
    em = exact_match_per_cell(pred, y, sel)
    assert em[0] == 0.5 and em[1] == 1.0 and np.isnan(em[2])
    # puzzle 0: two exact cells (0), puzzle 1: one cell with Brier 0.81 / 9
    assert np.isclose(masked_brier(pred, y, sel), (0.0 + 0.81 / 9) / 2)


def test_planted_signal_is_recovered_and_shuffled_is_not():
    X, Y = _planted()
    sel = np.ones((X.shape[0], 81), dtype=bool)
    test = np.zeros_like(sel)
    test[200:] = True
    train = sel & ~test
    fit, val = validation_carve(train, seed=0)
    model, _, info = train_untied(X, Y, fit, val, wd=0.0, lr=3e-3, seed=0, epochs=5, batch=64, min_steps=600)
    with torch.no_grad():
        pred = model(X).numpy()
    assert np.nanmean(exact_match_per_cell(pred, Y.numpy(), test)) > 0.9
    assert info["n_params"] == 32 * 729 + 729
    Xs = X[torch.randperm(X.shape[0], generator=torch.Generator().manual_seed(0))]
    model_s, _, _ = train_untied(Xs, Y, fit, val, wd=0.0, lr=3e-3, seed=0, epochs=5, batch=64, min_steps=600)
    with torch.no_grad():
        pred_s = model_s(Xs).numpy()
    assert np.nanmean(exact_match_per_cell(pred_s, Y.numpy(), test)) < 0.05


def test_unselected_entries_do_not_influence_training():
    X, Y = _planted(n=60)
    rng = np.random.default_rng(2)
    train = rng.random((60, 81)) < 0.5
    fit, val = validation_carve(train, seed=0)
    Y2 = Y.clone()
    outside = torch.from_numpy(~(fit | val))
    Y2[outside] = 1 - Y2[outside]
    kw = dict(wd=1e-3, lr=1e-3, seed=0, epochs=3, batch=16, min_steps=20)
    m1, b1, _ = train_untied(X, Y, fit, val, **kw)
    m2, b2, _ = train_untied(X, Y2, fit, val, **kw)
    assert b1 == b2
    assert all(torch.equal(p, q) for p, q in zip(m1.parameters(), m2.parameters()))
