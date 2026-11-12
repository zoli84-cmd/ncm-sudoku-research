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


def test_model_predict_fn_level_and_feature_builder(monkeypatch):
    calls = []

    def fake_level_states(m, puzzles, level, batch=50):
        calls.append((len(puzzles), level))
        return np.ones((len(puzzles), 81, 4), np.float32)

    monkeypatch.setattr(e3equiv, "cell_level_states", fake_level_states)
    monkeypatch.setattr(e3equiv, "level6_states", lambda *a, **k: pytest.fail("level 12 must not use level 6"))
    feats = lambda s: np.concatenate([s, 2 * s], axis=2)  # noqa: E731  [b, 81, 4] -> [b, 81, 8]
    probe = torch.nn.Sequential(torch.nn.Linear(8 + 81, 9), torch.nn.Sigmoid())
    cache = {}
    fns = [model_predict_fn(None, probe, cache, level=12, features=feats) for _ in range(2)]
    pz = np.asarray([P, P])
    a, b = fns[0](pz), fns[1](pz)
    assert a.shape == (2, 81, 9) and np.allclose(a, b) and calls == [(2, 12)]
    X = np.concatenate([np.ones((162, 4)), 2 * np.ones((162, 4)), np.tile(np.eye(81), (2, 1))], axis=1)
    with torch.no_grad():
        expect = probe(torch.from_numpy(X.astype(np.float32))).numpy().reshape(2, 81, 9)
    assert np.allclose(a, expect)


def test_level6_states_delegates_to_cell_level_states(monkeypatch):
    seen = []
    monkeypatch.setattr(e3equiv, "cell_level_states", lambda m, pz, level, batch=50: seen.append((level, batch)) or 0)
    e3equiv.level6_states(None, np.asarray([P]), batch=7)
    assert seen == [(6, 7)]


def test_equivariance_default_tolerance_is_seed_noise():
    f0 = lambda pz: np.zeros((len(pz), 81, 9))  # noqa: E731
    f1 = lambda pz: np.full((len(pz), 81, 9), 0.3)  # noqa: E731
    r = equivariance_pilot(np.asarray([P]), [f0, f1], n=1, k=1, seed=0)
    assert r["acceptable_source"] == "seed_noise"
    assert r["acceptable"] == r["seed_noise_p95"] == pytest.approx(0.3)


def test_equivariance_fixed_tolerance():
    # position-only predictor: digit deviation 0, geometric deviation > 0
    bias = np.random.default_rng(0).random((81, 9))
    f = lambda pz: np.broadcast_to(bias[:, :1], (len(pz), 81, 9)).copy()  # noqa: E731
    base = equivariance_pilot(np.asarray([P]), [f, f], n=1, k=2, seed=0)
    assert base["share_within"]["geometric"] == 0.0 and base["seed_noise_p95"] == 0.0
    big = float(base["deviation"]["geometric"][0]) + 1.0
    r = equivariance_pilot(np.asarray([P]), [f, f], n=1, k=2, seed=0, acceptable=big)
    assert r["acceptable_source"] == "fixed" and r["acceptable"] == big
    assert r["seed_noise_p95"] == 0.0  # still computed and reported
    assert r["share_within"] == {"all": 1.0, "digit": 1.0, "geometric": 1.0}
    assert np.allclose(r["deviation"]["geometric"], base["deviation"]["geometric"])
