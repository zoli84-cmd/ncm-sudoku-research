import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import torch

from ncm_sudoku import wholelayer
from ncm_sudoku.e3controls import first_n
from ncm_sudoku.e3data import raw_features
from ncm_sudoku.grid import PEERS
from ncm_sudoku.wholelayer import (
    PEER_IDX,
    cell_variance_share,
    fit_cell_pca,
    fit_pca,
    peer_states,
    project,
    raw_projected_features,
    variance_share,
    whole_layer_features,
)
from test_e3_scripts import FAST, _toy_runs

ROOT = Path(__file__).resolve().parents[1]


def _low_rank(n=60, d=40, r=5, seed=0):
    rng = np.random.default_rng(seed)
    return (rng.standard_normal((n, r)) @ rng.standard_normal((r, d)) + 3.0).astype(np.float32)


def test_fit_pca_recovers_low_rank_structure():
    x = _low_rank()
    pca = fit_pca(x, k=5)
    assert pca["components"].shape == (5, 40) and pca["mean"].shape == (40,)
    assert pca["explained_variance_share"] == pytest.approx(1.0, abs=1e-9)
    z = project(x, pca, whiten=False)
    assert z.shape == (60, 5) and z.dtype == np.float32
    recon = z.astype(np.float64) @ pca["components"] + pca["mean"]
    assert np.allclose(recon, x, atol=1e-3)


def test_chunked_covariance_pca_matches_direct_svd():
    rng = np.random.default_rng(3)
    x = rng.standard_normal((200, 12)) @ rng.standard_normal((12, 12))
    pca = fit_pca(x, k=6, chunk=17)  # chunk size does not divide n
    xc = x - x.mean(axis=0)
    _, s, vt = np.linalg.svd(xc, full_matrices=False)
    assert np.allclose(pca["mean"], x.mean(axis=0))
    # same subspace and, after the sign rule, the same vectors
    signs = np.sign(vt[np.arange(12), np.abs(vt).argmax(axis=1)])
    assert np.allclose(pca["components"], (vt * signs[:, None])[:6], atol=1e-8)
    assert pca["explained_variance_share"] == pytest.approx((s[:6] ** 2).sum() / (s**2).sum())


def test_whitening_gives_unit_train_std_and_padding():
    rng = np.random.default_rng(1)
    x = rng.standard_normal((500, 8)) * np.arange(1, 9)
    pca = fit_pca(x, k=8)
    z = project(x, pca)
    assert np.allclose(z.std(axis=0), 1.0, atol=1e-4)
    padded = fit_pca(x, k=12)  # more components than dimensions: zero rows, scale 1
    assert padded["components"].shape == (12, 8) and padded["n_components_fitted"] == 8
    assert np.all(padded["components"][8:] == 0.0) and np.all(padded["scale"][8:] == 1.0)
    assert np.allclose(project(x, padded)[:, 8:], 0.0)
    const = np.ones((10, 3))  # zero variance everywhere: scale 1, no division by zero
    assert np.all(fit_pca(const, k=2)["scale"] == 1.0)


def test_fit_pca_deterministic_sign():
    x = _low_rank(seed=2)
    a, b = fit_pca(x, k=5), fit_pca(x.copy(), k=5)
    assert np.array_equal(a["components"], b["components"])
    comp = a["components"]
    assert np.all(comp[np.arange(5), np.abs(comp).argmax(axis=1)] > 0)
    flipped = fit_pca(-x, k=5)["components"]
    assert np.allclose(flipped, comp, atol=1e-8)


def test_variance_share_on_val():
    rng = np.random.default_rng(4)
    basis = rng.standard_normal((2, 10))
    tr = rng.standard_normal((300, 2)) @ basis
    pca = fit_pca(tr, k=2)
    in_span = rng.standard_normal((50, 2)) @ basis
    assert variance_share(in_span, pca) == pytest.approx(1.0, abs=1e-9)
    off = rng.standard_normal((50, 10))
    share = variance_share(off, pca)
    assert 0.0 < share < 1.0
    xc = off - pca["mean"]
    exp = ((xc @ pca["components"].T) ** 2).sum() / (xc**2).sum()
    assert share == pytest.approx(exp)


def test_peer_layout():
    assert PEER_IDX.shape == (81, 21)
    for c in (0, 40, 80):
        assert PEER_IDX[c, 0] == c and list(PEER_IDX[c, 1:]) == list(PEERS[c])
    rng = np.random.default_rng(0)
    states = rng.standard_normal((2, 81, 3)).astype(np.float32)
    ps = peer_states(states)
    assert ps.shape == (2, 81, 21 * 3)
    assert np.array_equal(ps[1, 5].reshape(21, 3), states[1, PEER_IDX[5]])
    c = 0
    peer, non_peer = list(PEERS[c])[0], next(j for j in range(81) if j != c and j not in PEERS[c])
    moved = states.copy(); moved[0, peer] += 1.0
    assert not np.array_equal(peer_states(moved)[0, c], ps[0, c])
    moved = states.copy(); moved[0, non_peer] += 1.0
    assert np.array_equal(peer_states(moved)[0, c], ps[0, c])


