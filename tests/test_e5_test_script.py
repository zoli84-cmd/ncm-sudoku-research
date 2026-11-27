"""Model-free tests of scripts/e5_test.py: `extract_batch`, `evaluate_batch`, `generate_codes`
and `load_model` are replaced by deterministic fakes; every input lives under `tmp_path`."""

import importlib.util
import json

import numpy as np
import pytest
import torch

from conftest import ROOT
from ncm_sudoku import e5pairs, e5run, subsets, wp2
from ncm_sudoku.generate import random_solution

N = 250
N_T = 60  # TEST size in the model-free test-mode runs (two extraction batches, the second partial)
D, Z = 4, 3  # fake residual and Z<=6 state widths
OFFSET = 1000  # test-mode runs redirect the TEST seed namespace 10 to 1010: real TEST pairs are never generated


def _mod():
    spec = importlib.util.spec_from_file_location("e5_test", ROOT / "scripts" / "e5_test.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _grids(rng):
    sols, a, b = [], [], []
    for _ in range(N):
        s = random_solution(rng)
        pa, pb = s.copy(), s.copy()
        pa[rng.choice(81, 51, replace=False)] = 0
        pb[rng.choice(81, 51, replace=False)] = 0
        sols.append(s), a.append(pa), b.append(pb)
    return (np.stack(x).astype(np.uint8) for x in (a, b, sols))


def _head(rng, width):
    return [{"0.weight": torch.as_tensor(rng.normal(size=(9, width + 81)), dtype=torch.float32),
             "0.bias": torch.as_tensor(rng.normal(size=9), dtype=torch.float32)} for _ in range(3)]


def _fake_extract(nan_batch=None):
    calls = {"n": 0}

    def extract_batch(m, puzzles, solutions):
        calls["n"] += 1
        p = np.asarray(puzzles, np.float32)
        B = len(p)
        feat = np.stack([p[:, :D] * (k + 1) / 10 for k in range(9)], 1)[:, :, None, :]
        prefix = (np.broadcast_to(feat, (B, 9, 81, D)) + p[:, None, :, None] / 7).astype(np.float16)
        z6 = (p[:, :, None] / 9 + np.arange(Z)).astype(np.float32)
        if nan_batch is not None and calls["n"] == nan_batch:
            z6[0, 0, 0] = np.nan
        return {"prefix_cells": prefix, "prefix_bos": prefix[:, :, 0].copy(),
                "level7_queries": np.zeros((B, 9, 18, D), np.float16), "z6": z6, "z6_teacher": z6.copy(),
                "codes": (np.asarray(puzzles)[:, :40] % 16).astype(np.int8), "solved": np.ones(B, bool)}

    return extract_batch


def _fake_evaluate(fail_batches=()):
    calls = {"n": 0}

    def evaluate_batch(m, comps, heads, pr, pd, cr, cd, empty_r, empty_d, mask_r, mask_d):
        calls["n"] += 1
        B = len(cr)
        base = (pr.numpy().sum(1) - 0.5 * pd.numpy().sum(1)).astype(np.float64)[:, None] / 1e4
        directed = base + np.linspace(0.0, 0.01, 25)[None, :]
        directed[:, 0] += 0.02  # Q
        zeros = np.zeros((B, 25))
        reasons = ["written_rows"] if calls["n"] in fail_batches else []
        return {"directed": directed, "undirected": zeros, "argmax_changes": zeros, "shift4": zeros,
                "shift8": zeros, "flip4": zeros, "flip8": zeros, "conditions": list(range(25)),
                "invalid_reasons": reasons,
                "diagnostics": {"target_norm": np.ones(B), "actual_norm": zeros, "scale": zeros,
                                "cos_delta": zeros, "tv_clean_full": np.ones(B)}}

    return evaluate_batch


def _setup(tmp_path, monkeypatch, extract=None, evaluate=None, test_inputs=False):
    s = _mod()
    rng = np.random.default_rng(0)
    root = tmp_path / "root"
    pv = root / "runs" / "e5" / "pairs" / "probe_val"
    pv.mkdir(parents=True)
    a, b, sol = _grids(rng)
    ids = [f"e5pair-v1-9-{i}" for i in range(N)]
    (pv / "ids.json").write_text(json.dumps(ids), encoding="utf-8")
    for k, v in (("a", a), ("b", b), ("solutions", sol)):
        np.save(pv / f"{k}.npy", v)
    sha = {"ids": subsets.sha256_ids(ids), "a": subsets.sha256_array(a), "b": subsets.sha256_array(b),
           "solutions": subsets.sha256_array(sol)}
    (root / "experiments" / "e5" / "causal").mkdir(parents=True)
    (root / "experiments" / "e5" / "lock").mkdir(parents=True)
    pairs_json = {"subsets": {"probe_val": {"count": N, "ids": ids, "sha256": sha}}}
    if test_inputs:  # the extra files `_inputs("test", ...)` hashes: PROBE-TRAIN pairs, released set, WP2 TEST
        pt = root / "runs" / "e5" / "pairs" / "probe_train"
        pt.mkdir(parents=True)
        pt_ids = [f"e5pair-v1-8-{i}" for i in range(N)]
        (pt / "ids.json").write_text(json.dumps(pt_ids), encoding="utf-8")
        for k, v in (("a", a), ("b", b), ("solutions", sol)):
            np.save(pt / f"{k}.npy", v)
        pairs_json["subsets"]["probe_train"] = {"count": N, "ids": pt_ids,
                                                "sha256": {**sha, "ids": subsets.sha256_ids(pt_ids)}}
        rel = root / "data" / "released" / "sudoku" / "hard"
        rel.mkdir(parents=True)
        files = {}
        for name in ("puzzles.pickle", "solutions.pickle"):
            (rel / name).write_bytes(b"fake " + name.encode())
            files[f"sudoku/hard/{name}"] = {"sha256": wp2.file_sha256(rel / name)}
        (root / "experiments" / "provenance").mkdir(parents=True)
        (root / "experiments" / "provenance" / "released_data.json").write_text(
            json.dumps({"hard": {"files": files}}), encoding="utf-8")
        (root / "experiments" / "lock").mkdir(parents=True)
        (root / "experiments" / "lock" / "test_set.json").write_text(json.dumps({"sha256": {}}), encoding="utf-8")
    (root / "experiments" / "e5" / "pairs.json").write_text(json.dumps(pairs_json), encoding="utf-8")

    heads_dir, lock_dir = root / "runs" / "e5" / "causal" / "heads", root / "runs" / "e5" / "lock"
    heads_dir.mkdir(parents=True), lock_dir.mkdir(parents=True)
    heads = {}
    for rep, width in (("P2", D), ("P4", D), ("P8", D)):
        torch.save(_head(rng, width), heads_dir / f"{rep}.pt")
        heads[rep] = {"file": f"runs/e5/causal/heads/{rep}.pt", "sha256": wp2.file_sha256(heads_dir / f"{rep}.pt")}
    torch.save(_head(rng, Z), lock_dir / "z6.pt")
    files = {"z6_head": {"file": "runs/e5/lock/z6.pt", "sha256": wp2.file_sha256(lock_dir / "z6.pt")}}
    comps = {"W": rng.normal(size=(9, D)), "Q": rng.normal(size=(D, 9)), "H": rng.normal(size=(D, 9)),
             "R": rng.normal(size=(20, D, 9)), "Pi": np.roll(np.arange(9), 1)}
    for k, v in comps.items():
        np.save(lock_dir / f"{k}.npy", v)
        files[k] = {"file": f"runs/e5/lock/{k}.npy", "sha256": wp2.file_sha256(lock_dir / f"{k}.npy")}
    (root / "experiments" / "e5" / "causal" / "heads.json").write_text(json.dumps({"heads": heads}), encoding="utf-8")
    (root / "experiments" / "e5" / "lock" / "components.json").write_text(json.dumps({"files": files}),
                                                                         encoding="utf-8")
    ck = root / "checkpoints" / "sudoku" / "hard"
    ck.mkdir(parents=True)
    for name in wp2.CKPT_SHA256:
        (ck / name).write_bytes(b"fake " + name.encode())

    monkeypatch.setattr(s, "ROOT", root)
    monkeypatch.setattr(s, "D_MODEL", D)
    monkeypatch.setattr(s, "Z_DIM", Z)
    monkeypatch.setattr(s, "verify_checkpoints", lambda d: None)
    monkeypatch.setattr(s, "load_model", lambda d: object())
    monkeypatch.setattr(s, "extract_batch", extract or _fake_extract())
    monkeypatch.setattr(s, "evaluate_batch", evaluate or _fake_evaluate())
    monkeypatch.setattr(s, "generate_codes",
                        lambda m, puzzles, batch_size: torch.as_tensor(np.asarray(puzzles)[:, :40] % 16).long())
    monkeypatch.setattr(e5run, "RUN_DIR", {k: tmp_path / "runs" / k for k in e5run.RUN_DIR})
    monkeypatch.setattr(e5run, "OUT_DIR", {k: tmp_path / "out" / k for k in e5run.OUT_DIR})
    if test_inputs:
        monkeypatch.setattr(e5run, "require_lock", lambda manifest, dry_record: None)
        monkeypatch.setattr(s, "N_TEST", N_T)
    return s, ids


def _results(tmp_path, mode):
    return json.loads((tmp_path / "out" / mode / "results.json").read_text(encoding="utf-8"))


def _run_json(tmp_path, mode):
    return json.loads((tmp_path / "runs" / mode / "run.json").read_text(encoding="utf-8"))


def test_dry_mode_never_touches_test_generation(tmp_path, monkeypatch):
    s, ids = _setup(tmp_path, monkeypatch)

    def boom(*a, **k):
        raise AssertionError("TEST generation path reached in dry mode")

    monkeypatch.setattr(e5pairs, "generate_pair", boom)
    monkeypatch.setattr(subsets, "generate_subset", boom)
    assert s.run("dry", resume=False) == "finished"
    res = _results(tmp_path, "dry")
    assert list(res["pairs"]) == ids
    assert res["outcomes"]["A"] in ("holds", "not_shown") and res["outcomes"]["B"] in ("holds", "not_shown")
    assert res["threads"] == 4 and _run_json(tmp_path, "dry")["status"] == "finished"
    report = (tmp_path / "out" / "dry" / "report.md").read_text(encoding="utf-8")
    assert "Justified claim" in report


def test_stage_outputs_are_keyed_by_pair_id_under_permutation(tmp_path, monkeypatch):
    s, ids = _setup(tmp_path, monkeypatch)
    assert s.run("dry", resume=False) == "finished"
    monkeypatch.setattr(s, "extract_batch", _fake_extract())
    monkeypatch.setattr(s, "evaluate_batch", _fake_evaluate())
    assert s.run("dry_perm", resume=False) == "finished"
    dry, perm = _results(tmp_path, "dry"), _results(tmp_path, "dry_perm")
    assert dry["pairs"] == perm["pairs"]
    assert dry["decision"]["inputs"] == perm["decision"]["inputs"]
    assert dry["decision"]["log_k"] == perm["decision"]["log_k"]
    first = np.load(tmp_path / "runs" / "dry_perm" / "causal" / "ab_batch_0.npz", allow_pickle=False)
    assert first["pair_ids"].tolist() == [ids[int(j)] for j in s.PERMUTATION[:50]]
    assert first["pair_index"].tolist() == s.PERMUTATION[:50].tolist()
    assert (first["order"] == 0).all()
    ext = np.load(tmp_path / "runs" / "dry_perm" / "extract" / "b" / "batch_1.npz", allow_pickle=False)
    assert ext["pair_index"].tolist() == s.PERMUTATION[50:100].tolist()
    assert ext["pair_ids"].tolist() == [ids[int(j)] for j in s.PERMUTATION[50:100]]
    pr = np.load(tmp_path / "runs" / "dry_perm" / "probes.npz", allow_pickle=False)
    assert pr["pair_ids"].tolist() == [ids[int(j)] for j in s.PERMUTATION] * 2
    assert pr["member"].tolist() == ["a"] * N + ["b"] * N


def test_non_finite_extraction_stops_with_both_claims_invalid(tmp_path, monkeypatch):
    s, _ = _setup(tmp_path, monkeypatch, extract=_fake_extract(nan_batch=2))
    assert s.run("dry", resume=False) == "invalid"
    res = _results(tmp_path, "dry")
    assert res["outcomes"] == {"A": "invalid", "B": "invalid"}
    assert any("non_finite" in r for r in res["invalid_reasons"]["shared"])
    assert _run_json(tmp_path, "dry")["status"] == "invalid"
    assert not (tmp_path / "runs" / "dry" / "causal").exists()
    report = (tmp_path / "out" / "dry" / "report.md").read_text(encoding="utf-8")
    assert "Internal collision, shared failure or non-finite stop" in report


def test_claim_b_failure_in_one_batch_survives_later_batches(tmp_path, monkeypatch):
    s, ids = _setup(tmp_path, monkeypatch, evaluate=_fake_evaluate(fail_batches=(1,)))
    assert s.run("dry", resume=False) == "finished"
    res = _results(tmp_path, "dry")
    assert res["invalid_reasons"]["B"] == ["written_rows"]
    assert res["outcomes"]["B"] == "invalid" and res["outcomes"]["A"] != "invalid"
    assert len(res["pairs"]) == N and all(r["Q"] is not None for r in res["pairs"].values())
    first = np.load(tmp_path / "runs" / "dry" / "causal" / "ab_batch_0.npz", allow_pickle=False)
    assert first["invalid_reasons"].tolist() == ["written_rows"]


def test_permutation_property():
    s = _mod()
    perm = np.asarray(s.PERMUTATION)
    assert sorted(perm.tolist()) == list(range(N))
    j = np.arange(N)
    assert (perm % 50 != j % 50).all()  # every pair changes its in-batch position
    for k in range(N // 50):
        new = set(perm[50 * k: 50 * k + 50].tolist())
        assert max(len(new & set(range(50 * o, 50 * o + 50))) for o in range(N // 50)) <= 11


def test_resume_skips_recorded_stages(tmp_path, monkeypatch):
    s, _ = _setup(tmp_path, monkeypatch)
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 3:
            raise KeyboardInterrupt
        return base(*a, **k)

    base = _fake_evaluate()
    monkeypatch.setattr(s, "evaluate_batch", flaky)
    with pytest.raises(KeyboardInterrupt):
        s.run("dry", resume=False)
    (tmp_path / "runs" / "dry" / ".lock").unlink()
    monkeypatch.setattr(s, "extract_batch", lambda *a, **k: pytest.fail("extraction redone on resume"))
    assert s.run("dry", resume=True) == "finished"
    assert calls["n"] == 3 + 8  # 10 causal batches in total; two were recorded before the interrupt


def test_every_outcome_pair_selects_existing_section8_rows():
    s = _mod()
    table = s.section8_rows((ROOT / "e5_protocol_v1.md").read_text(encoding="utf-8"))
    assert len(table) == 10 and all(len(cells) == 3 for cells in table.values())
    outcomes = ("holds", "not_shown", "not_estimable", "invalid")
    for a in outcomes:
        for b in outcomes:
            rows = s.select_rows(a, b, stopped=False)
            assert all(r in table for r in rows)
    assert s.select_rows("holds", "holds", stopped=False) == ["Claim A holds", "Claim B holds", "Claims A and B hold"]
    assert s.select_rows("holds", "holds", stopped=True) == [s.STOP_ROW]
    assert s.select_rows("invalid", "invalid", stopped=False) == []
    assert s.select_rows("not_estimable", "invalid", stopped=False) == []
    assert s.select_rows("invalid", "not_estimable", stopped=False) == []
    assert s.select_rows("holds", "invalid", stopped=False) == ["Claim A holds", "Claim B invalid (§6), claim A valid"]


def test_capture_failure_stops_with_both_claims_invalid(tmp_path, monkeypatch):
    def broken(m, puzzles, solutions):
        raise RuntimeError("pass 6 not captured completely (8 tensors)")

    s, _ = _setup(tmp_path, monkeypatch, extract=broken)
    assert s.run("dry", resume=False) == "invalid"
    res = _results(tmp_path, "dry")
    assert res["outcomes"] == {"A": "invalid", "B": "invalid"}
    assert any(r.startswith("extraction_check: extract/a/batch_0: pass 6") for r in res["invalid_reasons"]["shared"])
    assert _run_json(tmp_path, "dry")["status"] == "invalid"
    assert not (tmp_path / "runs" / "dry" / ".lock").exists()


def test_test_generation_error_stops_with_reason(tmp_path, monkeypatch):
    from ncm_sudoku.generate import GenerationError

    s, _ = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(e5run, "require_lock", lambda manifest, dry_record: None)
    monkeypatch.setattr(s, "_inputs", lambda mode, P: ({"mode": mode}, {}))
    monkeypatch.setattr(s, "_start_checks", lambda *a: {"shared": [], "A": [], "B": []})
    monkeypatch.setattr(s, "screening_corpus", lambda P: ({}, {"counts": {}}, None))
    real = e5pairs.generate_pair

    def gen(seed, index):
        assert seed == e5pairs.PAIR_SEEDS["pairs_test"] == 10
        if index == 1:
            raise GenerationError("30 clues not reached in 50 attempts")
        return real(seed + OFFSET, index)

    monkeypatch.setattr(e5pairs, "generate_pair", gen)
    assert s.run("test", resume=False) == "invalid"
    res = _results(tmp_path, "test")
    assert res["outcomes"] == {"A": "invalid", "B": "invalid"}
    assert res["invalid_reasons"]["shared"] == ["generation_error: 1: 30 clues not reached in 50 attempts"]
    assert _run_json(tmp_path, "test")["status"] == "invalid"


def _tamper_head(s, tmp_path, rel, width):
    torch.save(_head(np.random.default_rng(99), width), s.ROOT / rel)


@pytest.mark.parametrize("target,expect", [
    ("z6", {"A": True, "B": False, "shared": False}),
    ("P4", {"A": False, "B": True, "shared": False}),
    ("P2", {"A": True, "B": True, "shared": True}),
    ("pairs", {"A": True, "B": True, "shared": True}),
])
def test_start_hash_categories(tmp_path, monkeypatch, target, expect):
    s, _ = _setup(tmp_path, monkeypatch)
    if target == "z6":
        _tamper_head(s, tmp_path, "runs/e5/lock/z6.pt", Z)
    elif target in ("P2", "P4"):
        _tamper_head(s, tmp_path, f"runs/e5/causal/heads/{target}.pt", D)
    else:
        pv = s.ROOT / "runs" / "e5" / "pairs" / "probe_val"
        a = np.load(pv / "a.npy")
        a[0, np.flatnonzero(a[0])[0]] = 0
        np.save(pv / "a.npy", a)
    status = s.run("dry", resume=False)
    res = _results(tmp_path, "dry")
    assert status == ("invalid" if expect["shared"] else "finished")
    assert bool(res["invalid_reasons"]["shared"]) == expect["shared"]
    assert (res["outcomes"]["A"] == "invalid") == expect["A"]
    assert (res["outcomes"]["B"] == "invalid") == expect["B"]
    if not expect["shared"]:
        assert len(res["pairs"]) == N  # the run continued for the other claim
        key = "component/z6_head" if target == "z6" else f"head/{target}"
        assert res["invalid_reasons"][expect["A"] and "A" or "B"] == [f"hash_mismatch: {key}"]


# --- test mode (review fixes 1, 2, 4): TEST generation redirected to a non-TEST namespace -------


def _redirect_generation(monkeypatch, replace=None):
    """`e5pairs.generate_pair` with seed 10 redirected to 10 + OFFSET; `replace` maps a raw index to
    the pair to return instead (internal-collision injection). Returns the list of raw indices asked."""
    real, asked = e5pairs.generate_pair, []

    def gen(seed, index):
        assert seed == e5pairs.PAIR_SEEDS["pairs_test"] == 10
        asked.append(index)
        if replace and index in replace:
            return replace[index]
        return real(seed + OFFSET, index)

    monkeypatch.setattr(e5pairs, "generate_pair", gen)
    return asked


def test_test_mode_screening_end_to_end(tmp_path, monkeypatch):
    s, _ = _setup(tmp_path, monkeypatch, test_inputs=True)
    real = e5pairs.generate_pair
    rejected = real(10 + OFFSET, 3)
    monkeypatch.setattr(s, "screening_corpus",
                        lambda P: ({"fake": [("ext-0", rejected.solution)]}, {"counts": {"fake": 1}}, None))
    asked = _redirect_generation(monkeypatch)
    assert s.run("test", resume=False) == "finished"

    assert asked == list(range(N_T + 1))  # raw-index stepping past the one external collision
    kept = [i for i in range(N_T + 1) if i != 3]
    z = np.load(tmp_path / "runs" / "test" / "pairs.npz", allow_pickle=False)
    assert z["ids"].tolist() == [f"e5pair-v1-{10 + OFFSET}-{i}" for i in kept]
    pairs = [real(10 + OFFSET, i) for i in kept]
    for key, attr in (("a", "a"), ("b", "b"), ("solutions", "solution")):
        assert z[key].dtype == np.uint8 and z[key].shape == (N_T, 81)
        assert np.array_equal(z[key], np.stack([getattr(p, attr) for p in pairs]))
    assert z["order"].tolist() == list(range(N_T))
    meta = json.loads(str(z["meta_json"]))
    screen = meta["screen"]
    assert (screen["applied"], screen["n_candidates"], screen["n_rejected"], screen["n_accepted"]) == (
        True, N_T + 1, 1, N_T)
    assert screen["log"][3] == {"index": 3, "pair_id": rejected.pair_id, "accepted": False,
                                "reason": "external_collision", "colliding_id": "ext-0"}
    assert meta["internal_collisions"] == []

    res = _results(tmp_path, "test")
    assert res["mode"] == "test" and res["n_pairs"] == N_T and list(res["pairs"]) == z["ids"].tolist()
    assert res["screening"]["n_rejected"] == 1 and "pilot_prediction_max_abs_diff" not in res
    log = json.loads((tmp_path / "out" / "test" / "screening_log.json").read_text(encoding="utf-8"))
    assert len(log["log"]) == N_T + 1 and log["log"][3]["accepted"] is False
    assert _run_json(tmp_path, "test")["status"] == "finished"

    # review fix 1: deleting the git-ignored run.json never reopens the single look
    before = (tmp_path / "out" / "test" / "results.json").read_bytes()
    (tmp_path / "runs" / "test" / "run.json").unlink()
    with pytest.raises(e5run.RunStateError, match="single look"):
        s.run("test", resume=False)
    assert (tmp_path / "out" / "test" / "results.json").read_bytes() == before
    assert not (tmp_path / "runs" / "test" / "run.json").exists()


def test_test_mode_internal_collision_stops_the_run(tmp_path, monkeypatch):
    from dataclasses import replace

    s, _ = _setup(tmp_path, monkeypatch, test_inputs=True)
    monkeypatch.setattr(s, "screening_corpus", lambda P: ({}, {"counts": {}}, None))
    twin = replace(e5pairs.generate_pair(10 + OFFSET, 2), pair_id=f"e5pair-v1-{10 + OFFSET}-5", index=5)
    _redirect_generation(monkeypatch, replace={5: twin})
    monkeypatch.setattr(s, "extract_batch", lambda *a, **k: pytest.fail("extraction after an internal collision"))
    assert s.run("test", resume=False) == "invalid"
    res = _results(tmp_path, "test")
    assert res["outcomes"] == {"A": "invalid", "B": "invalid"}
    assert res["invalid_reasons"]["shared"] == [
        f"internal_collision: e5pair-v1-{10 + OFFSET}-2 e5pair-v1-{10 + OFFSET}-5"]
    assert res["internal_collisions"] == [[f"e5pair-v1-{10 + OFFSET}-2", f"e5pair-v1-{10 + OFFSET}-5"]]
    assert _run_json(tmp_path, "test")["status"] == "invalid"
    assert (tmp_path / "out" / "test" / "screening_log.json").is_file()
    assert s.STOP_ROW in (tmp_path / "out" / "test" / "report.md").read_text(encoding="utf-8")


def _no_test_generation(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("TEST pair generation reached after a start refusal")

    monkeypatch.setattr(e5pairs, "generate_pair", boom)


def _nothing_started(tmp_path):
    rd = tmp_path / "runs" / "test"
    assert not rd.exists() or not any(rd.iterdir()), "a refused TEST start left something in RUN_DIR"
    assert not (tmp_path / "out" / "test").exists()


@pytest.mark.parametrize("exc", ["LockError", "DataIntegrityError"])
def test_test_mode_lock_failures_refuse_without_a_record(tmp_path, monkeypatch, exc):
    s, _ = _setup(tmp_path, monkeypatch, test_inputs=True)
    err = getattr(e5run, exc)

    def require_lock(manifest, dry_record):
        raise err("injected")

    monkeypatch.setattr(e5run, "require_lock", require_lock)
    _no_test_generation(monkeypatch)
    with pytest.raises(err, match="injected"):
        s.run("test", resume=False)
    _nothing_started(tmp_path)
    with pytest.raises(SystemExit) as ex:
        s.main(["--mode", "test"])
    assert ex.value.code == 2
    _nothing_started(tmp_path)


@pytest.mark.parametrize("target,category", [
    ("z6", "A"), ("P4", "B"), ("component/Q", "B"), ("P2", "shared"), ("checkpoint", "shared"),
    ("corpus", "shared"),
])
def test_test_mode_start_check_failures_refuse_without_a_record(tmp_path, monkeypatch, target, category):
    """Review fix 2: in test mode every start check of every §6 category refuses before start."""
    s, _ = _setup(tmp_path, monkeypatch, test_inputs=True)
    monkeypatch.setattr(s, "screening_corpus", lambda P: ({}, {"counts": {}}, None))
    if target == "z6":
        _tamper_head(s, tmp_path, "runs/e5/lock/z6.pt", Z)
    elif target in ("P2", "P4"):
        _tamper_head(s, tmp_path, f"runs/e5/causal/heads/{target}.pt", D)
    elif target == "component/Q":
        np.save(s.ROOT / "runs" / "e5" / "lock" / "Q.npy", np.zeros((D, 9)))
    elif target == "checkpoint":
        def bad(d):
            raise wp2.DataIntegrityError("checkpoint differs")

        monkeypatch.setattr(s, "verify_checkpoints", bad)
    else:
        monkeypatch.setattr(s, "screening_corpus", lambda P: ({}, {}, "screening_corpus_hash: WP2 TEST differs"))
    _no_test_generation(monkeypatch)
    with pytest.raises(s.StartRefused) as ex:
        s.run("test", resume=False)
    if target != "corpus":
        assert f"{category}: " in str(ex.value)
    else:
        assert "screening_corpus_hash" in str(ex.value)
    _nothing_started(tmp_path)
    with pytest.raises(SystemExit) as ex2:
        s.main(["--mode", "test"])
    assert ex2.value.code == 2
    _nothing_started(tmp_path)


def test_dry_mode_still_records_claim_specific_start_failures(tmp_path, monkeypatch):
    """Dry modes keep the §6 behaviour: a claim-B start mismatch is recorded and the run continues."""
    s, _ = _setup(tmp_path, monkeypatch)
    np.save(s.ROOT / "runs" / "e5" / "lock" / "Q.npy", np.zeros((D, 9)))
    assert s.run("dry", resume=False) == "finished"
    res = _results(tmp_path, "dry")
    assert res["invalid_reasons"]["B"] == ["hash_mismatch: component/Q"] and res["outcomes"]["B"] == "invalid"


# --- non-finite stops at every runner-level gate (protocol §6) ----------------------------------


def _assert_non_finite_stop(tmp_path, s, name):
    assert s.run("dry", resume=False) == "invalid"
    res = _results(tmp_path, "dry")
    assert res["outcomes"] == {"A": "invalid", "B": "invalid"}
    assert res["invalid_reasons"]["shared"] == [f"non_finite: {name}"]
    assert _run_json(tmp_path, "dry")["status"] == "invalid"


def test_non_finite_probe_prediction_stops(tmp_path, monkeypatch):
    s, _ = _setup(tmp_path, monkeypatch)
    real = s.head_probs

    def nan_probs(sd, feats, empty, batch):
        per_seed, mean = real(sd, feats, empty, batch=batch)
        mean = mean.copy()
        r, c = np.argwhere(empty)[0]
        mean[r, c, 0] = np.nan
        return per_seed, mean

    monkeypatch.setattr(s, "head_probs", nan_probs)
    _assert_non_finite_stop(tmp_path, s, "probes/P2")
    assert not (tmp_path / "runs" / "dry" / "causal").exists()


def test_non_finite_per_pair_a_value_stops(tmp_path, monkeypatch):
    s, _ = _setup(tmp_path, monkeypatch)
    real = s.pair_scores

    def nan_scores(pred, mask, empty, same, n):
        out = real(pred, mask, empty, same, n)
        return {**out, "w": [np.nan] * n}

    monkeypatch.setattr(s, "pair_scores", nan_scores)
    _assert_non_finite_stop(tmp_path, s, "per_pair_A")
    assert not (tmp_path / "runs" / "dry" / "decisions.json").exists()


def test_non_finite_per_pair_b_value_stops(tmp_path, monkeypatch):
    base = _fake_evaluate()

    def nan_evaluate(*a, **k):
        out = base(*a, **k)
        out["directed"] = out["directed"].copy()
        out["directed"][0, 0] = np.nan
        return out

    s, _ = _setup(tmp_path, monkeypatch, evaluate=nan_evaluate)
    _assert_non_finite_stop(tmp_path, s, "per_pair_B")


def test_non_finite_decision_input_stops(tmp_path, monkeypatch):
    s, _ = _setup(tmp_path, monkeypatch)
    real = s.decide

    def nan_decide(*a, **k):
        dec = real(*a, **k)
        dec["inputs"]["A2"] = [np.nan] + list(dec["inputs"]["A2"][1:])
        return dec

    monkeypatch.setattr(s, "decide", nan_decide)
    _assert_non_finite_stop(tmp_path, s, "decision_inputs")
    assert not (tmp_path / "runs" / "dry" / "decisions.json").exists()
