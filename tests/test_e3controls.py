import numpy as np
import pytest
import torch

from ncm_sudoku import e3controls
from ncm_sudoku.e3controls import (
    fit_cells,
    marginal_brier,
    marginal_probs,
    permuted_control,
    random_rows,
    permute_labels,
    permute_puzzles,
    random_features,
    roc_auc,
    run_controls,
    run_unit_digit,
    unit_digit_labels,
    unit_metrics,
    unit_readout,
)
from ncm_sudoku.e3data import labels, peer_counts
from ncm_sudoku.grid import UNITS
from ncm_sudoku.probes import brier_per_puzzle, build_inputs, fit_selected
from sudoku_cases import P

FAST = dict(epochs=1, min_steps=1)


def test_permuted_control_independent_and_eval_unpermuted():
    a = np.arange(10)[:, None, None] * np.ones((10, 81, 2))
    tr, va = permute_puzzles(a, 11), permute_puzzles(a, 12)
    assert not np.array_equal(tr, va)  # independent permutations
    assert all((tr[i] == tr[i, 0, 0]).all() for i in range(10))  # whole grid moved together
    # evaluation helper must score the permuted probe on UNPERMUTED val pairs:
    assert e3controls.EVAL_ON_UNPERMUTED_VAL is True


def test_permute_labels_keeps_multiset():
    m = np.random.default_rng(0).integers(0, 2, (5, 81, 9)).astype(np.uint8)
    e = np.ones((5, 81), bool)
    p = permute_labels(m, e, 0)
    assert sorted(map(tuple, p.reshape(-1, 9))) == sorted(map(tuple, m.reshape(-1, 9)))
    assert not np.array_equal(p, m)


def test_permute_labels_leaves_given_cells():
    m = np.random.default_rng(1).integers(0, 2, (3, 81, 9)).astype(np.uint8)
    e = np.zeros((3, 81), bool)
    e[:, ::2] = True
    p = permute_labels(m, e, 0)
    assert np.array_equal(p[~e], m[~e])


def test_random_features_shape_and_determinism():
    r = random_features(3, seed=0, dim=7)
    assert r.shape == (3, 81, 7) and r.dtype == np.float32
    assert np.array_equal(r, random_features(3, seed=0, dim=7))


def test_marginal_brier_constant_labels_is_zero():
    m = np.ones((4, 81, 9), np.uint8)
    e = np.ones((4, 81), bool)
    assert np.allclose(marginal_brier(m, e, m, e), 0.0)


def test_marginal_brier_half_rate():
    # Train: position bits are 1 in half the puzzles -> p = 0.5; val Brier = 0.25.
    m_tr = np.zeros((2, 81, 9), np.uint8)
    m_tr[0] = 1
    e = np.ones((2, 81), bool)
    out = marginal_brier(m_tr, e, np.ones((3, 81, 9), np.uint8), np.ones((3, 81), bool))
    assert out.shape == (3,) and np.allclose(out, 0.25)


def test_unit_digit_labels_shape_and_definition():
    u = unit_digit_labels(np.asarray([P]))
    assert u.shape == (1, 27, 9)
    p = np.asarray(P)
    row0 = set(p[:9]) - {0}
    assert [d + 1 for d in range(9) if u[0, 0, d]] == sorted(row0)  # unit 0 = row 0: placed digits
    box0 = set(p[UNITS[18]]) - {0}
    assert [d + 1 for d in range(9) if u[0, 18, d]] == sorted(box0)


def test_unit_readout_is_mean_over_unit_cells():
    f = np.arange(2 * 81 * 3, dtype=np.float32).reshape(2, 81, 3)
    r = unit_readout(f)
    assert r.shape == (2, 27, 3)
    assert np.allclose(r[1, 9], f[1, UNITS[9]].mean(axis=0))  # column 0


