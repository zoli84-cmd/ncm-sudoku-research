import numpy as np
import pytest
import torch

from ncm_sudoku import e3equiv
from ncm_sudoku.e3equiv import equivariance_pilot, model_predict_fn
from ncm_sudoku.labels import candidate_mask
from ncm_sudoku.symmetry import apply_symmetry, random_symmetry
from sudoku_cases import P


def _exact(pz):
    return np.stack([candidate_mask(p) for p in pz]).astype(float)


def test_equivariance_exact_predictor_zero_deviation():
    # candidate_mask is exactly equivariant, so back-transformed predictions equal the originals
    r = equivariance_pilot(np.asarray([P, P]), [_exact, _exact, _exact], n=2, k=3, seed=0)
    assert all(np.allclose(r["deviation"][kind], 0) for kind in ("all", "digit", "geometric"))
    assert r["acceptable"] == 0.0
    assert all(r["share_within"][kind] == 1.0 for kind in ("all", "digit", "geometric"))
    assert len(r["seed_noise"]) == 2 and r["n"] == 2 and r["k"] == 3


def test_equivariance_reports_brier_exact_and_constant():
    # §8.4: predictive performance next to deviation; Brier against candidate_mask(original)
    r = equivariance_pilot(np.asarray([P, P]), [_exact, _exact], n=2, k=3, seed=0)
    assert all(np.allclose(r["brier"][kind], 0) for kind in ("all", "digit", "geometric"))
    assert np.allclose(r["brier_original"], 0) and r["mean_brier"]["all"] == 0.0
    half = lambda pz: np.full((len(pz), 81, 9), 0.5)  # noqa: E731
    r = equivariance_pilot(np.asarray([P, P]), [half, half], n=2, k=3, seed=0)
    assert all(np.allclose(r["brier"][kind], 0.25) for kind in ("all", "digit", "geometric"))
    assert np.allclose(r["brier_original"], 0.25) and r["mean_brier_original"] == pytest.approx(0.25)
    assert len(r["brier"]["all"]) == 2 and len(r["brier_original"]) == 2


def test_equivariance_takes_first_n_and_counts_transforms():
    calls = []

    def f(pz):
        calls.append(len(pz))
        return _exact(pz)

    pz = np.stack([P, apply_symmetry(P, random_symmetry(np.random.default_rng(5))), P])
    r = equivariance_pilot(pz, [f, f], n=2, k=4, seed=0)
    assert len(r["deviation"]["all"]) == 2
    assert sum(calls) == 2 * (2 + 2 * (4 + 2 + 2))  # per predictor: originals + (k + 2 + 2) transforms each


def test_equivariance_position_bias_breaks_geometric_not_digit():
    # A predictor that depends on cell position only is digit-equivariant but not geometric.
    bias = np.random.default_rng(0).random((81, 9))
    f = lambda pz: np.broadcast_to(bias[:, :1], (len(pz), 81, 9)).copy()  # noqa: E731  same for all digits
    r = equivariance_pilot(np.asarray([P]), [f, f], n=1, k=2, seed=0)
    assert np.allclose(r["deviation"]["digit"], 0)
    assert r["deviation"]["geometric"][0] > 0 and r["deviation"]["all"][0] > 0
    assert r["share_within"]["geometric"] == 0.0


def test_seed_noise_is_pairwise_difference():
    f0 = lambda pz: np.zeros((len(pz), 81, 9))  # noqa: E731
    f1 = lambda pz: np.full((len(pz), 81, 9), 0.3)  # noqa: E731
    r = equivariance_pilot(np.asarray([P]), [f0, f1], n=1, k=1, seed=0)
    assert r["seed_noise"][0] == pytest.approx(0.3) and r["acceptable"] == pytest.approx(0.3)


def test_model_predict_fn_applies_probe_and_caches(monkeypatch):
    calls = []

    def fake_states(m, puzzles, batch=50):
        calls.append(len(puzzles))
        return np.ones((len(puzzles), 81, 4), np.float32)

    monkeypatch.setattr(e3equiv, "level6_states", fake_states)
    probe = torch.nn.Sequential(torch.nn.Linear(4 + 81, 9), torch.nn.Sigmoid())
    cache = {}
    fns = [model_predict_fn(None, probe, cache), model_predict_fn(None, probe, cache)]
    pz = np.asarray([P, P, P])
    a, b = fns[0](pz), fns[1](pz)
    assert a.shape == (3, 81, 9) and np.allclose(a, b) and calls == [3]
    x = torch.cat([torch.ones(81, 4), torch.eye(81)], dim=1)
    with torch.no_grad():
        assert np.allclose(a[0], probe(x).numpy(), atol=1e-6)
