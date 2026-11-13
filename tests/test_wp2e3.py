import dataclasses
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
import torch

from ncm_sudoku import wp2e3
from ncm_sudoku.e3controls import permute_labels, random_features
from ncm_sudoku.e3data import labels, load_level, save_subset
from ncm_sudoku.probes import GRID, SEEDS, build_inputs
from ncm_sudoku.symmetry import apply_symmetry, random_symmetry
from ncm_sudoku.wholelayer import whole_layer_features
from ncm_sudoku.wp2 import file_sha256
from sudoku_cases import P, S
from test_e3_scripts import FAST, GOLDEN, _load, _toy_runs

SUMMARY_KEYS = ("config", "val_brier_mean", "tune_brier_mean", "per_puzzle", "budget")


def _toy_score(root: Path, n: int, seed: int) -> None:
    """A score set of n new symmetric images of P with random level arrays (dim 4)."""
    rng = np.random.default_rng(seed)
    syms = [random_symmetry(rng) for _ in range(n)]
    pz = np.stack([apply_symmetry(P, s) for s in syms])
    sol = np.stack([apply_symmetry(S, s) for s in syms])
    save_subset(root, "score", [f"score-{i}" for i in range(n)], pz, sol, {"solve": np.ones(n, bool)}, labels(pz))
    for lv in range(1, 13):
        np.save(root / "score" / f"L{lv:02d}.npy", rng.standard_normal((n, 81, 4)).astype(np.float32))
    for lv in (2, 6, 12):
        np.save(root / "score" / f"T{lv:02d}.npy", rng.standard_normal((n, 81, 4)).astype(np.float32))


def _sets(tmp: Path, score_n: int | None = None) -> wp2e3.Sets:
    runs, score_root = tmp / "runs", tmp / "e3data"
    _toy_runs(runs)
    if score_n is None:  # dry-run shape: score = PROBE-VAL
        shutil.copytree(runs / "probe_val", score_root / "score")
    else:
        _toy_score(score_root, score_n, 5)
    return wp2e3.load_sets(runs, score_root, tmp / "e3")


def _stored(res: dict, files: dict) -> dict:
    """What Task 9 rebuilds from a verified per-stage checkpoint (JSON round trip)."""
    return json.loads(json.dumps({"summary": res["summary"], "files": files, "in_dims": res["in_dims"]}))


def _run(sets, names, stored=None) -> tuple[dict, dict, dict]:
    stored = {} if stored is None else stored
    res, files = {}, {}
    for name, fn in wp2e3.STAGES:
        if name in names:
            res[name] = fn(sets, FAST, stored)
            files[name] = wp2e3.save_stage(sets.out, name, res[name])
            stored[name] = _stored(res[name], files[name])
    return res, stored, files


