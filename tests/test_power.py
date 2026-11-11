import numpy as np
import pytest

from ncm_sudoku.power import e2_sample_size, h1_sample_size, required_n, shift_to, sign_flip, sign_mix, thin


def test_thin_hits_target_and_keeps_zeros():
    rng = np.random.default_rng(0); x = np.r_[np.full(200, -1.0), np.zeros(800)]   # mean -0.2
    m = np.mean([thin(x, 0.05, rng).mean() for _ in range(400)])
    assert m == pytest.approx(-0.05, abs=0.005)
    assert (thin(x, 0.05, rng)[200:] == 0).all()


def test_sign_mix_keeps_magnitudes():
    rng = np.random.default_rng(0); x = np.r_[np.full(200, -1.0), np.zeros(800)]
    y = sign_mix(x, -0.05, rng)
    assert (np.abs(y) == np.abs(x)).all()
    assert np.mean([sign_mix(x, -0.05, rng).mean() for _ in range(400)]) == pytest.approx(-0.05, abs=0.005)
    with pytest.raises(ValueError):
        sign_mix(np.r_[np.full(10, -1.0), np.zeros(990)], -0.05, rng)


def test_sign_flip_range_and_zeros():
    rng = np.random.default_rng(0); x = np.array([0.0, 1.0, -1 / 3, 2 / 3])
    y = sign_flip(x, rng)
    assert y[0] == 0 and (np.abs(y) == np.abs(x)).all()


def test_required_n_monotone_toy():
    n = required_n(lambda n, rng: rng.normal(-0.2, 1, n), lambda a: a.mean() < 0, ns=range(10, 201, 10), reps=200)
    assert n is not None and n <= 100


def test_required_n_none_when_target_unreachable():
    assert required_n(lambda n, rng: np.zeros(n), lambda a: False, ns=range(10, 31, 10), reps=5) is None


def test_thin_and_sign_mix_size_resample_from_pilot():
    rng = np.random.default_rng(0); x = np.r_[np.full(200, -1.0), np.zeros(800)]
    assert thin(x, -0.05, rng, size=50).shape == (50,)
    y = sign_mix(x, -0.05, rng, size=5000)
    assert set(np.unique(y)) <= {-1.0, 0.0, 1.0}
    assert y.mean() == pytest.approx(-0.05, abs=0.03)


def test_e2_sample_size_structure_and_infeasible_scenarios():
    values = {
        "theta2": np.r_[np.full(60, -1.0), np.zeros(240)],        # mean -0.2
        "theta_comp": np.zeros(300),     # bound q(0, n) at 0.98333 is about 4.1 / n
        "theta2_prime": np.zeros(300),   # bound q(0, n) at 0.95 is about 3.0 / n; sign_mix infeasible
    }
    out = e2_sample_size(values, reps=10, n_boot_sim=100, seed=0, ns=range(100, 201, 100))
    assert set(out) >= {"h2_thinning", "h2_sign_mix", "h3", "equivalence", "equivalence_error_at_boundary",
                        "max_rounded", "planning_parameters", "notes"}
    assert out["h3"] == 200 and out["equivalence"] == 100
    err = out["equivalence_error_at_boundary"]
    assert err["+0.03"] is None and err["-0.03"] is None and "notes" in out
    assert out["planning_parameters"]["reps"] == 10 and out["planning_parameters"]["n_boot_sim"] == 100
    assert out["h2_target"] == pytest.approx(-0.05) and out["h2_shortfall"] is False
    if None in (out["h2_thinning"], out["h2_sign_mix"]):
        assert out["max_rounded"] is None
    else:
        assert out["max_rounded"] == max(out["h2_thinning"], out["h2_sign_mix"], 200)


def test_e2_sample_size_shortfall_uses_observed_values():
    values = {"theta2": np.r_[np.full(10, -1.0), np.zeros(290)],
              "theta_comp": np.zeros(300), "theta2_prime": np.zeros(300)}
    out = e2_sample_size(values, reps=5, n_boot_sim=50, seed=0, ns=range(100, 101, 100))
    assert out["h2_shortfall"] is True
    assert out["h2_thinning"] is None and out["h2_sign_mix"] is None and out["max_rounded"] is None


def test_shift_to_mean_and_range():
    x = np.array([0.5, -0.2, 0.0, 0.1]); y = shift_to(x, 0.01)
    assert y.mean() == pytest.approx(0.01) and (np.abs(y) <= 1).all()


def test_shift_to_clips():
    assert shift_to(np.array([1.0, -1.0, 0.9]), 0.5).max() == 1.0


def test_h1_sample_size_toy():
    rng = np.random.default_rng(0); d = rng.normal(0.05, 0.05, 500)
    r = h1_sample_size(d, reps=100, n_boot_sim=200, ns=range(100, 501, 100))
    assert r["h1"] is not None and r["shortfall"] is False
    assert r["planning_parameters"]["reps"] == 100 and r["planning_parameters"]["h1_shift_target"] == 0.01


def test_h1_sample_size_is_directional(monkeypatch):
    # F7: H1 succeeds only when the interval lies above 0; an interval below 0 is a failure
    from ncm_sudoku import power
    monkeypatch.setattr(power, "interval", lambda a, level, n_boot: {"ci": (-0.2, -0.1)})
    assert h1_sample_size(np.full(50, 0.02), reps=5, n_boot_sim=20, ns=range(100, 201, 100))["h1"] is None
    monkeypatch.setattr(power, "interval", lambda a, level, n_boot: {"ci": (0.1, 0.2)})
    assert h1_sample_size(np.full(50, 0.02), reps=5, n_boot_sim=20, ns=range(100, 201, 100))["h1"] == 100


def test_h1_sample_size_shortfall_flag():
    r = h1_sample_size(np.full(50, 0.001) + np.linspace(-0.01, 0.01, 50), reps=5, n_boot_sim=50, ns=range(100, 101))
    assert r["shortfall"] is True and r["observed_mean"] == pytest.approx(0.001)
