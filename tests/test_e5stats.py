import numpy as np
import pytest

from ncm_sudoku.e5stats import ALPHA, betting_logk, claim_a, claim_b, rejects, to_unit


def test_input_checks():
    with pytest.raises(ValueError):
        betting_logk(np.array([0.5, 1.2]), 0.5)
    with pytest.raises(ValueError):
        betting_logk(np.array([0.5, np.nan]), 0.5)


def test_constant_at_null_never_rejects():
    x = np.full(500, 0.5)
    assert betting_logk(x, 0.5) == 0.0 and not rejects(x, 0.5)


def test_all_ones_bound_is_limited():
    # An all-ones sample cannot reject m0 above alpha^(1/N) (the D105 sanity limit).
    n = 50
    limit = ALPHA ** (1.0 / n)
    assert not rejects(np.ones(n), min(limit + 1e-6, 0.999))
    assert rejects(np.ones(n), 0.5)


@pytest.mark.parametrize("m0", [0.47, 0.5, 0.625])
def test_two_point_extreme_at_null_keeps_level(m0):
    rng = np.random.default_rng(int(m0 * 1000))
    x = (rng.random((40000, 200)) < m0).astype(float)  # Bernoulli with mean exactly m0
    fpr = rejects(x, m0).mean()
    assert fpr <= ALPHA + 3 * np.sqrt(ALPHA * (1 - ALPHA) / 40000)


def test_level_under_mixed_bounded_null():
    rng = np.random.default_rng(7)
    x = np.clip(rng.beta(2, 2, size=(20000, 300)) * 0.9 + 0.05, 0, 1)
    m0 = float(x.mean())  # null boundary at the true mean
    assert rejects(x, m0 + 1e-12).mean() <= ALPHA + 0.004


def test_power_on_clear_effects_and_claims():
    rng = np.random.default_rng(3)
    n = 300
    w_z = np.clip(0.5 + rng.normal(0, 0.04, n), 0, 1)
    w_p = np.ones(n)
    a = claim_a(w_p, w_z)
    assert a["A1_lower"] and a["A1_upper"] and a["A2"] and a["A"]
    q = np.clip(rng.normal(0.05, 0.06, n), -1, 1)
    b = claim_b(q, q - 0.05, q - 0.03, q - 0.13)
    assert b["B"]
    assert not claim_b(np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n))["B"]


def test_to_unit():
    assert np.allclose(to_unit([-1, 0, 1]), [0, 0.5, 1])