def test_roc_auc_rank_formula():
    assert roc_auc(np.array([0.1, 0.2, 0.8, 0.9]), np.array([0, 0, 1, 1])) == 1.0
    assert roc_auc(np.array([0.9, 0.8, 0.2, 0.1]), np.array([0, 0, 1, 1])) == 0.0
    assert roc_auc(np.full(4, 0.5), np.array([0, 1, 0, 1])) == 0.5  # ties count half
    # one pos/neg pair tied, one correctly ordered: (1 + 0.5 + 1 + 1) / 4
    assert roc_auc(np.array([0.1, 0.5, 0.5, 0.9]), np.array([0, 0, 1, 1])) == pytest.approx(0.875)
    assert np.isnan(roc_auc(np.array([0.1, 0.2]), np.array([1, 1])))  # missing class


def test_unit_metrics():
    y = np.array([[1, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 0, 0, 0, 0, 0, 0, 0]], dtype=float)
    pred = np.array([[0.9] + [0.1] * 8, [0.9, 0.4] + [0.1] * 7])  # row 1 misses one digit
    out = unit_metrics(pred, y, np.array([0, 0]), 1)
    assert out["exact_match"] == 0.5
    assert out["roc_auc"] == pytest.approx(roc_auc(pred, y))
    assert out["brier_ensemble"] == pytest.approx(((pred - y) ** 2).mean())


def _subset(n, seed, dim=4):
    """Digit-relabelled copies of P (all 30 clues), with their true labels."""
    rng = np.random.default_rng(seed)
    p = np.asarray(P)
    puzzles = np.stack([np.concatenate([[0], rng.permutation(9) + 1])[p] for _ in range(n)])
    lab = labels(puzzles)
    return {
        "puzzles": puzzles,
        "mask": lab["mask"],
        "empty": lab["empty"],
        "rep": rng.standard_normal((n, 81, dim)).astype(np.float32),
        "teacher": {lv: rng.standard_normal((n, 81, dim)).astype(np.float32) for lv in (2, 6, 12)},
    }


CONTROLS = {
    "raw_linear",
    "raw_mlp",
    "peer_counts_linear",
    "rule",
    "surface_linear",
    "permuted_linear",
    "random_linear",
    "label_permuted_linear",
    "teacher_L02_linear",
    "teacher_L06_linear",
    "teacher_L12_linear",
    "marginal",
}


def test_run_controls_outputs():
    tr, va = _subset(4, 0), _subset(3, 1)
    out = run_controls(tr, va, **FAST)
    assert set(out) == CONTROLS
    for name, r in out.items():
        assert len(r["per_puzzle"]) == 3 and isinstance(r["per_puzzle"], list), name
    assert out["rule"]["val_brier_mean"] == 0.0  # exact candidate_mask rule = ceiling
    assert np.isfinite(out["permuted_linear"]["val_brier_mean"])
    assert out["permuted_linear"]["budget"]["n_params"] == (4 + 81) * 9 + 9
    assert len(out["permuted_linear"]["budget"]["selected"]) == 3
    # F1: the headline Brier is the scored (unpermuted PROBE-VAL) value, the tuning value is kept apart
    pl = out["permuted_linear"]
    assert pl["val_brier_mean"] == pytest.approx(np.nanmean(pl["per_puzzle"]))
    assert "tune_brier_mean" in pl


def test_permuted_control_tunes_on_permuted_and_reports_on_unpermuted(monkeypatch):
    tr, va = _subset(4, 0), _subset(3, 1)
    calls = []

    def fake_fit(Xtr, Ytr, Xva, Yva, va_puzzle, n_va, kind, train_va=None, **kw):
        calls.append((Xtr, Xva, train_va))
        return {"config": (0, 1e-3), "val_brier_mean": 0.0, "tune_brier_mean": 0.1, "per_puzzle": np.zeros(n_va),
                "preds": None, "budget": {}}

    monkeypatch.setattr(e3controls, "fit_selected", fake_fit)
    run_controls(tr, va, **FAST)
    perm = [c for c in calls if c[2] is not None]
    assert len(perm) == 1
    Xtr, Xva, train_va = perm[0]
    e = va["empty"]
    rep_va = np.asarray(Xva[:, :4])
    assert np.array_equal(rep_va, va["rep"][e])  # reported on unpermuted val
    assert np.array_equal(np.asarray(train_va[0][:, :4]), permute_puzzles(va["rep"], 12)[e])
    assert np.array_equal(np.asarray(Xtr[:, :4]), permute_puzzles(tr["rep"], 11)[tr["empty"]])


