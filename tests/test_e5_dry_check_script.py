"""Model-free tests of scripts/e5_dry_check.py (protocol §9.4 pass rule).

The dry and permuted dry runs are produced by the real runner `scripts/e5_test.py` with the
deterministic fakes of `test_e5_test_script.py`, so every file layout is the runner's own; the
pilot references (`runs/e5/pilot/{P2,z6}__shared__none.npy`, `runs/e5/causal/primary.npz`,
`runs/e5/acts/probe_val/`) are then written from the dry run's raw outputs in the pilot layouts.
The tree is built once per module and copied for each test."""

import importlib.util
import json
import shutil

import numpy as np
import pytest

from conftest import ROOT
from ncm_sudoku import e5run, wp2
from ncm_sudoku.e5batch import CONDITIONS
from test_e5_test_script import N, _fake_evaluate, _fake_extract, _setup


CLEAN = {"commit": "c" * 40, "dirty": False, "diff_sha256": None}


def _mod():
    spec = importlib.util.spec_from_file_location("e5_dry_check", ROOT / "scripts" / "e5_dry_check.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _npz(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def _dirs(root):
    return ({k: root / "runs" / "e5" / k for k in e5run.RUN_DIR},
            {k: root / "experiments" / "e5" / k for k in e5run.OUT_DIR})


def _write_pilot_refs(root):
    """Pilot references in the pilot layouts, taken from the dry run's raw outputs (raw order)."""
    rd = root / "runs" / "e5" / "dry"
    pr = _npz(rd / "probes.npz")
    (root / "runs" / "e5" / "pilot").mkdir(parents=True)
    for rep in ("P2", "z6"):
        np.save(root / "runs" / "e5" / "pilot" / f"{rep}__shared__none.npy", pr[f"{rep}_mean"])
    for member in "ab":
        batches = [_npz(rd / "extract" / member / f"batch_{k}.npz") for k in range(N // 50)]
        acts = root / "runs" / "e5" / "acts" / "probe_val" / member
        acts.mkdir(parents=True)
        for key in ("prefix_cells", "z6", "codes", "solved"):
            np.save(acts / f"{key}.npy", np.concatenate([b[key] for b in batches]))
    meta, directed = [], []
    for order in ("ab", "ba"):
        for k in range(N // 50):
            z = _npz(rd / "causal" / f"{order}_batch_{k}.npz")
            meta.append(np.stack([z["pair_index"], z["order"]], axis=1))
            directed.append(z["directed"])
    np.savez(root / "runs" / "e5" / "causal" / "primary.npz", conditions=np.array(CONDITIONS),
             meta=np.concatenate(meta), directed=np.concatenate(directed),
             undirected=np.zeros((2 * N, len(CONDITIONS))))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    base = tmp_path_factory.mktemp("built")
    with pytest.MonkeyPatch.context() as mp:
        s, ids = _setup(base, mp)
        root = base / "root"
        run_dir, out_dir = _dirs(root)
        mp.setattr(e5run, "RUN_DIR", run_dir)
        mp.setattr(e5run, "OUT_DIR", out_dir)
        assert s.run("dry", resume=False) == "finished"
        mp.setattr(s, "extract_batch", _fake_extract())
        mp.setattr(s, "evaluate_batch", _fake_evaluate())
        assert s.run("dry_perm", resume=False) == "finished"
    _write_pilot_refs(root)
    return root, ids


@pytest.fixture
def tree(built, tmp_path, monkeypatch):
    src, ids = built
    root = tmp_path / "root"
    shutil.copytree(src, root)
    m = _mod()
    run_dir, out_dir = _dirs(root)
    monkeypatch.setattr(m, "ROOT", root)
    monkeypatch.setattr(e5run, "RUN_DIR", run_dir)
    monkeypatch.setattr(e5run, "OUT_DIR", out_dir)
    monkeypatch.setattr(m, "code_state", lambda: dict(CLEAN))
    for mode in ("dry", "dry_perm"):
        _edit_results(root, mode, lambda res: res.update(code_state=dict(CLEAN)))
    return m, root, ids


def _main(m):
    with pytest.raises(SystemExit) as e:
        m.main([])
    return e.value.code


def _record(root):
    return json.loads((root / "experiments" / "e5" / "dry" / "check.json").read_text(encoding="utf-8"))


def _edit_results(root, mode, fn):
    p = root / "experiments" / "e5" / mode / "results.json"
    res = json.loads(p.read_text(encoding="utf-8"))
    fn(res)
    p.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")


def _edit_primary(root, fn):
    p = root / "runs" / "e5" / "causal" / "primary.npz"
    z = _npz(p)
    fn(z)
    np.savez(p, **z)


def test_all_equal_passes_and_record_has_the_lock_format(tree):
    m, root, ids = tree
    assert _main(m) == 0
    rec = _record(root)
    assert rec["passed"] is True
    assert all(rec["parts"][k]["passed"] for k in ("code_state", "a", "b", "c", "d", "e", "run_records")), \
        rec["parts"]
    assert rec["parts"]["c"]["raw_equal"] and rec["parts"]["c"]["pair_means_equal"]
    sidecar = (root / "experiments" / "e5" / "dry" / "check.sha256").read_text(encoding="utf-8").strip()
    assert sidecar == wp2.file_sha256(root / "experiments" / "e5" / "dry" / "check.json")
    assert rec["ids_sha256"] == json.loads((root / "experiments" / "e5" / "pairs.json").read_text(
        encoding="utf-8"))["subsets"]["probe_val"]["sha256"]["ids"]
    for rel, sha in rec["hashes"].items():
        assert "\\" not in rel and not rel.startswith("/")
        base = root if (root / rel).is_file() else ROOT
        assert wp2.file_sha256(base / rel) == sha
    for rel in ("runs/e5/pilot/P2__shared__none.npy", "runs/e5/pilot/z6__shared__none.npy",
                "runs/e5/causal/primary.npz", "experiments/e5/dry/results.json",
                "experiments/e5/dry_perm/results.json", "scripts/e5_test.py", "src/ncm_sudoku/e5stats.py",
                "runs/e5/causal/heads/P2.pt", "runs/e5/lock/Q.npy", "src/ncm_sudoku/e5pilot.py",
                "runs/e5/pairs/probe_val/a.npy", "runs/e5/acts/probe_val/b/prefix_cells.npy"):
        assert rel in rec["hashes"]
    assert set(rec["tie_rule_effect"]) == {"P2", "z6"}
    assert set(rec["prediction_max_abs_diff"]) == {"dry_vs_pilot", "dry_perm_vs_dry"}
    assert rec["prediction_max_abs_diff"]["dry_vs_pilot"]["P2"]["max_abs_diff"] == 0.0


def test_code_files_cover_every_module_the_runner_can_use(tree):
    """Review fix 3: the approval hashes the whole package, both E5 scripts, the environment lock and
    the protocol, so require_lock catches a change to any module the runner imports."""
    m, root, _ = tree
    package = {f"src/ncm_sudoku/{p.name}" for p in (ROOT / "src" / "ncm_sudoku").glob("*.py")}
    named = {"scripts/e5_test.py", "scripts/e5_dry_check.py", "pyproject.toml", "uv.lock", "e5_protocol_v1.md"}
    assert set(m.CODE_FILES) == package | named and len(m.CODE_FILES) == len(package | named)
    assert _main(m) == 0
    hashes = _record(root)["hashes"]
    for rel in package | named:
        assert hashes[rel] == wp2.file_sha256(ROOT / rel)


def test_one_ulp_off_per_pair_value_fails_part_b(tree):
    m, root, ids = tree

    def bump(res):
        row = res["pairs"][ids[7]]
        row["w_Z"] = float(np.nextafter(row["w_Z"], np.inf))

    _edit_results(root, "dry", bump)
    assert _main(m) == 1
    rec = _record(root)
    assert rec["passed"] is False
    assert rec["parts"]["b"]["passed"] is False
    assert any("w_Z" in r and ids[7] in r for r in rec["parts"]["b"]["reasons"])
    assert rec["parts"]["c"]["passed"] is True


def test_swapped_orders_fail_part_c_although_pair_means_agree(tree):
    m, root, ids = tree
    j = 3

    def swap(z):
        meta = z["meta"]
        ab = np.flatnonzero((meta[:, 0] == j) & (meta[:, 1] == 0))[0]
        ba = np.flatnonzero((meta[:, 0] == j) & (meta[:, 1] == 1))[0]
        assert not np.array_equal(z["directed"][ab], z["directed"][ba])
        z["directed"][[ab, ba]] = z["directed"][[ba, ab]]

    _edit_primary(root, swap)
    assert _main(m) == 1
    c = _record(root)["parts"]["c"]
    assert c["passed"] is False and c["raw_equal"] is False
    assert c["pair_means_equal"] is True and c["decision_inputs_equal"] is True
    assert any(ids[j] in r for r in c["reasons"])


def test_condition_missing_from_one_side_fails_part_c(tree):
    m, root, _ = tree
    hv = CONDITIONS.index("hv")

    def drop(z):
        keep = [i for i in range(len(CONDITIONS)) if i != hv]
        z["conditions"] = z["conditions"][keep]
        z["directed"] = z["directed"][:, keep]

    _edit_primary(root, drop)
    assert _main(m) == 1
    c = _record(root)["parts"]["c"]
    assert c["passed"] is False and any("hv" in r for r in c["reasons"])


def test_conditions_are_matched_by_name_not_position(tree):
    m, root, _ = tree

    def reorder(z):
        perm = np.arange(len(CONDITIONS))[::-1]
        z["conditions"] = z["conditions"][perm]
        z["directed"] = z["directed"][:, perm]

    _edit_primary(root, reorder)
    assert _main(m) == 0


def test_invalid_reason_in_dry_run_fails_part_d(tree):
    m, root, _ = tree
    _edit_results(root, "dry", lambda res: res["invalid_reasons"]["B"].append("written_rows"))
    assert _main(m) == 1
    d = _record(root)["parts"]["d"]
    assert d["passed"] is False and any("written_rows" in r for r in d["reasons"])


def test_permuted_run_value_difference_fails_part_e(tree):
    m, root, ids = tree

    def bump(res):
        row = res["pairs"][ids[11]]
        row["Q"] = float(np.nextafter(row["Q"], -np.inf))

    _edit_results(root, "dry_perm", bump)
    assert _main(m) == 1
    rec = _record(root)
    assert rec["parts"]["e"]["passed"] is False
    assert any(ids[11] in r and "Q" in r for r in rec["parts"]["e"]["reasons"])
    assert rec["parts"]["b"]["passed"] and rec["parts"]["c"]["passed"]


def test_tampered_raw_stage_file_fails_run_records(tree):
    m, root, _ = tree
    p = root / "runs" / "e5" / "dry_perm" / "causal" / "ba_batch_2.npz"
    z = _npz(p)
    z["directed"][0, 0] = np.nextafter(z["directed"][0, 0], np.inf)
    np.savez(p, **z)
    assert _main(m) == 1
    rec = _record(root)
    assert rec["parts"]["run_records"]["passed"] is False
    assert rec["parts"]["e"]["passed"] is False


def test_missing_file_fails_closed_with_a_record(tree):
    m, root, _ = tree
    (root / "experiments" / "e5" / "dry_perm" / "results.json").unlink()
    assert _main(m) == 1
    rec = _record(root)
    assert rec["passed"] is False and rec["parts"]["e"]["passed"] is False
    assert any("missing" in r for r in rec["hash_problems"])


def test_unreadable_input_exits_nonzero_without_a_record(tree):
    m, root, _ = tree
    out = root / "experiments" / "e5" / "dry"
    (out / "check.json").write_text("{}", encoding="utf-8")
    (out / "check.sha256").write_text("x\n", encoding="utf-8")
    (root / "runs" / "e5" / "causal" / "primary.npz").write_bytes(b"not an npz")
    assert _main(m) == 2
    assert not (out / "check.json").exists() and not (out / "check.sha256").exists()


def test_dirty_dry_run_fails_code_state(tree):
    m, root, _ = tree
    _edit_results(root, "dry_perm", lambda res: res["code_state"].update(dirty=True))
    assert _main(m) == 1
    rec = _record(root)
    assert rec["passed"] is False and rec["parts"]["code_state"]["passed"] is False
    assert all(rec["parts"][k]["passed"] for k in ("a", "b", "c", "d", "e", "run_records"))


def test_check_at_another_commit_fails_code_state(tree, monkeypatch):
    m, root, _ = tree
    monkeypatch.setattr(m, "code_state", lambda: {**CLEAN, "commit": "d" * 40})
    assert _main(m) == 1
    cs = _record(root)["parts"]["code_state"]
    assert cs["passed"] is False and any("commits differ" in r for r in cs["reasons"])


def test_missing_code_state_key_fails(tree):
    m, root, _ = tree
    _edit_results(root, "dry", lambda res: res["code_state"].pop("dirty"))
    assert _main(m) == 1
    assert _record(root)["parts"]["code_state"]["passed"] is False


def test_fixed_permutation_matches_the_runner():
    from test_e5_test_script import _mod as runner

    assert np.array_equal(_mod().fixed_permutation(N), runner().PERMUTATION)


def test_other_valid_permutation_fails_part_e(tree):
    m, root, ids = tree
    p = root / "runs" / "e5" / "dry_perm" / "pairs.npz"
    z = _npz(p)
    other = (21 * np.arange(N) + 3) % N
    assert sorted(other.tolist()) == list(range(N)) and (other % 50 != np.arange(N) % 50).all()
    z["order"] = other
    np.savez(p, **z)
    from ncm_sudoku import subsets
    _edit_results(root, "dry_perm", lambda res: res["inputs"].update(order=subsets.sha256_ids([ids[i] for i in other])))
    assert _main(m) == 1
    e = _record(root)["parts"]["e"]
    assert e["passed"] is False and any("fixed permutation" in r for r in e["reasons"])


def test_wrong_recorded_threads_fails_part_d(tree):
    m, root, _ = tree
    _edit_results(root, "dry", lambda res: res["inputs"].update(threads="3"))
    assert _main(m) == 1
    d = _record(root)["parts"]["d"]
    assert d["passed"] is False and any("threads" in r for r in d["reasons"])


def test_nan_in_a_row_with_discordant_bits_fails_part_b(tree):
    m, root, ids = tree

    def blank(res):
        row = res["pairs"][ids[5]]
        assert row["n_disc"] > 0
        row["w_P2"] = None

    _edit_results(root, "dry", blank)
    assert _main(m) == 1
    b = _record(root)["parts"]["b"]
    assert b["passed"] is False and any("w_P2" in r and ids[5] in r for r in b["reasons"])


def test_string_value_in_a_row_fails_part_b(tree):
    m, root, ids = tree

    def stringify(res):
        res["pairs"][ids[2]]["w_Z"] = str(res["pairs"][ids[2]]["w_Z"])

    _edit_results(root, "dry", stringify)
    assert _main(m) == 1
    b = _record(root)["parts"]["b"]
    assert b["passed"] is False and any("w_Z" in r for r in b["reasons"])


def test_unexpected_error_exits_2_without_a_record(tree, monkeypatch):
    m, root, _ = tree

    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(m, "_hash_files", boom)
    assert _main(m) == 2
    assert not (root / "experiments" / "e5" / "dry" / "check.json").exists()
