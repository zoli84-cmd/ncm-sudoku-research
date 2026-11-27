import importlib.util

import numpy as np

from conftest import ROOT


def _mod():
    spec = importlib.util.spec_from_file_location("e5_power", ROOT / "scripts" / "e5_power.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _rows(n=60, seed=0):
    rng = np.random.default_rng(seed)
    wz = np.where(rng.random(n) < 0.4, 0.5, np.clip(0.5 + rng.normal(0, 0.05, n), 0, 1))
    full = np.abs(rng.normal(0.06, 0.05, n))
    q = full * 0.85
    return {"wz": wz, "wp2": np.ones(n), "Q": q, "rand": full * 0.05, "hv": full * 0.35, "shuf": -full, "full": full}


def test_tilt_hits_target_and_keeps_tie_mass():
    m = _mod()
    rows = _rows()
    for target in (0.47, 0.515, 0.53):
        w = m.tilt_weights(rows["wz"], target)
        assert np.isclose((w * rows["wz"]).sum(), target) and np.isclose(w.sum(), 1)
        tie = rows["wz"] == 0.5
        assert np.isclose(w[tie].sum(), tie.mean())


def test_scenarios_put_exactly_one_contrast_at_its_null():
    m = _mod()
    rows = _rows()
    for mix, key in (("rand", "Q_minus_rand"), ("hv", "Q_minus_hv"), ("shuf", "Q_minus_shuf")):
        sc = m.scenario(rows, mix=mix)
        assert abs(sc["means"][key]) < 1e-12
        others = [k for k in ("Q_minus_rand", "Q_minus_hv", "Q_minus_shuf") if k != key]
        assert all(sc["means"][k] > 0 for k in others)
    sc = m.scenario(rows, kappa=0.7)
    assert np.isclose(sc["means"]["wp"], 0.85)
    sc = m.scenario(rows, scale=0.01 / rows["Q"].mean())
    assert np.isclose(sc["means"]["Q"], 0.01) and sc["means"]["Q_minus_hv"] > 0
