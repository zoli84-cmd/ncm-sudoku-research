import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import torch

from ncm_sudoku.wholelayer import fit_pca, project, raw_whole, raw_whole_features, whole_layer_features
from test_e3_scripts import FAST, _toy_runs

ROOT = Path(__file__).resolve().parents[1]


def _low_rank(n=60, d=40, r=5, seed=0):
    rng = np.random.default_rng(seed)
    return (rng.standard_normal((n, r)) @ rng.standard_normal((r, d)) + 3.0).astype(np.float32)


def test_fit_pca_recovers_low_rank_structure():
    x = _low_rank()
    pca = fit_pca(x, k=8)
    assert pca["components"].shape == (8, 40) and pca["mean"].shape == (40,)
    assert pca["explained_variance_share"] == pytest.approx(1.0, abs=1e-9)
    z = project(x, pca)
    assert z.shape == (60, 8) and z.dtype == np.float32
    recon = z.astype(np.float64) @ pca["components"] + pca["mean"]
    assert np.allclose(recon, x, atol=1e-4)
    assert np.allclose(z[:, 5:], 0.0, atol=1e-4)  # rank 5: the rest carries no variance


def test_fit_pca_partial_share_and_padding():
    rng = np.random.default_rng(1)
    x = rng.standard_normal((10, 30))
    share = fit_pca(x, k=3)["explained_variance_share"]
    assert 0.0 < share < 1.0
    pca = fit_pca(x, k=16)  # more components than samples: zero-padded to width k
    assert pca["components"].shape == (16, 30) and pca["n_components_fitted"] == 10
    assert np.all(pca["components"][10:] == 0.0)
    assert project(x, pca).shape == (10, 16)


def test_fit_pca_deterministic_sign():
    x = _low_rank(seed=2)
    a, b = fit_pca(x, k=5), fit_pca(x.copy(), k=5)
    assert np.array_equal(a["components"], b["components"])
    comp = a["components"]
    idx = np.abs(comp).argmax(axis=1)
    assert np.all(comp[np.arange(5), idx] > 0)
    flipped = fit_pca(-x, k=5)["components"]  # sign convention survives a sign flip of the data
    assert np.allclose(np.abs(flipped), np.abs(comp), atol=1e-8)
    assert np.all(flipped[np.arange(5), np.abs(flipped).argmax(axis=1)] > 0)


def test_whole_layer_features_layout():
    rng = np.random.default_rng(0)
    states = rng.standard_normal((6, 81, 4)).astype(np.float32)
    pca = fit_pca(states.reshape(6, -1), k=3)
    f = whole_layer_features(states, pca)
    assert f.shape == (6, 81, 3 + 4) and f.dtype == np.float32
    glob = project(states.reshape(6, -1), pca)
    assert np.allclose(f[:, :, :3], glob[:, None, :])
    assert np.all(f[:, :1, :3] == f[:, :, :3])  # same global part in every cell
    assert np.array_equal(f[:, :, 3:], states)


def test_raw_whole_one_hot():
    p = np.zeros((2, 81), np.int64)
    p[0, 0], p[0, 80], p[1, 40] = 5, 9, 1
    r = raw_whole(p)
    assert r.shape == (2, 810) and r.dtype == np.float32
    assert np.all(r.reshape(2, 81, 10).sum(axis=2) == 1)
    assert r[0, 5] == 1 and r[0, 80 * 10 + 9] == 1 and r[1, 40 * 10 + 1] == 1 and r[1, 0] == 1


def test_raw_whole_features_widths():
    rng = np.random.default_rng(0)
    p = rng.integers(0, 10, (300, 81))
    un = raw_whole_features(p, None)
    assert un.shape == (300, 81, 810 + 10)
    assert np.array_equal(un[:, 7, :810], raw_whole(p)) and np.array_equal(un[:, 7, 810:], np.eye(10)[p[:, 7]])
    pca = fit_pca(raw_whole(p), k=256)
    pr = raw_whole_features(p, pca)
    assert pr.shape == (300, 81, 256 + 10) and pr.dtype == np.float32
    assert np.allclose(pr[:, 3, :256], project(raw_whole(p), pca))
    assert np.array_equal(pr[:, :, 256:], np.eye(10, dtype=np.float32)[p])


def _load():
    spec = importlib.util.spec_from_file_location("e3_wholelayer", ROOT / "scripts" / "e3_wholelayer.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_e3_wholelayer_guard(tmp_path, monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod, "OUT", tmp_path)
    (tmp_path / "wholelayer.json").write_text("{}")
    with pytest.raises(SystemExit):
        mod.guard(force=False)
    mod.guard(force=True)


def test_e3_wholelayer_end_to_end(tmp_path, monkeypatch):
    runs, out = tmp_path / "runs", tmp_path / "exp"
    _toy_runs(runs)
    mod = _load()
    for k, v in dict(RUNS=runs, OUT=out, KW=FAST, K=6).items():
        monkeypatch.setattr(mod, k, v)
    monkeypatch.setattr(mod, "environment_record", lambda: {"deterministic": torch.are_deterministic_algorithms_enabled()})
    monkeypatch.setattr(mod, "code_state", lambda: {"commit": "abc", "dirty": False, "diff_sha256": None})
    monkeypatch.setattr(mod.sys, "argv", ["e3_wholelayer.py"])
    torch.use_deterministic_algorithms(False)
    mod.main()
    r = json.loads((out / "wholelayer.json").read_text(encoding="utf-8"))
    assert "non-confirmatory" in r["note"] and r["environment"]["deterministic"] is True
    assert r["code"]["commit"] == "abc" and r["n_train"] == 8 and r["n_val"] == 4 and r["k"] == 6
    st = r["stages"]
    assert set(st) == {"L06", "L12", "teacher_L12", "raw_projected", "raw_unprojected"}
    val_ids = [f"probe_val-{i}" for i in range(4)]
    for tag in ("L06", "L12"):
        s = st[tag]
        assert {"pca", "generated_linear", "permuted_linear", "h1"} <= set(s)
        assert 0.0 < s["pca"]["explained_variance_share"] <= 1.0 + 1e-9
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
    assert st["raw_projected"]["linear"]["budget"]["n_params"] == (6 + 10 + 81) * 9 + 9
    assert "explained_variance_share" in st["raw_projected"]["pca"]
    assert st["raw_unprojected"]["linear"]["budget"]["n_params"] == (810 + 10 + 81) * 9 + 9
    assert set(r["seconds"]) == set(st)
    report = (out / "wholelayer_report.md").read_text(encoding="utf-8")
    assert "Non-confirmatory" in report and "relative improvement" in report and "unprojected" in report
    with pytest.raises(SystemExit):
        mod.main()
