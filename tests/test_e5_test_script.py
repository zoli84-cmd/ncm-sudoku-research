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
D, Z = 4, 3  # fake residual and Z<=6 state widths


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


def _setup(tmp_path, monkeypatch, extract=None, evaluate=None):
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
    (root / "experiments" / "e5" / "pairs.json").write_text(
        json.dumps({"subsets": {"probe_val": {"count": N, "ids": ids, "sha256": sha}}}), encoding="utf-8")

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
    monkeypatch.setattr(s.Runner, "_corpus", lambda self: ({}, {"counts": {}}))
    real = e5pairs.generate_pair

    def gen(seed, index):
        assert seed == 10
        if index == 1:
            raise GenerationError("30 clues not reached in 50 attempts")
        return real(seed, index)

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
