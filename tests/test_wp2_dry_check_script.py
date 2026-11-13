import importlib.util
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

import wp2_fakes
from ncm_sudoku import wp2
from ncm_sudoku.e3metrics import depth_breakdown_seeds
from ncm_sudoku.probes import SEEDS
from ncm_sudoku.wp2e3 import STAGE_FITS

ROOT = Path(__file__).resolve().parents[1]
KINDS = ("all", "digit", "geometric")
N_EQ = 20
N_EXTRA = 3


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load("wp2_dry_check")


@pytest.fixture(autouse=True)
def _restore_determinism():
    prev = torch.are_deterministic_algorithms_enabled()
    yield
    torch.use_deterministic_algorithms(prev)


def _read(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _set_output(env, runner: str, path: Path, obj, name: str) -> None:
    """Rewrites a dry output and the producing run record's `outputs` entry (a consistent dry run)."""
    wp2.atomic_json(path, obj, indent=None)
    rec_path = env.records / f"{runner}.json"
    rec = _read(rec_path)
    rec["outputs"] = {**rec.get("outputs", {}), name: wp2.file_sha256(path)}
    wp2.atomic_json(rec_path, rec)


def _edit_record(env, runner: str, **fields) -> None:
    p = env.records / f"{runner}.json"
    wp2.atomic_json(p, {**_read(p), **fields})


def _set_path(tree: dict, path: tuple, value) -> None:
    for k in path[:-1]:
        tree = tree.setdefault(k, {})
    tree[path[-1]] = value


def _patch(root: Path, mp: pytest.MonkeyPatch) -> None:
    mp.setattr(wp2, "ROOT", root)
    mp.setattr(wp2, "DRY_CHECK", root / "experiments" / "wp2" / "dry" / "check.json")
    mp.setattr(wp2, "freeze_state", lambda root=None: dict(wp2_fakes.FROZEN))
    mp.setattr(wp2, "code_state", lambda: dict(wp2_fakes.CODE))
    mp.setattr(wp2, "environment_record", lambda: dict(wp2_fakes.ENV))


def _paths(root: Path, ids: SimpleNamespace) -> SimpleNamespace:
    exp, raw = root / "experiments" / "wp2" / "dry", root / "runs" / "wp2" / "dry"
    return SimpleNamespace(
        root=root, exp=exp, raw=raw, records=exp / "runs", score_dir=raw / "e3data" / "score", check=exp / "check.json",
        pilot2=root / "runs" / "e2p2" / "pilot2.json", full=root / "runs" / "lock" / "level1_full_batch.json",
        probes=root / "experiments" / "e3prep" / "probes.json",
        wholelayer=root / "experiments" / "e3prep" / "wholelayer.json",
        lock_eq=root / "experiments" / "lock" / "equivariance_l12.json", **vars(ids))


def _build(root: Path, mp: pytest.MonkeyPatch) -> SimpleNamespace:
    """A consistent synthetic dry run (`wp2_fakes.write_role`, 50 E2 ids) plus pre-lock references
    that equal it on the dry ids and carry extra ids the check must filter out."""
    _patch(root, mp)
    fake = wp2_fakes.write_role(root, "dry", n=wp2.N_DRY, theta2=0.0, n_score=24)
    env = _paths(root, SimpleNamespace(e2_ids=fake.e2_ids, score_ids=fake.score_ids))

    # E1: generated solve equals the E2 base solve_A (both are A)
    e1 = _read(env.raw / "e1.json")
    for r in e1["records"]:
        r["solve"] = True
    _set_output(env, "e1", env.raw / "e1.json", e1, "e1.json")

    # E2: parts manifest, identity counts in the record
    e2 = _read(env.raw / "e2.json")
    parts = env.raw / "e2" / "parts.json"
    wp2.atomic_json(parts, {"parts/base.json": "0" * 64})
    _edit_record(env, "e2", level1_noop_mismatch=0, sham_mismatch={"level1_B1": 0, "levels_B": {"2": 0, "6": 0, "11": 0}},
                 code_mismatch=e2["code_mismatch"])
    _set_output(env, "e2", parts, _read(parts), "parts.json")

    extra = [f"cal-extra-{j}" for j in range(N_EXTRA)]
    ref_base = e2["base"] + [{"puzzle_id": p, "solve_A": 0, "solve_B1": 1} for p in extra]
    ex_l1 = [{**r, "puzzle_id": p, "solve_C": 0} for p in extra for r in e2["level1"] if r["puzzle_id"] == "e2-0"]
    ex_recs = [{**r, "puzzle_id": p, "tv": 9.0} for p in extra for r in e2["records"] if r["puzzle_id"] == "e2-0"]
    pilot2 = {"freqs_level1": e2["freqs_level1"], "base": ref_base,
              "level1": [{k: v for k, v in r.items() if k != "noop"} for r in e2["level1"] + ex_l1 if not r["noop"]],
              "records": e2["records"] + ex_recs}
    full = {"freqs_level1": e2["freqs_level1"], "freq_source": "frozen", "ids": env.e2_ids + extra,
            "base": ref_base, "level1": e2["level1"] + ex_l1, "level1_noop_mismatch": 0}
    wp2.atomic_json(env.pilot2, pilot2, indent=None)
    wp2.atomic_json(env.full, full, indent=None)

    # E3: PROBE inputs in the e3 record, references equal to the dry fits
    probe_inputs, files = {}, {}
    for subset in ("probe_train", "probe_val"):
        for name in mod.PROBE_INPUT_FILES:
            p = root / "runs" / "e3prep" / subset / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(f"{subset}/{name}".encode())
            files[f"{subset}/{name}"] = wp2.file_sha256(p)
            probe_inputs[f"runs/e3prep/{subset}/{name}"] = files[f"{subset}/{name}"]
    files["score/ids.json"] = wp2.file_sha256(env.score_dir / "ids.json")
    _edit_record(env, "e3", inputs={"files": files, "arrays": {}, "budget_overrides": {}, "k": 256,
                                    "sizes": [125, 250, 500, 1000, 2000]})
    env.probe_inputs = probe_inputs

    fits = _read(env.exp / "e3_fits.json")
    refs = {"probes.json": {"val_ids": env.score_ids, "stages": {}},
            "wholelayer.json": {"val_ids": env.score_ids, "stages": {}}}
    for name, (ref_file, path) in mod.E3_MAP.items():
        stage, fit = name.split(".")
        s = fits["stages"][stage][fit]
        _set_path(refs[ref_file], path, {"config": s["config"], "per_puzzle": s["per_puzzle"], "val_brier_mean": 0.0})
    score = {n: np.load(env.score_dir / f"{n}.npy") for n in ("mask", "empty", "depth")}

    def depth(stage_fit):
        stage, fit = stage_fit.split(".")
        with np.load(env.raw / "e3" / "preds" / f"{stage}__{fit}.npz") as z:
            preds = [z[f"seed{s}"] for s in SEEDS]
        return depth_breakdown_seeds(preds, score["mask"], score["empty"], score["depth"])

    refs["probes.json"]["stages"]["depth_L06"] = {"aggregation": "per seed model, then mean of the per-seed Briers",
                                                  **{k: depth(v) for k, v in mod.DEPTH_MAP.items()}}
    wp2.atomic_json(env.probes, refs["probes.json"])
    wp2.atomic_json(env.wholelayer, refs["wholelayer.json"])

    # extraction
    _edit_record(env, "e3_extract", matches_e3prep={Path(n).stem: {"equal": True, "max_abs_diff": 0.0}
                                                    for n in mod.EXTRACT_ARRAYS})

    # equivariance
    rng = np.random.default_rng(7)
    dev = {k: rng.uniform(0.005, 0.02, N_EQ).tolist() for k in KINDS}
    common = {"level": 12, "n": N_EQ, "k": 4, "seed": 0, "n_predictors": 3, "ids": env.score_ids[:N_EQ],
              "deviation": dev, "seed_noise": rng.uniform(0, 0.02, N_EQ).tolist(),
              "brier": {k: rng.uniform(0.1, 0.2, N_EQ).tolist() for k in KINDS},
              "brier_original": rng.uniform(0.1, 0.2, N_EQ).tolist()}
    within = lambda a: {k: float(np.mean(np.asarray(v) <= a)) for k, v in dev.items()}  # noqa: E731
    equiv = {**_read(env.exp / "equivariance.json"), **common, "acceptable": 0.0116, "share_within": within(0.0116),
             "probe": {"config": [0.1, 0.001], "files": {}}}
    _set_output(env, "equiv", env.exp / "equivariance.json", equiv, "equivariance.json")
    lock_acc = 0.011644554557515473
    wp2.atomic_json(env.lock_eq, {**common, "acceptable": lock_acc, "share_within": within(lock_acc),
                                  "probe": {"level": 12, "kind": "linear", "config": [0.1, 0.001]}})
    return env


@pytest.fixture(scope="module")
def _template(tmp_path_factory):
    with pytest.MonkeyPatch.context() as mp:
        env = _build(tmp_path_factory.mktemp("template"), mp)
    return env


@pytest.fixture
def env(_template, tmp_path, monkeypatch):
    """A fresh copy of the module's synthetic dry tree per test."""
    root = tmp_path / "root"
    shutil.copytree(_template.root, root)
    _patch(root, monkeypatch)
    return _paths(root, SimpleNamespace(e2_ids=_template.e2_ids, score_ids=_template.score_ids,
                                        probe_inputs=_template.probe_inputs))


# --- compare_keyed ------------------------------------------------------------------------------

def test_compare_keyed_counts_and_lists_differences():
    new = [{"k": i, "a": i, "b": float(i)} for i in range(60)]
    old = [{"k": i, "a": i + (1 if i else 0), "b": float(i) + (0.5 if i == 3 else 0.0)} for i in range(60)]
    r = mod.compare_keyed(new, old, ("k",), ("a", "b"))
    assert r["n_matched"] == 60 and r["n_missing_new"] == 0 and r["n_missing_old"] == 0
    assert r["complete_coverage"] is True
    assert r["a"] == {"n_diff": 59, "max_abs_diff": 1.0}
    assert r["b"]["n_diff"] == 1 and r["b"]["max_abs_diff"] == pytest.approx(0.5)
    assert len(r["differing"]) == 50
    assert r["differing"][0] == {"key": [1], "fields": ["a"]}
    assert {"key": [3], "fields": ["a", "b"]} in r["differing"]
    assert mod.compare_keyed(new, old[:-1], ("k",), ("a",))["n_missing_old"] == 1
    assert mod.compare_keyed(new[:-1], old, ("k",), ("a",))["n_missing_new"] == 1
    assert mod.compare_keyed(new[:-1], old, ("k",), ("a",))["complete_coverage"] is False


def test_compare_keyed_none_handling():
    new = [{"k": 1, "h": None}, {"k": 2, "h": None}, {"k": 3, "h": 0.5}]
    old = [{"k": 1, "h": None}, {"k": 2, "h": 0.1}, {"k": 3, "h": 0.25}]
    r = mod.compare_keyed(new, old, ("k",), ("h",))
    assert r["h"]["n_diff"] == 2 and r["h"]["max_abs_diff"] == pytest.approx(0.25)
    r = mod.compare_keyed([{"k": 1, "h": None}], [{"k": 1, "h": 0.3}], ("k",), ("h",))
    assert r["h"] == {"n_diff": 1, "max_abs_diff": None}
    r = mod.compare_keyed([{"k": 1, "h": True}], [{"k": 1, "h": 1}], ("k",), ("h",))
    assert r["h"]["n_diff"] == 0


def test_compare_keyed_filters_and_asserts_coverage():
    old = [{"pid": f"p{i}", "v": v, "x": 1} for i in range(300) for v in range(2)]
    new = [{"pid": f"p{i}", "v": v, "x": 1} for i in range(50) for v in range(2)]
    expected = {(f"p{i}", v) for i in range(50) for v in range(2)}
    r = mod.compare_keyed(new, old, ("pid", "v"), ("x",), expected_keys=expected)
    assert r["complete_coverage"] is True and r["n_matched"] == 100 and r["n_missing_new"] == 0
    assert r["n_missing_old"] == 0 and r["x"]["n_diff"] == 0
    r = mod.compare_keyed(new[1:], old, ("pid", "v"), ("x",), expected_keys=expected)
    assert r["complete_coverage"] is False and r["n_missing_new"] == 1
    r = mod.compare_keyed(new, old[2:], ("pid", "v"), ("x",), expected_keys=expected)
    assert r["complete_coverage"] is False and r["n_missing_old"] == 2
    r = mod.compare_keyed(new + [{"pid": "p99", "v": 0, "x": 1}], old, ("pid", "v"), ("x",), expected_keys=expected)
    assert r["complete_coverage"] is False


# --- end to end ---------------------------------------------------------------------------------

def test_dry_check_success_on_identical_synthetic_references(env, capsys):
    assert mod.run([]) == 0
    c = _read(env.check)
    assert c["technical_success"] is True, json.dumps({k: v.get("ok") for k, v in c["comparisons"].items()})
    assert c["code"]["commit"] == wp2_fakes.TAG and "environment" in c and c["freeze_state"]["frozen"] is True
    assert c["note"] == wp2.DRY_NOTE
    assert set(c["snapshot"]["dry_records"]) == {f"experiments/wp2/dry/runs/{r}.json"
                                                 for r in ("e3_extract", "e3", "equiv", "e2", "e1")}
    assert set(c["snapshot"]["compared"]) == {
        "runs/wp2/dry/e2.json", "runs/wp2/dry/e1.json", "runs/wp2/dry/e2/parts.json",
        "experiments/wp2/dry/e3_fits.json", "experiments/wp2/dry/e3_budget.json",
        "experiments/wp2/dry/equivariance.json", "runs/e2p2/pilot2.json", "runs/lock/level1_full_batch.json",
        "experiments/e3prep/probes.json", "experiments/e3prep/wholelayer.json",
        "experiments/lock/equivariance_l12.json"}
    assert c["records"]["e2"]["status"] == "valid" and c["records"]["e2"]["valid"] is True
    cmp = c["comparisons"]
    assert cmp["e2_records"]["n_matched"] == 50 * 78 and cmp["e2_records"]["complete_coverage"] is True
    assert cmp["e2_level1"]["n_matched"] == 50 * 16
    assert cmp["e2_base"]["pilot2"]["n_matched"] == 50 and cmp["e2_base"]["level1_full_batch"]["n_matched"] == 50
    assert cmp["e1"]["n_matched"] == 50
    assert set(cmp["e3"]["new_fits"]) == mod.NEW_FITS
    assert cmp["e3"]["depth"]["ok"] is True
    assert cmp["equivariance"]["share_within"]["at_0.0116"] == _read(env.exp / "equivariance.json")["share_within"]
    assert set(cmp["equivariance"]["share_within"]["at_lock_value"]) == set(KINDS)
    assert (env.check.parent / "check.md").is_file()
    assert "DRY RUN" in (env.check.parent / "check.md").read_text(encoding="utf-8")
    out = capsys.readouterr().out.strip().splitlines()
    assert [json.loads(x) for x in out] == [{"runner": "dry_check", "complete": True, "valid": True}]
    wp2.verify_dry_approval(c)  # passes on the unchanged files
    assert mod.run([]) == 0  # safe to rerun
    assert _read(env.check)["technical_success"] is True


def test_dry_check_snapshot_detects_later_change(env):
    mod.run([])
    c = _read(env.check)
    p = env.raw / "e2.json"
    b = bytearray(p.read_bytes())
    b[-2] = ord(" ") if b[-2] != ord(" ") else ord("\t")
    p.write_bytes(bytes(b))
    with pytest.raises(wp2.DataIntegrityError, match="runs/wp2/dry/e2.json"):
        wp2.verify_dry_approval(c)


def test_dry_check_probe_inputs_from_dry_e3_record(env):
    mod.run([])
    c = _read(env.check)
    assert c["technical_success"] is True
    assert c["snapshot"]["probe_inputs"] == env.probe_inputs
    assert len(env.probe_inputs) == 2 * len(mod.PROBE_INPUT_FILES)
    (env.root / "runs" / "e3prep" / "probe_val" / "L06.npy").write_bytes(b"changed after the dry E3 run")
    mod.run([])
    c = _read(env.check)
    assert c["technical_success"] is False and c["comparisons"]["probe_inputs"]["ok"] is False
    assert "runs/e3prep/probe_val/L06.npy" in c["comparisons"]["probe_inputs"]["changed"]


def test_dry_check_deletes_stale_check_before_refusing(env):
    mod.run([])
    assert env.check.is_file()
    (env.raw / "e1.json").write_text("{}", encoding="utf-8")  # differs from the e1 record's outputs
    with pytest.raises(SystemExit, match="e1.json"):
        mod.main([])
    assert not env.check.exists() and not (env.check.parent / "check.md").exists()


def _mutate(env, part: str) -> None:
    if part == "e2_records":
        p = _read(env.pilot2)
        p["records"][5]["tv"] += 1e-9
        wp2.atomic_json(env.pilot2, p, indent=None)
    elif part == "e2_level1":
        f = _read(env.full)
        noop = next(r for r in f["level1"] if r["noop"] and r["puzzle_id"] in env.e2_ids)
        noop["tv"] = 1e-12
        wp2.atomic_json(env.full, f, indent=None)
    elif part == "e2_base":
        f = _read(env.full)
        f["base"][0]["solve_B1"] = 0
        wp2.atomic_json(env.full, f, indent=None)
    elif part == "e2_identity":
        _edit_record(env, "e2", sham_mismatch={"level1_B1": 0, "levels_B": {"2": 0, "6": 1, "11": 0}})
    elif part == "e2_code_identity":
        e2 = _read(env.raw / "e2.json")
        e2["code_mismatch"]["levels_B"]["11"] = 1
        _set_output(env, "e2", env.raw / "e2.json", e2, "e2.json")
    elif part == "e3_config":
        p = _read(env.probes)
        p["stages"]["controls"]["teacher_L06_linear"]["config"] = [0.0, 0.001]
        wp2.atomic_json(env.probes, p)
    elif part == "e3_per_puzzle":
        w = _read(env.wholelayer)
        w["stages"]["L06"]["generated_linear"]["per_puzzle"][3] += 1e-3
        wp2.atomic_json(env.wholelayer, w)
    elif part == "equivariance":
        q = _read(env.lock_eq)
        q["seed_noise"][0] += 1e-3
        wp2.atomic_json(env.lock_eq, q)
    elif part == "e1":
        e1 = _read(env.raw / "e1.json")
        e1["records"][7]["solve"] = False
        _set_output(env, "e1", env.raw / "e1.json", e1, "e1.json")
    elif part == "e1_coverage":
        e1 = _read(env.raw / "e1.json")
        e1["records"] = e1["records"][:-1]
        _set_output(env, "e1", env.raw / "e1.json", e1, "e1.json")
    elif part == "extraction":
        rec = _read(env.records / "e3_extract.json")
        rec["matches_e3prep"]["L06"] = {"equal": False, "max_abs_diff": 1e-7}
        wp2.atomic_json(env.records / "e3_extract.json", rec)
    elif part == "invalid_record":
        _edit_record(env, "e3", code_changed_during_run=True)
    else:
        raise ValueError(part)


FAILS = {"e2_records": "e2_records", "e2_level1": "e2_level1", "e2_base": "e2_base", "e2_identity": "e2_identity",
         "e2_code_identity": "e2_identity", "e3_config": "e3", "e3_per_puzzle": "e3", "equivariance": "equivariance",
         "e1": "e1", "e1_coverage": "e1", "extraction": "extraction", "invalid_record": None}


@pytest.mark.parametrize("part", ["e2_records", "e2_level1", "e2_base", "e2_identity", "e2_code_identity",
                                  "e3_config", "e3_per_puzzle", "equivariance", "e1", "e1_coverage", "extraction",
                                  "invalid_record"])
def test_dry_check_detects_each_difference(env, part, capsys):
    _mutate(env, part)
    mod.run([])
    c = _read(env.check)
    assert c["technical_success"] is False
    failing = {k for k, v in c["comparisons"].items() if not v["ok"]}
    assert failing == ({FAILS[part]} if FAILS[part] else set())
    invalid = {r for r, s in c["records"].items() if not s["valid"]}
    assert invalid == ({"e3"} if part == "invalid_record" else set())
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["valid"] is False


def test_dry_check_depth_difference(env):
    p = _read(env.probes)
    p["stages"]["depth_L06"]["raw_linear"]["1"]["brier_per_seed"][0] += 1e-3
    wp2.atomic_json(env.probes, p)
    mod.run([])
    c = _read(env.check)
    assert c["technical_success"] is False and c["comparisons"]["e3"]["depth"]["ok"] is False


def test_dry_check_mapping_covers_every_stage_fit():
    assert not set(mod.E3_MAP) & mod.NEW_FITS
    assert set(mod.E3_MAP) | mod.NEW_FITS == {f"{s}.{f}" for s, fits in STAGE_FITS.items() for f in fits}
    assert mod.E3_MAP["wl_L06.generated"] == ("wholelayer.json", ("stages", "L06", "generated_linear"))
    assert mod.E3_MAP["wl_teacher_L12.teacher"] == ("wholelayer.json", ("stages", "teacher_L12", "teacher_linear"))
    assert mod.E3_MAP["raw_unprojected.linear"] == ("wholelayer.json", ("stages", "raw_unprojected", "linear"))
    assert mod.E3_MAP["pc_L02.permuted"] == ("probes.json", ("stages", "L02_permuted_linear"))
    assert mod.E3_MAP["pc_L06.mlp"] == ("probes.json", ("stages", "L06_mlp"))
    assert mod.E3_MAP["controls.rule"] == ("probes.json", ("stages", "controls", "rule"))
    assert mod.E3_MAP["unit_digit.raw"] == ("probes.json", ("stages", "unit_digit", "raw"))
    assert mod.E3_MAP["training_size.n125"] == ("probes.json", ("stages", "training_size", "125"))
    assert mod.DEPTH_MAP == {"generated_linear": "pc_L06.linear", "raw_linear": "controls.raw_linear"}
    assert len(mod.E2_FIELDS) == 20 and mod.E2_FIELDS[:5] == ("puzzle_id", "level", "policy", "dose", "seed")