def test_run_controls_rejects_mixed_clue_counts():
    tr, va = _subset(4, 0), _subset(3, 1)
    tr["puzzles"][0, np.nonzero(tr["puzzles"][0])[0][0]] = 0
    with pytest.raises(ValueError):
        run_controls(tr, va, **FAST)


def test_run_unit_digit_outputs():
    tr, va = _subset(4, 0), _subset(3, 1)
    out = run_unit_digit(tr, va, **FAST)
    assert set(out) == {"generated", "raw"}
    for r in out.values():
        assert {"config", "val_brier_mean", "tune_brier_mean", "per_puzzle", "budget", "exact_match", "roc_auc",
                "brier", "brier_ensemble"} <= set(r)
        assert len(r["per_puzzle"]) == 3
        # F5: "brier" is the per-seed-mean Brier (same scale as every other Brier)
        assert r["brier"] == pytest.approx(np.nanmean(r["per_puzzle"]))
        assert r["brier"] == pytest.approx(r["val_brier_mean"])
        assert 0.0 <= r["exact_match"] <= 1.0


# --- WP2 Task 5: three-set fitting (train on PROBE-TRAIN, select on PROBE-VAL, score on the score set) ---


def _with_ids(d, prefix):
    return {**d, "ids": [f"{prefix}{i}" for i in range(len(d["puzzles"]))]}


def _sets():
    return _with_ids(_subset(4, 0), "tr"), _with_ids(_subset(3, 1), "va"), _with_ids(_subset(5, 2), "sc")


def test_fit_cells_score_none_unchanged():
    """Reference built independently of fit_cells: fit_selected on build_inputs rows
    with the train/val masks (the pre-WP2 fit_cells formula)."""
    tr, va, _ = _sets()
    Xtr, _, _ = build_inputs(tr["rep"], tr["empty"])
    Ytr = torch.from_numpy(tr["mask"][tr["empty"]].astype(np.float32))
    Xva, pz_va, _ = build_inputs(va["rep"], va["empty"])
    Yva = torch.from_numpy(va["mask"][va["empty"]].astype(np.float32))
    ref = fit_selected(Xtr, Ytr, Xva, Yva, pz_va.numpy(), len(va["empty"]), "linear", **FAST)
    got = fit_cells(tr["rep"], va["rep"], tr, va, "linear", **FAST)
    assert got["config"] == ref["config"] and np.array_equal(got["per_puzzle"], ref["per_puzzle"], equal_nan=True)
    assert np.array_equal(got["preds"], ref["preds"])


def test_fit_cells_score_equal_val_reproduces_two_set_fit():
    tr, va, _ = _sets()
    a = fit_cells(tr["rep"], va["rep"], tr, va, "linear", **FAST)
    b = fit_cells(tr["rep"], va["rep"], tr, va, "linear", f_score=va["rep"].copy(), score=dict(va), **FAST)
    assert a["config"] == b["config"] and np.array_equal(a["per_puzzle"], b["per_puzzle"], equal_nan=True)
    assert np.array_equal(a["preds"], b["preds"])
    assert a["tune_brier_mean"] == b["tune_brier_mean"]


def test_fit_cells_selects_on_val_scores_on_score(monkeypatch):
    tr, va, sc = _sets()
    captured = {}

    def fake_fit(Xtr, Ytr, Xva, Yva, va_puzzle, n_va, kind, train_va=None, **kw):
        captured.update(features_va=Xva, lab_va=Yva, n_va=n_va, train_va=train_va)
        return {"config": (0, 1e-3), "per_puzzle": np.zeros(n_va)}

    monkeypatch.setattr(e3controls, "fit_selected", fake_fit)
    fit_cells(tr["rep"], va["rep"], tr, va, "linear", f_score=sc["rep"], score=sc, **FAST)
    assert captured["features_va"].shape[0] == sc["empty"].sum()
    assert np.array_equal(np.asarray(captured["features_va"][:, :4]), sc["rep"][sc["empty"]])
    assert np.array_equal(captured["lab_va"].numpy(), sc["mask"][sc["empty"]])
    assert captured["n_va"] == 5
    Xt, Yt, _, n_t = captured["train_va"]
    assert Xt.shape[0] == va["empty"].sum() and n_t == 3
    assert np.array_equal(np.asarray(Xt[:, :4]), va["rep"][va["empty"]])
    assert np.array_equal(Yt.numpy(), va["mask"][va["empty"]])
    # f_tune replaces the selection features; labels stay the true PROBE-VAL labels
    tune = va["rep"] + 1
    fit_cells(tr["rep"], va["rep"], tr, va, "linear", f_tune=tune, f_score=sc["rep"], score=sc, **FAST)
    assert np.array_equal(np.asarray(captured["train_va"][0][:, :4]), tune[va["empty"]])