def _toy_states(n=12, f=3, seed=0):
    rng = np.random.default_rng(seed)
    states = rng.standard_normal((n, 81, f)).astype(np.float32)
    empty = rng.random((n, 81)) < 0.6
    return states, empty


def test_cell_pca_fits_empty_rows_only_and_features():
    states, empty = _toy_states()
    pca = fit_cell_pca(states, empty, k=10, batch=5)
    rows = peer_states(states)[empty]
    direct = fit_pca(rows, k=10)
    assert np.allclose(pca["components"], direct["components"], atol=1e-8)
    assert np.allclose(pca["scale"], direct["scale"])
    f = whole_layer_features(states, pca, batch=5)
    assert f.shape == (12, 81, 10 + 3) and f.dtype == np.float32
    assert np.allclose(f[..., :10], project(peer_states(states).reshape(-1, 63), pca).reshape(12, 81, 10), atol=1e-5)
    assert np.array_equal(f[..., 10:], states)
    assert np.allclose(f[empty][:, :10].std(axis=0), 1.0, atol=1e-4)  # whitened on train empty rows
    assert cell_variance_share(states, empty, pca, batch=5) == pytest.approx(pca["explained_variance_share"])


def test_raw_projected_features():
    rng = np.random.default_rng(0)
    p = rng.integers(0, 10, (40, 81))
    empty = p == 0
    rows = raw_features(p)[empty]
    pca = fit_pca(rows, k=min(256, *rows.shape))  # k = min(256, number of components)
    assert pca["components"].shape[0] == 210
    f = raw_projected_features(p, pca)
    assert f.shape == (40, 81, 210) and f.dtype == np.float32
    assert np.allclose(f, project(raw_features(p).reshape(-1, 210), pca).reshape(40, 81, 210))


