import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import torch

import ncm_sudoku.e2
import ncm_sudoku.e2p2 as e2p2
import ncm_sudoku.wp2eval as wp2eval
import wp2_fakes
from ncm_sudoku import wp2

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("wp2_evaluate", ROOT / "scripts" / "wp2_evaluate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _restore_determinism():
    prev = torch.are_deterministic_algorithms_enabled()
    yield
    torch.use_deterministic_algorithms(prev)


def _builder(root: Path, mp: pytest.MonkeyPatch):
    """Patches the repo root, freeze/code/environment state and the role data; returns a builder.
    The score set defaults to 24 puzzles (>= 20 nonzero values keep H1 on the bootstrap path)."""
    mp.setattr(wp2, "ROOT", root)
    mp.setattr(wp2, "freeze_state", lambda root=None: dict(wp2_fakes.FROZEN))
    mp.setattr(wp2, "code_state", lambda: dict(wp2_fakes.CODE))
    mp.setattr(wp2, "environment_record", lambda: dict(wp2_fakes.ENV))
    mod = _load()
    mp.setattr(mod, "N_BOOT", 500)

    def build(role="dry", **kw):
        env = wp2_fakes.write_role(root, role, **{"n_score": 24, **kw})
        mp.setattr(wp2, "load_role", lambda r: wp2.RoleData(
            ids=env.e2_ids, puzzles=env.e2_puzzles, solutions=env.e2_puzzles, source="fake"))
        env.mod = mod
        return env

    return build


@pytest.fixture
def setup(tmp_path, monkeypatch):
    return _builder(tmp_path, monkeypatch)


@pytest.fixture(scope="module")
def default(tmp_path_factory):
    """One evaluation of the default synthetic dry role, shared by the read-only tests."""
    prev = torch.are_deterministic_algorithms_enabled()
    with pytest.MonkeyPatch.context() as mp:
        env = _builder(tmp_path_factory.mktemp("default"), mp)()
        env.res = _run(env)
        env.report = (env.exp / "report.md").read_text(encoding="utf-8")
        yield env
    torch.use_deterministic_algorithms(prev)


def _run(env, role="dry") -> dict:
    env.mod.main(["--role", role])
    return json.loads((env.exp / "results.json").read_text(encoding="utf-8"))


def _edit_record(env, runner, **fields):
    p = env.records / f"{runner}.json"
    rec = json.loads(p.read_text(encoding="utf-8"))
    rec.update(fields)
    wp2.atomic_json(p, rec)


def test_wp2_evaluate_end_to_end_synthetic(setup):
    env = setup(n=40, theta2=-0.10, theta1_shift=0.003)
    res = _run(env)
    assert res["role"] == "dry" and res["note"] == wp2.DRY_NOTE
    assert res["primary"]["H2"]["estimate"] == pytest.approx(-0.10, abs=1e-12)
    assert res["primary"]["H2"]["family"]["ci"][1] < 0
    assert {r["row"] for r in res["readings"] if r["hypothesis"] == "H2"} == {"early_sensitivity"}
    assert res["primary"]["H1"]["family"]["level"] == pytest.approx(1 - 0.05 / 3)
    assert res["primary"]["H1"]["estimate"] == pytest.approx(0.003, abs=1e-6)
    assert res["primary"]["H1"]["tost"]["level"] == pytest.approx(1 - 2 * 0.05 / 3)
    assert {r["row"] for r in res["readings"] if r["hypothesis"] == "H1"} == {"h1_small_positive", "probe_beats_null"}
    assert res["secondary"]["theta2_prime"]["tost"]["level"] == pytest.approx(0.90)
    assert res["secondary"]["theta_T"]["tost"]["level"] == pytest.approx(0.90)
    assert set(res["secondary"]["theta1_wl"]) == {"L02", "L12"} and set(res["secondary"]["theta1_pc"]) == {
        "L02", "L06", "L12"}
    assert set(res["secondary"]["raw_minus_generated"]) == {"projected", "unprojected"}
    assert res["secondary"]["raw_minus_generated"]["projected"]["estimate"] < 0
    assert set(res["secondary"]["uniform"]) == {"theta2", "theta_comp", "theta2_prime"}
    assert res["secondary"]["correct_baseline"]["theta2"]["n"] == 40
    assert res["rare_event"]["H2"]["ci95_method"] == "bootstrap"
    assert res["rare_event"]["H3"]["ci95_method"] == "bound" and res["rare_event"]["H3"]["n_nonzero"] == 0
    assert res["auc"]["2-11"]["auc_a"] is None
    assert res["auc"]["6-11"]["covered"] is True and res["auc"]["6-11"]["auc_a"] == pytest.approx(0.0)
    report = (env.exp / "report.md").read_text(encoding="utf-8")
    assert "DRY RUN" in report and "98.33%" in report and "96.67%" in report


def test_wp2_evaluate_records_inputs(default):
    env, res = default, default.res
    assert set(res["records"]) == {"e3_extract", "e3", "equiv", "e2", "e1"}
    assert res["records"]["e2"] == {"status": "valid", "valid": True, "commit": wp2_fakes.TAG, "seconds": 1.5,
                                    "reasons": []}
    e2_json = (env.raw / "e2.json").relative_to(env.root).as_posix()
    assert res["inputs"][e2_json] == wp2.file_sha256(env.raw / "e2.json")
    assert any(k.endswith("preds/wl_L06__generated.npz") for k in res["inputs"])
    assert any(k.endswith("e2/diag/level1__v00.npz") for k in res["inputs"])


def test_wp2_evaluate_refuses_incomplete_records(setup):
    env = setup()
    _edit_record(env, "e2", complete=False)
    with pytest.raises(SystemExit, match=r"e2.*incomplete"):
        env.mod.main(["--role", "dry"])
    assert not (env.exp / "results.json").exists()


def test_wp2_evaluate_refuses_missing_record(setup):
    env = setup()
    (env.records / "equiv.json").unlink()
    with pytest.raises(SystemExit, match="equiv"):
        env.mod.main(["--role", "dry"])


def test_wp2_evaluate_test_role_requires_frozen_and_tag_commits(setup, monkeypatch):
    env = setup(role="test")
    monkeypatch.setattr(wp2, "freeze_state", lambda root=None: {**wp2_fakes.FROZEN, "frozen": False})
    with pytest.raises(SystemExit, match="frozen"):
        env.mod.main(["--role", "test"])
    monkeypatch.setattr(wp2, "freeze_state", lambda root=None: dict(wp2_fakes.FROZEN))
    _edit_record(env, "e1", code={**wp2_fakes.CODE, "commit": "b" * 40}, code_end={**wp2_fakes.CODE, "commit": "b" * 40})
    with pytest.raises(SystemExit, match=r"e1.*not_tag_commit"):
        env.mod.main(["--role", "test"])
    _edit_record(env, "e1", code=dict(wp2_fakes.CODE), code_end=dict(wp2_fakes.CODE))
    res = _run(env, "test")
    assert res["role"] == "test" and res["freeze_state"]["frozen"] is True
    assert "DRY RUN" not in (env.exp / "report.md").read_text(encoding="utf-8")


def test_wp2_evaluate_rejects_restored_worktree_record(setup):
    env = setup()
    _edit_record(env, "e3", code_changed_during_run=True, freeze_end={**wp2_fakes.FROZEN, "frozen": False})
    with pytest.raises(SystemExit, match=r"e3.*freeze_end"):
        env.mod.main(["--role", "dry"])
    assert not (env.exp / "results.json").exists()


def test_wp2_evaluate_e2_identity_failure_blocks_inference(setup, monkeypatch):
    env = setup(identity_failure=True)
    n_e2, calls = env.n, {"interval": 0}
    assert n_e2 != env.n_score
    interval, tost = e2p2.interval, wp2eval.tost

    def guarded_interval(values, *a, **k):
        if len(values) == n_e2:
            pytest.fail("interval called on an E2 puzzle-value vector")
        calls["interval"] += 1
        return interval(values, *a, **k)

    def guarded_tost(values, *a, **k):
        if len(values) == n_e2:
            pytest.fail("tost called on an E2 puzzle-value vector")
        return tost(values, *a, **k)

    monkeypatch.setattr(e2p2, "interval", guarded_interval)
    monkeypatch.setattr(wp2eval, "tost", guarded_tost)
    monkeypatch.setattr(e2p2, "puzzle_values", lambda *a, **k: pytest.fail("puzzle_values called"))
    res = _run(env)
    assert res["primary"]["H2"]["status"] == "identity-failure"
    assert res["primary"]["H3"]["status"] == "identity-failure"
    assert "deviation" in res["primary"]["H2"]["deviation_required"]
    assert res["primary"]["H2"]["code_mismatch"]["level1_B1"] == 1
    assert res["secondary"]["theta2_prime"]["status"] == "identity-failure"
    assert res["secondary"]["uniform"]["status"] == "identity-failure"
    assert res["secondary"]["correct_baseline"]["status"] == "identity-failure"
    assert res["auc"]["6-11"]["auc_a"] is None and res["auc"]["6-11"]["status"] == "identity-failure"
    assert not any(r["hypothesis"] in ("H2", "H3", "theta2_prime") for r in res["readings"])
    assert any(r["hypothesis"] == "E2" for r in res["readings"])
    assert calls["interval"] > 0  # H1 and the other E3 contrasts are still evaluated
    assert res["primary"]["H1"]["estimate"] is not None
    assert res["tables"]["e2"]["code_mismatch"] is not None  # descriptive table still written
    assert res["records"]["e2"]["status"] == "identity-failure"
    assert "logged deviation" in (env.exp / "report.md").read_text(encoding="utf-8")


def test_wp2_evaluate_identity_failure_only_exception(setup):
    env = setup(identity_failure=True)
    _edit_record(env, "e2", invalid_reasons=["identity-failure", "code_dirty"])
    with pytest.raises(SystemExit, match=r"e2.*code_dirty"):
        env.mod.main(["--role", "dry"])


@pytest.mark.parametrize("failure", [False, True])
def test_wp2_evaluate_never_calls_auc_pair_or_summarize2(setup, monkeypatch, failure):
    env = setup(identity_failure=failure)
    for name in ("auc_pair", "summarize2"):
        monkeypatch.setattr(e2p2, name, lambda *a, _n=name, **k: pytest.fail(f"{_n} called by wp2_evaluate"))
    monkeypatch.setattr(ncm_sudoku.e2, "cluster_bootstrap", lambda *a, **k: pytest.fail("cluster_bootstrap called"))
    res = _run(env)
    assert res["role"] == "dry"


@pytest.mark.parametrize("target", ["preds", "diag", "score", "e2_json", "equiv"])
def test_wp2_evaluate_rejects_altered_raw_input(setup, target):
    env = setup()
    path = {"preds": env.raw / "e3" / "preds" / "wl_L06__generated.npz",
            "diag": env.raw / "e2" / "diag" / "L11__frequency__d01__s0.npz",
            "score": env.score_dir / "mask.npy",
            "e2_json": env.raw / "e2.json",
            "equiv": env.exp / "equivariance.json"}[target]
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(SystemExit, match=path.name):
        env.mod.main(["--role", "dry"])
    assert not (env.exp / "results.json").exists()


def test_wp2_evaluate_e3_main_relative_within_construction(default):
    res = default.res
    rows = {r["row"]: r for r in res["tables"]["e3_main"]}
    assert rows["controls.random_linear"]["reference"] == "pc_L06.linear"
    assert rows["wl_L06_controls.random"]["reference"] == "wl_L06.generated"
    assert rows["wl_teacher_L12.teacher"]["reference"] == "wl_L12.generated"
    assert rows["controls.raw_mlp"]["reference"] == "pc_L06.mlp"
    assert rows["controls.teacher_L02_linear"]["reference"] == "pc_L02.linear"
    assert rows["controls.teacher_L12_linear"]["reference"] == "pc_L12.linear"
    assert rows["raw_projected.linear"]["reference"] == "wl_L06.generated"
    assert rows["controls.rule"]["relative_difference"] is None and rows["controls.marginal"]["reference"] is None
    assert "controls.raw_mlp" in rows and "controls.peer_counts_linear" in rows
    perm = rows["wl_L06.permuted"]
    assert perm["relative_difference"] == pytest.approx((perm["brier"] - rows["wl_L06.generated"]["brier"])
                                                        / rows["wl_L06.generated"]["brier"])
    assert perm["construction"] == "whole_layer" and perm["n_params"] == 3042 and perm["config"] == [0.1, 0.001]
    assert len(rows) == 22


def test_wp2_evaluate_budget_lists_30_entries(default):
    res = default.res
    b = res["tables"]["budget"]
    assert all(len(x["entries"]) == 30 for x in b.values())
    assert "wl_L06.generated" in b and "controls.rule" not in b and "training_size.n2000" not in b
    assert b["pc_L06.mlp"]["n_params"] == 22217 and b["pc_L06.mlp"]["any_hit_cap"] is False


def test_wp2_evaluate_secondary_metrics_scope(default):
    res = default.res
    sm = res["tables"]["secondary_metrics"]
    assert "controls.rule" in sm and "controls.marginal" in sm and "unit_digit.generated" not in sm
    assert sm["training_size.n2000"] == {"reused_from": "pc_L06.linear"}
    assert sm["wl_L06.generated"]["mask_exact_match"] == pytest.approx(1.0)
    assert sm["controls.rule"]["brier_ensemble"] == pytest.approx(0.0)
    ud = res["tables"]["unit_digit"]
    assert set(ud) == {"generated", "raw"} and ud["generated"]["exact_match"] == pytest.approx(1.0)


def test_wp2_evaluate_e2_diagnostics_tables(default):
    env, res = default, default.res
    d = res["tables"]["e2_diagnostics"]
    cm = d["cell_change_map"]["L11-frequency-d1"]
    assert len(cm["D"]["cells"]) == 81 and cm["D"]["cells"][0] == pytest.approx(1.0)
    assert cm["D"]["cells"][1] == 0.0 and sum(cm["C"]["cells"]) == 0.0
    assert len(cm["D"]["rows"]) == len(cm["D"]["columns"]) == len(cm["D"]["boxes"]) == 9
    assert cm["D"]["rows"][0] == pytest.approx(1 / 9) and cm["D"]["boxes"][0] == pytest.approx(1 / 9)
    assert set(cm["D"]["empty_given"]) == {"empty", "given"}
    assert set(d["propagation"]) == {"level1-frequency", "level1-uniform", "L11-frequency-d1"}
    prop = d["propagation"]["L11-frequency-d1"]
    assert prop["state_dist_D"] == pytest.approx([0.5] * 12) and prop["state_dist_C"] == pytest.approx([0.25] * 12)
    assert len(prop["level_changed_D"]["map"]) == 12 and len(prop["level_changed_D"]["map"][0]) == 81
    assert d["later_level_changes"]["L11-frequency-d1"] == {"12": pytest.approx(2.0)}
    assert d["later_level_changes"]["level1-frequency"]["2"] == pytest.approx(2.0)
    rep = d["replacement"]["L06-frequency-d4"]
    assert rep["p_new"] == pytest.approx([0.1] * 5) and rep["freq_new"] == pytest.approx([1 / 16] * 5)
    # level 1: each puzzle's weighted share of cell c is 1/15 for c in 0..15 other than its own a1
    l1 = d["cell_change_map"]["level1-frequency"]["C"]["cells"]
    a1 = np.arange(env.n) % 16
    assert l1[3] == pytest.approx(np.mean(np.where(a1 == 3, 0.0, 1 / 15)))
    assert l1[20] == 0.0


def test_wp2_evaluate_results_metadata(default):
    res = default.res
    assert {"date", "code_state", "freeze_state", "environment", "records", "disclosure_7_4"} <= set(res)
    assert "D78" in res["disclosure_7_4"]
    assert "downstream_changes_D" in res["tables"]["e2"]
    assert res["tables"]["equivariance"]["equivariance_reading"] == wp2eval.EQUIV_READING
    assert res["tables"]["equivariance"]["categories"]["all"]["mean_deviation"] == pytest.approx(0.079)
    assert res["tables"]["e1"]["hamming"]["n_cell_hamming"] == 40 and "cell_empty_mean" in res["tables"]["e1"]["hamming"]
    cvp = res["tables"]["config_vs_prelock"]
    assert cvp["pc_L06.mlp"]["differs"] is True and cvp["pc_L06.linear"]["differs"] is False
    assert cvp["wl_L02.generated"]["prelock"] is None
    assert len(res["tables"]["seed_stability"]["H1"]["per_seed"]) == 3
    ts = res["tables"]["training_size"]
    assert {"whole_layer", "per_cell"} <= set(ts) and ts["whole_layer"]["n2000"]["reused_from"] == "wl_L06.generated"


def test_wp2_evaluate_depth_has_label_rates(default):
    res = default.res
    depth = res["tables"]["depth"]
    assert set(depth) == {"wl_L06.generated", "pc_L06.linear", "raw_unprojected.linear", "raw_projected.linear"}
    assert "positive_rate" in depth["wl_L06.generated"]["label_rates"]["1"]
    assert "brier" in depth["wl_L06.generated"]["brier"]["1"]


def test_wp2_evaluate_never_loads_the_model(setup, monkeypatch):
    env = setup()
    monkeypatch.setattr("ncm_sudoku.model.load_model", lambda *a: pytest.fail("evaluation must read raw outputs only"))
    _run(env)


def test_wp2_evaluate_report_contains_does_not_follow_text(default):
    report = default.report
    assert wp2eval.S13["early_sensitivity"]["does_not_follow"] in report
    assert wp2eval.S13["early_sensitivity"]["claim"] in report
    assert "D78" in report and "Results are stated conditionally on checkpoint and intervention policy" in report
    assert wp2eval.NO_ROW in report  # level-12 criterion not met with theta_T on the bound path


def test_wp2_evaluate_labels_rare_event_ci95_of_primary_contrasts(default):
    res, mod = default.res, default.mod
    assert res["primary"]["H3"]["ci95"]["method"] == "bound"
    assert res["primary"]["H3"]["ci95_label"] == mod.CI95_BOUND_LABEL
    assert res["primary"]["H2"]["ci95_label"] == mod.CI95_LABEL
    assert mod.CI95_BOUND_LABEL in default.report


def test_wp2_evaluate_h1_negative_reports_equivalence_also_held(setup):
    env = setup(theta1_shift=-0.003)
    res = _run(env)
    rows = {r["row"] for r in res["readings"] if r["hypothesis"] == "H1"}
    assert rows == {"h1_negative"} and res["primary"]["H1"]["tost"]["equivalent"] is True
    assert env.mod.EQUIV_BOTH_NOTE in (env.exp / "report.md").read_text(encoding="utf-8")
