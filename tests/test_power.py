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


# --- lock preparation (D70) ---

from ncm_sudoku.power import equivalence_boundary_error, equivalence_ok, h1_tost, inject  # noqa: E402


@pytest.mark.parametrize("target", [0.03, -0.03])
def test_inject_hits_target_and_keeps_nonzero(target):
    rng = np.random.default_rng(0); x = np.r_[np.full(5, 1.0), np.full(5, -1.0), np.full(10, 0.5), np.zeros(280)]
    assert np.mean([inject(x, target, rng).mean() for _ in range(2000)]) == pytest.approx(target, abs=0.002)
    y = inject(x, target, rng)
    assert (y[x != 0] == x[x != 0]).all()
    assert set(np.unique(y[x == 0])) <= {0.0, float(np.sign(target))}
    big = inject(x, target, rng, size=200000)
    assert big.shape == (200000,) and big.mean() == pytest.approx(target, abs=0.002)


def test_inject_infeasible_raises():
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        inject(np.ones(10), 0.03, rng)                              # z = 0
    with pytest.raises(ValueError):
        inject(np.r_[np.full(10, 1.0), np.zeros(90)], 0.03, rng)    # mean 0.1 > 0.03: p < 0
    with pytest.raises(ValueError):
        inject(np.r_[np.full(99, 1.0), np.zeros(1)], -0.5, rng)     # p > 1


def test_equivalence_ok_matches_tost_rule(monkeypatch):
    from ncm_sudoku import power
    calls = []

    def fake(a, level, n_boot):
        calls.append(level)
        return {"method": "bound", "ci": (-0.01, 0.01)} if level == 0.90 else {"method": "bound", "ci": (-0.04, 0.04)}
    monkeypatch.setattr(power, "interval", fake)
    assert equivalence_ok(np.zeros(5), 10) is False and calls == [0.90, 0.95]
    monkeypatch.setattr(power, "interval", lambda a, level, n_boot: {"method": "bootstrap", "ci": (-0.02, 0.02)})
    assert equivalence_ok(np.zeros(5), 10) is True


def test_equivalence_boundary_error_toy():
    x = np.r_[np.full(3, 1.0), np.full(3, -1.0), np.zeros(294)]
    r = equivalence_boundary_error(x, n=300, reps=20, n_boot_sim=100, seed=0)
    for k in ("+0.03", "-0.03"):
        assert 0.0 <= r["error"][k] <= 1.0
    assert r["planning_parameters"]["n"] == 300 and r["planning_parameters"]["margin"] == 0.03
    again = equivalence_boundary_error(x, n=300, reps=20, n_boot_sim=100, seed=0)
    assert again["error"] == r["error"]
    for k in ("+0.03", "-0.03"):
        d, p = r["detail"][k], r["error"][k]
        assert 0.0 <= d["bound_share"] <= 1.0
        assert d["mc_se"] == pytest.approx(np.sqrt(p * (1 - p) / 20))
        nb = round(d["bound_share"] * 20)
        parts = [(d["error_by_path"]["bound"], nb), (d["error_by_path"]["bootstrap"], 20 - nb)]
        for v, m in parts:
            assert (v is None) == (m == 0)
        assert sum(v * m for v, m in parts if m) / 20 == pytest.approx(p)


def test_equivalence_boundary_error_path_split(monkeypatch):
    from ncm_sudoku import power
    seq = iter([("bound", (-0.01, 0.01)), ("bootstrap", (-0.05, 0.05)), ("bootstrap", (-0.01, 0.01))] * 10)

    def fake(a, level, n_boot):
        if level == 0.95:
            return {"method": "bound", "ci": (-0.01, 0.01)}
        m, ci = next(seq)
        return {"method": m, "ci": ci}
    monkeypatch.setattr(power, "interval", fake)
    x = np.r_[np.full(3, 1.0), np.full(3, -1.0), np.zeros(294)]
    r = equivalence_boundary_error(x, n=300, reps=3, n_boot_sim=10)
    d = r["detail"]["+0.03"]
    assert d["bound_share"] == pytest.approx(1 / 3)
    assert d["error_by_path"] == {"bound": 1.0, "bootstrap": 0.5} and r["error"]["+0.03"] == pytest.approx(2 / 3)


def test_lock_defaults():
    import inspect
    assert inspect.signature(equivalence_boundary_error).parameters["reps"].default == 2000
    assert inspect.signature(h1_tost).parameters["n_boot_sim"].default == 2000


def test_equivalence_boundary_error_infeasible_is_none():
    r = equivalence_boundary_error(np.ones(100), n=100, reps=5, n_boot_sim=50)
    assert r["error"] == {"+0.03": None, "-0.03": None} and "+0.03" in r["notes"]


def test_h1_tost_toy():
    rng = np.random.default_rng(0); d = rng.normal(0.003, 0.004, 500)
    r = h1_tost(d, n=600, reps=40, n_boot_sim=200, seed=0)
    assert r["power_at_zero"] >= 0.9 and r["power_at_observed"] >= 0.9
    assert r["false_equivalence"]["+0.01"] <= 0.2 and r["false_equivalence"]["-0.01"] <= 0.2
    assert r["excludes_zero_at_observed"] >= 0.9
    assert r["observed_mean"] == pytest.approx(d.mean())
    assert r["planning_parameters"]["tost_level"] == pytest.approx(1 - 2 * 0.05 / 3)


def test_h1_tost_uses_two_sided_family_level(monkeypatch):
    from ncm_sudoku import power
    levels = []

    def fake(a, level, n_boot):
        levels.append(level)
        return {"method": "bootstrap", "ci": (0.001, 0.009)}
    monkeypatch.setattr(power, "interval", fake)
    r = h1_tost(np.full(50, 0.003), n=100, reps=3, n_boot_sim=20)
    assert sorted(set(levels)) == pytest.approx([1 - 2 * 0.05 / 3, 1 - 0.05 / 3])
    assert r["power_at_zero"] == 1.0 and r["excludes_zero_at_observed"] == 1.0
    monkeypatch.setattr(power, "interval", lambda a, level, n_boot: {"method": "bootstrap", "ci": (-0.02, 0.0)})
    assert h1_tost(np.full(50, 0.003), n=100, reps=3, n_boot_sim=20)["power_at_zero"] == 0.0


def test_h1_tost_inside_and_above_zero_needs_lower_bound_above_zero(monkeypatch):
    from ncm_sudoku import power
    # inside +-0.01 and excludes 0, but below 0: not "above 0"
    monkeypatch.setattr(power, "interval", lambda a, level, n_boot: {"method": "bootstrap", "ci": (-0.009, -0.001)})
    r = h1_tost(np.full(50, 0.003), n=100, reps=3, n_boot_sim=20)
    assert r["excludes_zero_at_observed"] == 1.0 and r["inside_and_above_zero_at_observed"] == 0.0