def test_permuted_control_with_score_scores_unpermuted_score(monkeypatch):
    tr, va, sc = _sets()
    captured = {}

    def fake_fit(Xtr, Ytr, Xva, Yva, va_puzzle, n_va, kind, train_va=None, **kw):
        captured.update(Xtr=Xtr, features_va=Xva, train_va=train_va)
        return {"config": (0, 1e-3), "per_puzzle": np.zeros(n_va)}

    monkeypatch.setattr(e3controls, "fit_selected", fake_fit)
    permuted_control(tr["rep"], va["rep"], tr, va, rep_score=sc["rep"], score=sc, **FAST)
    assert np.array_equal(np.asarray(captured["features_va"][:, :4]), sc["rep"][sc["empty"]])  # unpermuted score
    assert np.array_equal(np.asarray(captured["train_va"][0][:, :4]), permute_puzzles(va["rep"], 12)[va["empty"]])
    assert np.array_equal(np.asarray(captured["Xtr"][:, :4]), permute_puzzles(tr["rep"], 11)[tr["empty"]])


def test_random_rows_new_and_shared_puzzles():
    assert random_rows(8, ["v0", "v1"], ["t0", "t1"]).tolist() == [10, 11]
    assert random_rows(8, ["v0", "v1"], ["v1", "v0"]).tolist() == [9, 8]
    assert random_rows(8, ["v0", "v1"], ["t0", "v1", "t1"]).tolist() == [10, 9, 11]
    with pytest.raises(ValueError):
        random_rows(8, ["v0"], ["t0", "t0"])


def test_random_features_longer_stream_keeps_train_val_prefix():
    """Spec ambiguity 17: appending score rows leaves the train/val rows unchanged."""
    assert np.array_equal(random_features(9, seed=0, dim=6)[:5], random_features(5, seed=0, dim=6))


def test_marginal_probs_matches_marginal_brier():
    tr, va, _ = _sets()
    p = marginal_probs(tr["mask"], tr["empty"])
    assert p.shape == (81, 9)
    e = va["empty"]
    pz, pos = np.nonzero(e)
    assert np.array_equal(brier_per_puzzle(p[pos], va["mask"][e], pz, len(e)),
                          marginal_brier(tr["mask"], tr["empty"], va["mask"], va["empty"]))


def test_run_controls_score_equal_val_matches_two_set():
    tr, va, _ = _sets()
    a = run_controls(tr, va, **FAST)
    b = run_controls(tr, va, score=dict(va), **FAST)
    assert set(a) == set(b) == CONTROLS
    assert all(np.array_equal(a[k]["per_puzzle"], b[k]["per_puzzle"], equal_nan=True) for k in a)
    assert all(a[k]["config"] == b[k]["config"] for k in a)


def test_run_controls_requires_ids_with_score():
    tr, va, sc = _sets()
    del tr["ids"]
    with pytest.raises(ValueError):
        run_controls(tr, va, score=sc, **FAST)


def test_run_controls_rejects_score_overlapping_train():
    tr, va, sc = _sets()
    sc["ids"] = ["tr0"] + sc["ids"][1:]
    with pytest.raises(ValueError):
        run_controls(tr, va, score=sc, **FAST)