def _load():
    spec = importlib.util.spec_from_file_location("e3_wholelayer", ROOT / "scripts" / "e3_wholelayer.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CODE = {"commit": "abc", "dirty": False, "diff_sha256": None}


def _setup(tmp_path, monkeypatch, probes: dict | None = None):
    runs, out = tmp_path / "runs", tmp_path / "exp"
    _toy_runs(runs)
    if probes is not None:
        out.mkdir(parents=True)
        (out / "probes.json").write_text(json.dumps(probes), encoding="utf-8")
    mod = _load()
    for k, v in dict(RUNS=runs, OUT=out, KW=FAST, K=6).items():
        monkeypatch.setattr(mod, k, v)
    monkeypatch.setattr(mod, "environment_record", lambda: {"deterministic": torch.are_deterministic_algorithms_enabled()})
    monkeypatch.setattr(mod, "code_state", lambda: CODE)
    monkeypatch.setattr(mod.sys, "argv", ["e3_wholelayer.py"])
    return mod, runs, out


def test_e3_wholelayer_guard(tmp_path, monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod, "OUT", tmp_path)
    (tmp_path / "wholelayer.json").write_text("{}")
    with pytest.raises(SystemExit):
        mod.guard(force=False)
    mod.guard(force=True)


def _ref(b):
    return {"val_brier_mean": b}


PROBES = {"val_ids": [f"probe_val-{i}" for i in range(4)], "stages": {
    "L06_linear": _ref(0.20), "L12_linear": _ref(0.21), "L12_permuted_linear": _ref(0.24),
    "controls": {"permuted_linear": _ref(0.23), "surface_linear": _ref(0.22), "raw_linear": _ref(0.19)}}}


def test_e3_wholelayer_end_to_end(tmp_path, monkeypatch):
    mod, runs, out = _setup(tmp_path, monkeypatch, PROBES)
    torch.use_deterministic_algorithms(False)
    mod.main()
    r = json.loads((out / "wholelayer.json").read_text(encoding="utf-8"))
    assert "non-confirmatory" in r["note"] and r["environment"]["deterministic"] is True
    assert r["code"] == CODE and r["n_train"] == 8 and r["n_val"] == 4 and r["k"] == 6
    st = r["stages"]
    assert set(st) == {"L06", "L12", "teacher_L12", "raw_projected", "raw_unprojected"}
    val_ids = [f"probe_val-{i}" for i in range(4)]
    for tag in ("L06", "L12"):
        s = st[tag]
        assert {"pca", "generated_linear", "permuted_linear", "h1"} <= set(s)
        assert s["pca"]["input_dim"] == 21 * 4
        assert 0.0 < s["pca"]["explained_variance_share"] <= 1.0 + 1e-9
        assert 0.0 < s["pca"]["explained_variance_share_val"] <= 1.0 + 1e-9
        g, p = s["generated_linear"], s["permuted_linear"]
        assert g["budget"]["n_params"] == (6 + 4 + 81) * 9 + 9
        assert p["val_brier_mean"] == pytest.approx(np.nanmean(p["per_puzzle"])) and "tune_brier_mean" in p
        diffs = np.subtract(p["per_puzzle"], g["per_puzzle"])
        assert s["h1"]["mean_diff"] == pytest.approx(np.nanmean(diffs))
        assert s["h1"]["relative_improvement"] == pytest.approx(np.nanmean(diffs) / np.nanmean(p["per_puzzle"]))
        f = json.loads((out / f"wholelayer_h1_diffs_{tag}.json").read_text(encoding="utf-8"))
        assert f["ids"] == val_ids and np.allclose(f["diffs"], diffs)
    t = st["teacher_L12"]
    assert {"pca", "teacher_linear", "teacher_minus_generated"} <= set(t)
    tg = t["teacher_minus_generated"]
    exp = np.subtract(t["teacher_linear"]["per_puzzle"], st["L12"]["generated_linear"]["per_puzzle"])
    assert tg["ids"] == val_ids and np.allclose(tg["diffs"], exp) and tg["mean_diff"] == pytest.approx(np.nanmean(exp))
    k_raw = st["raw_projected"]["pca"]["k"]
    assert k_raw == 6 and st["raw_projected"]["linear"]["budget"]["n_params"] == (k_raw + 81) * 9 + 9
    assert "explained_variance_share_val" in st["raw_projected"]["pca"]
    assert st["raw_unprojected"]["linear"]["budget"]["n_params"] == (210 + 81) * 9 + 9
    assert set(r["seconds"]) == set(st)
    ref = r["references"]
    assert ref["available"] is True and ref["val_ids_match"] is True
    assert ref["rows"] == {"L06_linear": 0.20, "L12_linear": 0.21, "L06_permuted_linear": 0.23,
                           "L12_permuted_linear": 0.24, "surface_linear": 0.22, "raw_linear": 0.19}
    for tag, b in (("L06", 0.20), ("L12", 0.21)):
        assert r["whole_minus_per_cell"][tag] == pytest.approx(st[tag]["generated_linear"]["val_brier_mean"] - b)
    report = (out / "wholelayer_report.md").read_text(encoding="utf-8")
    assert "Non-confirmatory" in report and "relative improvement" in report and "unprojected" in report
    assert "per-cell" in report and "surface" in report
    assert not list(out.glob("*.tmp"))
    with pytest.raises(SystemExit):
        mod.main()


def test_e3_wholelayer_missing_probes_json(tmp_path, monkeypatch):
    mod, runs, out = _setup(tmp_path, monkeypatch, None)
    monkeypatch.setattr(mod, "STAGES", mod.STAGES[:1])  # L06 only
    mod.main()
    r = json.loads((out / "wholelayer.json").read_text(encoding="utf-8"))
    assert r["references"]["available"] is False and r["whole_minus_per_cell"]["L06"] is None
    assert "n/a" in (out / "wholelayer_report.md").read_text(encoding="utf-8")


def test_relative_improvement_zero_denominator():
    mod = _load()
    d = mod._diff([0.0, 0.0], [0.0, 0.0], ["a", "b"], "q")
    assert d["relative_improvement"] is None and d["mean_diff"] == 0.0


def test_e3_wholelayer_resume_skips_finished_stages(tmp_path, monkeypatch):
    mod, runs, out = _setup(tmp_path, monkeypatch, PROBES)
    full = mod.STAGES
    monkeypatch.setattr(mod, "STAGES", full[:1])
    mod.main()
    monkeypatch.setattr(mod, "STAGES", full[:2])
    monkeypatch.setattr(mod.sys, "argv", ["e3_wholelayer.py", "--resume"])
    real_fit = wholelayer.fit_cell_pca
    calls = []
    monkeypatch.setattr(wholelayer, "fit_cell_pca", lambda *a, **k: calls.append(1) or real_fit(*a, **k))
    mod.main()
    assert len(calls) == 1  # only L12 ran
    r = json.loads((out / "wholelayer.json").read_text(encoding="utf-8"))
    assert set(r["stages"]) == {"L06", "L12"}


@pytest.mark.parametrize("change", ["val_ids", "budget", "commit", "dirty"])
def test_e3_wholelayer_resume_mismatch_exits(tmp_path, monkeypatch, change):
    mod, runs, out = _setup(tmp_path, monkeypatch, None)
    monkeypatch.setattr(mod, "STAGES", mod.STAGES[:1])
    mod.main()
    monkeypatch.setattr(mod.sys, "argv", ["e3_wholelayer.py", "--resume"])
    mod.main()  # unchanged: accepted
    if change == "val_ids":
        (runs / "probe_val" / "ids.json").write_text(json.dumps([f"other-{i}" for i in range(4)]))
    elif change == "budget":
        monkeypatch.setattr(mod, "KW", dict(epochs=2, min_steps=1))
    elif change == "commit":
        monkeypatch.setattr(mod, "code_state", lambda: {**CODE, "commit": "def"})
    else:
        monkeypatch.setattr(mod, "code_state", lambda: {**CODE, "dirty": True, "diff_sha256": "x"})
    with pytest.raises(SystemExit, match="resume"):
        mod.main()


def test_e3_wholelayer_force_and_resume_rejected(tmp_path, monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod, "OUT", tmp_path)
    monkeypatch.setattr(mod.sys, "argv", ["e3_wholelayer.py", "--force", "--resume"])
    with pytest.raises(SystemExit, match="--force"):
        mod.main()


def test_pca_info_moved_verbatim():
    assert _load()._pca_info is wholelayer.pca_info  # the script re-exports the moved function


def test_cell_pca_features_matches_whole_layer_path():
    s_tr, e_tr = _toy_states(seed=0)
    s_va, e_va = _toy_states(n=5, seed=1)
    s_sc, e_sc = _toy_states(n=4, seed=2)
    pca, info, f_tr, f_va, f_sc = wholelayer.cell_pca_features(s_tr, s_va, e_tr, e_va, 8)
    ref = fit_cell_pca(s_tr, e_tr, 8)
    assert all(np.array_equal(pca[k], ref[k]) for k in ("mean", "components", "scale"))
    assert info == wholelayer.pca_info(ref, 21 * 3, cell_variance_share(s_va, e_va, ref))
    assert np.array_equal(f_tr, whole_layer_features(s_tr, ref)) and np.array_equal(f_va, whole_layer_features(s_va, ref))
    assert f_sc is None and "explained_variance_share_score" not in info
    _, info2, _, _, f_sc = wholelayer.cell_pca_features(s_tr, s_va, e_tr, e_va, 8, s_sc=s_sc, empty_sc=e_sc)
    assert np.array_equal(f_sc, whole_layer_features(s_sc, ref))
    assert info2 == {**info, "explained_variance_share_score": cell_variance_share(s_sc, e_sc, ref)}
    with pytest.raises(ValueError):
        wholelayer.cell_pca_features(s_tr, s_va, e_tr, e_va, 8, s_sc=s_sc)


def test_raw_pca_features_matches_raw_projected_path():
    rng = np.random.default_rng(0)
    p_tr, p_va, p_sc = (rng.integers(0, 10, (n, 81)) for n in (12, 5, 4))
    e_tr, e_va = p_tr == 0, p_va == 0
    pca, info, f_tr, f_va, f_sc = wholelayer.raw_pca_features(p_tr, p_va, e_tr, e_va, 8, p_sc=p_sc)
    rows = raw_features(p_tr)[e_tr]
    ref = fit_pca(rows, min(8, *rows.shape))
    assert np.array_equal(pca["components"], ref["components"])
    assert info == wholelayer.pca_info(ref, 210, variance_share(raw_features(p_va)[e_va], ref))
    assert np.array_equal(f_tr, raw_projected_features(p_tr, ref)) and np.array_equal(f_sc, raw_projected_features(p_sc, ref))
    assert wholelayer.raw_pca_features(p_tr, p_va, e_tr, e_va, 8)[4] is None


def test_first_n_slices_training_arrays():
    rng = np.random.default_rng(0)
    tr = {"ids": list("abcd"), "puzzles": rng.integers(0, 10, (4, 81)), "mask": rng.integers(0, 2, (4, 81, 9)),
          "empty": rng.random((4, 81)) < 0.5, "depth": np.zeros((4, 81))}
    sub = first_n(tr, 2)
    assert set(sub) == {"puzzles", "mask", "empty"}
    assert all(np.array_equal(sub[k], tr[k][:2]) for k in sub)
    sub = first_n({**tr, "rep": rng.standard_normal((4, 81, 3))}, 3)
    assert set(sub) == {"puzzles", "mask", "empty", "rep"} and len(sub["rep"]) == 3