@pytest.fixture(scope="module")
def full(tmp_path_factory):
    """Every stage once, in order, on the toy runs with score = PROBE-VAL (K 8, SIZES (4, 8))."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(wp2e3, "K", 8)
        mp.setattr(wp2e3, "SIZES", (4, 8))
        sets = _sets(tmp_path_factory.mktemp("full"))
        res, stored, files = _run(sets, [n for n, _ in wp2e3.STAGES])
    return sets, res, stored, files


@pytest.fixture
def small(monkeypatch):
    monkeypatch.setattr(wp2e3, "K", 8)
    monkeypatch.setattr(wp2e3, "SIZES", (4, 8))


def test_stage_names_and_fits_exact():
    assert [n for n, _ in wp2e3.STAGES] == ["wl_L06", "wl_L12", "wl_teacher_L12", "wl_L02", "raw_projected",
        "raw_unprojected", "pc_L02", "pc_L06", "pc_L12", "controls", "unit_digit", "training_size",
        "wl_L06_controls", "wl_teacher_L06", "wl_training_size"]
    sizes = ("n125", "n250", "n500", "n1000", "n2000")
    assert wp2e3.STAGE_FITS == {
        "wl_L06": ("generated", "permuted"), "wl_L12": ("generated", "permuted"), "wl_teacher_L12": ("teacher",),
        "wl_L02": ("generated", "permuted"), "raw_projected": ("linear",), "raw_unprojected": ("linear",),
        "pc_L02": ("linear", "mlp", "permuted"), "pc_L06": ("linear", "mlp"), "pc_L12": ("linear", "mlp", "permuted"),
        "controls": ("raw_linear", "raw_mlp", "peer_counts_linear", "rule", "surface_linear", "permuted_linear",
                     "random_linear", "label_permuted_linear", "teacher_L02_linear", "teacher_L06_linear",
                     "teacher_L12_linear", "marginal"),
        "unit_digit": ("generated", "raw"), "training_size": sizes,
        "wl_L06_controls": ("random", "label_permuted"), "wl_teacher_L06": ("teacher",), "wl_training_size": sizes}
    assert wp2e3.SIZES == (125, 250, 500, 1000, 2000) and wp2e3.K == 256


def _fits_of(stage: str) -> tuple:
    if stage in ("training_size", "wl_training_size"):
        return ("n4", "n8")
    return wp2e3.STAGE_FITS[stage]


def test_every_stage_summary_has_its_fits_and_fields(full):
    sets, res, _, _ = full
    construction = {"wl_L06": "whole_layer", "wl_L12": "whole_layer", "wl_teacher_L12": "whole_layer",
                    "wl_L02": "whole_layer", "raw_projected": "input", "raw_unprojected": "input",
                    "pc_L02": "per_cell", "pc_L06": "per_cell", "pc_L12": "per_cell", "training_size": "per_cell",
                    "wl_L06_controls": "whole_layer", "wl_teacher_L06": "whole_layer", "wl_training_size": "whole_layer"}
    for stage, r in res.items():
        for fit in _fits_of(stage):
            s = r["summary"][fit]
            assert s["n_score"] == 4
            if stage in construction:
                assert s["construction"] == construction[stage], (stage, fit)
            assert s["rows"] == ("reused" if s.get("reused") else "unit" if stage == "unit_digit" else "cell")
    c = res["controls"]["summary"]
    assert {k: c[k]["construction"] for k in ("raw_mlp", "rule", "marginal", "permuted_linear", "teacher_L06_linear")} \
        == {"raw_mlp": "input", "rule": "input", "marginal": "input", "permuted_linear": "per_cell",
            "teacher_L06_linear": "per_cell"}
    u = res["unit_digit"]["summary"]
    assert u["generated"]["construction"] == "per_cell" and u["raw"]["construction"] == "input"


def test_wl_stage_with_score_equal_val_matches_e3_wholelayer(full, tmp_path, monkeypatch):
    sets, res, _, _ = full
    mod = _load("e3_wholelayer")
    for k, v in dict(RUNS=sets.probe_runs, OUT=tmp_path, KW=FAST, K=8).items():
        monkeypatch.setattr(mod, k, v)
    tr, va = mod._subset("probe_train"), mod._subset("probe_val")
    ref = mod._level(6)(tr, va, {})
    got = res["wl_L06"]["summary"]
    assert np.array_equal(got["generated"]["per_puzzle"], ref["generated_linear"]["per_puzzle"], equal_nan=True)
    assert got["permuted"]["config"] == ref["permuted_linear"]["config"]
    assert np.array_equal(got["permuted"]["per_puzzle"], ref["permuted_linear"]["per_puzzle"], equal_nan=True)
    pca = dict(got["pca"])
    assert pca.pop("explained_variance_share_score") == pytest.approx(pca["explained_variance_share_val"])
    assert pca == ref["pca"]


def _same(got: dict, ref: dict, keys=SUMMARY_KEYS) -> None:
    for k in keys:
        if k in ref:
            assert json.loads(json.dumps(got[k])) == ref[k], k


def test_d64_d67_stages_with_score_equal_val_match_golden(full):
    """With score = PROBE-VAL every pre-lock stage equals the D64/D67 script output
    (tests/golden/e3_scripts_toy.json, same toy runs, FAST, K 8, SIZES (4, 8))."""
    _, res, _, _ = full
    g = json.loads(GOLDEN.read_text(encoding="utf-8"))
    wl, pr = g["e3_wholelayer"], g["e3_probes"]
    s = {k: v["summary"] for k, v in res.items()}
    for tag in ("L06", "L12"):
        _same(s[f"wl_{tag}"]["generated"], wl[tag]["generated_linear"])
        _same(s[f"wl_{tag}"]["permuted"], wl[tag]["permuted_linear"])
    _same(s["wl_teacher_L12"]["teacher"], wl["teacher_L12"]["teacher_linear"])
    _same(s["raw_projected"]["linear"], wl["raw_projected"]["linear"])
    _same(s["raw_unprojected"]["linear"], wl["raw_unprojected"]["linear"])
    _same(s["raw_projected"]["pca"], wl["raw_projected"]["pca"], tuple(wl["raw_projected"]["pca"]))
    for lv in ("02", "06", "12"):
        _same(s[f"pc_L{lv}"]["linear"], pr[f"L{lv}_linear"])
        _same(s[f"pc_L{lv}"]["mlp"], pr[f"L{lv}_mlp"])
    for lv in ("02", "12"):
        _same(s[f"pc_L{lv}"]["permuted"], pr[f"L{lv}_permuted_linear"])
    for name, ref in pr["controls"].items():
        _same(s["controls"][name], ref)
    for name, ref in pr["unit_digit"].items():
        _same(s["unit_digit"][name], ref, tuple(ref))
    _same(s["training_size"]["n4"], pr["training_size"]["4"])
    _same(s["training_size"]["n8"], pr["training_size"]["8"])
    assert s["training_size"]["n8"]["reused"] is True and s["training_size"]["n8"]["n_puzzles"] == 8


def test_score_set_differs_from_val_scores_on_score(small, tmp_path):
    sets = _sets(tmp_path, score_n=3)
    res = dict(wp2e3.STAGES)["wl_L06"](sets, FAST, {})
    assert len(res["summary"]["generated"]["per_puzzle"]) == 3 and res["summary"]["generated"]["n_score"] == 3
    assert len(res["fits"]["permuted"]["preds"]) == int(sets.score["empty"].sum())
    u = dict(wp2e3.STAGES)["unit_digit"](sets, FAST, {})
    assert len(u["summary"]["raw"]["per_puzzle"]) == 3 and len(u["fits"]["generated"]["preds"]) == 3 * 27


def test_load_sets_rejects_score_overlapping_train(tmp_path):
    runs = tmp_path / "runs"
    _toy_runs(runs)
    shutil.copytree(runs / "probe_train", tmp_path / "e3data" / "score")
    with pytest.raises(ValueError, match="overlap"):
        wp2e3.load_sets(runs, tmp_path / "e3data", tmp_path / "e3")


def test_save_and_load_probe_reproduces_preds(full):
    sets, res, _, _ = full
    out = sets.out
    probes, pca, meta = wp2e3.load_probe(out, "wl_L12", "generated")
    assert len(probes) == 3 and meta["kind"] == "linear" and meta["in_dim"] == 8 + 4 + 81
    score_l12 = load_level(sets.score_root, "score", 12)
    X = build_inputs(whole_layer_features(score_l12, pca), sets.score["empty"])[0]
    npz = np.load(out / "preds" / "wl_L12__generated.npz")
    assert sorted(npz.files) == ["mean", "seed0", "seed1", "seed2"] and npz["mean"].dtype == np.float32
    with torch.no_grad():
        per = [p(X).numpy() for p in probes]
    assert np.allclose(np.mean(per, axis=0), npz["mean"])
    assert all(np.allclose(per[i], npz[f"seed{i}"]) for i in range(3))
    probes, pca, meta = wp2e3.load_probe(out, "pc_L06", "mlp")
    assert pca is None and meta["kind"] == "mlp" and meta["rows"] == "cell"


def test_training_size_reuses_full_fit_from_stored(full, small):
    sets, _, stored, _ = full
    fn = dict(wp2e3.STAGES)["training_size"]
    res = fn(sets, FAST, {"pc_L06": stored["pc_L06"]})  # as after a resume
    n8 = res["summary"]["n8"]
    assert n8["reused"] is True and n8["reused_from"] == "pc_L06.linear"
    assert n8["per_puzzle"] == stored["pc_L06"]["summary"]["linear"]["per_puzzle"]
    assert res["summary"]["n4"]["reused"] is False and res["summary"]["n4"]["n_puzzles"] == 4
    assert set(res["fits"]) == set(res["budget"]) == {"n4"}
    with pytest.raises(ValueError, match="pc_L06"):
        fn(sets, FAST, {})


def test_wl_training_size_reuses_wl_L06_and_keeps_full_pca(full, small, monkeypatch):
    sets, res, stored, _ = full
    r = res["wl_training_size"]
    for k in ("mean", "components", "scale"):
        assert np.array_equal(r["pcas"]["n4"][k], res["wl_L06"]["pcas"]["generated"][k])
    n8 = r["summary"]["n8"]
    assert n8["reused"] is True and n8["reused_from"] == "wl_L06.generated"
    assert n8["per_puzzle"] == stored["wl_L06"]["summary"]["generated"]["per_puzzle"]
    seen = []
    real = wp2e3.fit_cells
    monkeypatch.setattr(wp2e3, "fit_cells", lambda f_tr, f_va, tr, *a, **k: seen.append(
        (len(f_tr), len(tr["puzzles"]), np.array_equal(tr["mask"], sets.train["mask"][:4]))) or real(f_tr, f_va, tr, *a, **k))
    again = dict(wp2e3.STAGES)["wl_training_size"](sets, FAST, {"wl_L06": stored["wl_L06"]})
    assert seen == [(4, 4, True)]
    assert again["summary"]["n4"]["per_puzzle"] == json.loads(json.dumps(r["summary"]["n4"]["per_puzzle"]))
    with pytest.raises(ValueError, match="wl_L06"):
        dict(wp2e3.STAGES)["wl_training_size"](sets, FAST, {})


def _tampered(sets, stored, tmp_path, change_sha: bool):
    out = tmp_path / "e3"
    shutil.copytree(sets.out, out)
    path = out / "models" / "wl_L06__generated_pca.pt"
    pca = torch.load(path, weights_only=True)
    pca["mean"] = pca["mean"] + 1.0
    torch.save(pca, path)
    st = json.loads(json.dumps(stored))
    if change_sha:
        st["wl_L06"]["files"]["generated"]["models/wl_L06__generated_pca.pt"] = file_sha256(path)
    return dataclasses.replace(sets, out=out), st


@pytest.mark.parametrize("change_sha", [False, True])
def test_wl_stages_refuse_a_different_saved_pca(full, small, tmp_path, change_sha):
    sets, _, stored, _ = full
    sets2, st = _tampered(sets, stored, tmp_path, change_sha)
    for stage in ("wl_L06_controls", "wl_training_size"):
        with pytest.raises(ValueError, match="PCA|SHA-256"):
            dict(wp2e3.STAGES)[stage](sets2, FAST, {"wl_L06": st["wl_L06"]})


def test_wl_controls_size_matched_and_label_permuted(full, small, monkeypatch):
    sets, res, stored, _ = full
    r = res["wl_L06_controls"]
    assert r["in_dims"]["random"] == stored["wl_L06"]["in_dims"]["generated"] == 8 + 4 + 81
    assert r["in_dims"]["label_permuted"] == 8 + 4 + 81
    assert r["summary"]["random"]["construction"] == "whole_layer"
    assert r["summary"]["label_permuted"]["construction"] == "whole_layer"
    assert r["summary"]["pca_matches_saved"] is True
    seen = {}
    real = wp2e3.fit_cells

    def spy(f_tr, f_va, tr, va, kind, mask_tr=None, **k):
        seen["random" if "random" not in seen else "label_permuted"] = (f_tr, f_va, k["f_score"], mask_tr)
        return real(f_tr, f_va, tr, va, kind, mask_tr=mask_tr, **k)

    monkeypatch.setattr(wp2e3, "fit_cells", spy)
    dict(wp2e3.STAGES)["wl_L06_controls"](sets, FAST, {"wl_L06": stored["wl_L06"]})
    rnd = random_features(8 + 4, seed=0, dim=12)
    f_tr, f_va, f_sc, mask = seen["random"]
    assert np.array_equal(f_tr, rnd[:8]) and np.array_equal(f_va, rnd[8:]) and np.array_equal(f_sc, rnd[8:])
    assert mask is None
    f_tr, _, _, mask = seen["label_permuted"]
    assert f_tr.shape == (8, 81, 12)
    assert np.array_equal(mask, permute_labels(sets.train["mask"], sets.train["empty"], 0))


def test_wl_controls_rejects_a_different_input_width(full, small):
    sets, _, stored, _ = full
    st = json.loads(json.dumps(stored["wl_L06"]))
    st["in_dims"]["generated"] = 999
    with pytest.raises(ValueError, match="width"):
        dict(wp2e3.STAGES)["wl_L06_controls"](sets, FAST, {"wl_L06": st})


def test_budget_table_has_30_entries_per_trained_fit(full):
    _, res, _, _ = full
    grid = {(wd, lr, s) for wd, lr in GRID for s in SEEDS}
    for stage, r in res.items():
        trained = {f for f in _fits_of(stage) if f not in ("rule", "marginal") and not r["summary"][f].get("reused")}
        assert set(r["budget"]) == trained, stage
        for fit, table in r["budget"].items():
            assert len(table) == 30 and {(e["wd"], e["lr"], e["seed"]) for e in table} == grid
            assert sum(e["selected"] for e in table) == 3
            cfg = r["summary"][fit]["config"]
            assert all([e["wd"], e["lr"]] == list(cfg) for e in table if e["selected"])
            assert set(table[0]) == {"wd", "lr", "seed", "best_epoch", "epochs_run", "n_steps", "hit_cap",
                                     "n_params", "selected"}
    json.dumps({s: r["budget"] for s, r in res.items()})  # JSON-ready


def test_save_stage_rule_marginal_and_reused(full):
    sets, _, stored, files = full
    out = sets.out
    for fit in ("rule", "marginal"):
        assert np.load(out / "preds" / f"controls__{fit}.npz").files == ["mean"]
        assert not list((out / "models").glob(f"controls__{fit}*.pt"))
        assert set(files["controls"][fit]) == {f"preds/controls__{fit}.npz", f"models/controls__{fit}.json"}
    meta = json.loads((out / "models" / "controls__marginal.json").read_text(encoding="utf-8"))
    assert np.asarray(meta["probs"]).shape == (81, 9) and meta["kind"] == "marginal"
    assert files["training_size"]["n8"] == files["pc_L06"]["linear"]
    assert files["wl_training_size"]["n8"] == files["wl_L06"]["generated"]
    assert not list(out.rglob("training_size__n8*")) and not list(out.rglob("wl_training_size__n8*"))
    assert set(files["wl_L06"]["generated"]) == {
        "preds/wl_L06__generated.npz", "models/wl_L06__generated.json", "models/wl_L06__generated_pca.pt",
        *(f"models/wl_L06__generated_seed{s}.pt" for s in SEEDS)}
    for name, sha in files["wl_L06"]["generated"].items():
        assert file_sha256(out / name) == sha
    assert len(np.load(out / "preds" / "unit_digit__generated.npz")["mean"]) == 4 * 27
    assert not list(out.rglob("*.tmp*"))