def test_marginal_and_rule_scored_on_score_set():
    tr, va, sc = _sets()
    out = run_controls(tr, va, score=sc, **FAST)
    assert set(out) == CONTROLS
    for name, r in out.items():
        assert len(r["per_puzzle"]) == 5, name
    assert out["rule"]["val_brier_mean"] == 0.0
    mb = marginal_brier(tr["mask"], tr["empty"], sc["mask"], sc["empty"])
    assert np.array_equal(out["marginal"]["per_puzzle"], mb)


def test_run_controls_random_features_use_random_rows(monkeypatch):
    tr, va, sc = _sets()
    sc["ids"] = ["va2", "sc0"] + sc["ids"][2:]  # one shared puzzle (val row 2), four new
    calls = []

    def fake_fit(Xtr, Ytr, Xva, Yva, va_puzzle, n_va, kind, train_va=None, **kw):
        calls.append((Xtr, Xva, train_va))
        return {"config": (0, 1e-3), "val_brier_mean": 0.0, "tune_brier_mean": 0.0, "per_puzzle": np.zeros(n_va),
                "budget": {}}

    monkeypatch.setattr(e3controls, "fit_selected", fake_fit)
    run_controls(tr, va, score=sc, **FAST)
    rnd = random_features(4 + 3 + 4, seed=0, dim=4)
    rows = random_rows(4, va["ids"], sc["ids"])
    assert rows.tolist() == [6, 7, 8, 9, 10]
    hit = [c for c in calls if np.array_equal(np.asarray(c[0][:, :4]), rnd[:4][tr["empty"]])]
    assert len(hit) == 1
    _, Xsc, train_va = hit[0]
    assert np.array_equal(np.asarray(Xsc[:, :4]), rnd[rows][sc["empty"]])
    assert np.array_equal(np.asarray(train_va[0][:, :4]), rnd[4:7][va["empty"]])


def test_rule_and_marginal_preds_reproduce_per_puzzle():
    tr, va, sc = _sets()
    fits = {}
    out = run_controls(tr, va, score=sc, fits=fits, **FAST)
    assert set(fits) == CONTROLS
    e = sc["empty"]
    pz, _ = np.nonzero(e)
    y = sc["mask"][e]
    for k in ("rule", "marginal"):
        assert fits[k]["preds"].dtype == np.float32
        assert np.allclose(brier_per_puzzle(fits[k]["preds"], y, pz, 5), out[k]["per_puzzle"], equal_nan=True)
    assert np.array_equal(fits["rule"]["preds"], (peer_counts(sc["puzzles"]) == 0)[e].astype(np.float32))
    assert np.array_equal(fits["marginal"]["probs"], marginal_probs(tr["mask"], tr["empty"]))
    for k in CONTROLS - {"rule", "marginal"}:
        assert np.array_equal(fits[k]["per_puzzle"], out[k]["per_puzzle"], equal_nan=True), k
        assert len(fits[k]["seed_preds"]) == 3 and len(fits[k]["state_dicts"]) == 3


def test_run_unit_digit_with_score_and_fits_collector():
    tr, va, sc = _sets()
    fits = {}
    out = run_unit_digit(tr, va, score=sc, fits=fits, **FAST)
    assert set(fits) == {"generated", "raw"} and len(out["generated"]["per_puzzle"]) == len(sc["puzzles"])
    assert len(out["raw"]["per_puzzle"]) == 5
    y = unit_digit_labels(sc["puzzles"]).reshape(-1, 9).astype(np.float32)
    pz = np.repeat(np.arange(5), 27)
    for k in ("generated", "raw"):
        assert fits[k]["preds"].shape == (5 * 27, 9)
        assert out[k]["exact_match"] == pytest.approx(unit_metrics(fits[k]["preds"], y, pz, 5)["exact_match"])


def test_run_unit_digit_score_equal_val_matches_two_set():
    tr, va, _ = _sets()
    a = run_unit_digit(tr, va, **FAST)
    b = run_unit_digit(tr, va, score=dict(va), **FAST)
    for k in ("generated", "raw"):
        assert a[k]["config"] == b[k]["config"] and a[k]["per_puzzle"] == b[k]["per_puzzle"]
        assert a[k]["exact_match"] == b[k]["exact_match"]
