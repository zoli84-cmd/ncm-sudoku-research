"""Model-free tests of scripts/e5_manifest.py (protocol §10 hash manifest).

Builds a small synthetic repository root under `tmp_path` with every input
`scripts/e5_manifest.py` reads (checkpoints, released data, screening corpus, E5 pair arrays,
lock components, code files, the dry-run record), runs `build_manifest(root)` against it and
checks the result with the real `ncm_sudoku.e5run.verify_manifest` (ROOT monkeypatched to the
fixture root, as `tests/test_e5run.py` already does for that function)."""

import importlib.util
import json

import numpy as np
import pytest

from conftest import ROOT
from ncm_sudoku import e5run, subsets, wp2


def _mod():
    spec = importlib.util.spec_from_file_location("e5_manifest", ROOT / "scripts" / "e5_manifest.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def _write_ids_and_solutions(d, ids, n_cols=9):
    d.mkdir(parents=True, exist_ok=True)
    (d / "ids.json").write_text(json.dumps(ids) + "\n", encoding="utf-8", newline="\n")
    sol = np.arange(len(ids) * n_cols, dtype=np.uint8).reshape(len(ids), n_cols)
    np.save(d / "solutions.npy", sol)


def build_fixture_root(root) -> None:
    """A minimal, self-contained tree covering every source `build_manifest` reads, so the gate and
    CAL screening files are already present and no real puzzle generation ever runs in this test."""
    (root / "e5_protocol_v1.md").write_text("fake protocol\n", encoding="utf-8")
    (root / "uv.lock").write_text("fake lock\n", encoding="utf-8")
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    for name in ("e5_test.py", "e5_pilot.py", "e5_pilot_ref.py"):
        (root / "scripts" / name).write_text(f"# fake {name}\n", encoding="utf-8")
    (root / "src" / "ncm_sudoku").mkdir(parents=True, exist_ok=True)
    for name in ("alpha.py", "beta.py"):
        (root / "src" / "ncm_sudoku" / name).write_text(f"# fake {name}\n", encoding="utf-8")

    # checkpoints
    ckpt_rel = "sudoku/hard/generator.pt"
    (root / "checkpoints" / "sudoku" / "hard").mkdir(parents=True, exist_ok=True)
    (root / "checkpoints" / ckpt_rel).write_bytes(b"fake checkpoint bytes")
    _write_json(root / "experiments" / "provenance" / "checkpoints.json",
                {"files": {ckpt_rel: {"bytes": 21}}, "repo_id": "fake/repo", "revision": "deadbeef"})

    # released data
    rel_dir = root / "data" / "released" / "sudoku" / "hard"
    rel_dir.mkdir(parents=True, exist_ok=True)
    (rel_dir / "puzzles.pickle").write_bytes(b"fake puzzles")
    (rel_dir / "solutions.pickle").write_bytes(b"fake solutions")
    _write_json(root / "experiments" / "provenance" / "released_data.json",
                {"hard": {"files": {"sudoku/hard/puzzles.pickle": {}, "sudoku/hard/solutions.pickle": {}},
                          "repo_id": "fake/dataset", "repo_type": "dataset", "revision": "cafef00d"}})

    # screening corpus: gate and cal already materialized (so ensure_screening_corpus is a no-op),
    # plus the three subsets reused from earlier steps
    _write_ids_and_solutions(root / "runs" / "e5" / "lock" / "screening" / "gate", ["gate-0", "gate-1"])
    _write_ids_and_solutions(root / "runs" / "e5" / "lock" / "screening" / "cal", ["cal-0", "cal-1"])
    _write_ids_and_solutions(root / "runs" / "e3prep" / "probe_train", ["pt-0", "pt-1", "pt-2"])
    _write_ids_and_solutions(root / "runs" / "e3prep" / "probe_val", ["pv-0"])
    _write_ids_and_solutions(root / "runs" / "lock" / "test", ["t-0", "t-1"])

    # E5 counterfactual pairs
    for name, ns in (("probe_train", 8), ("probe_val", 9)):
        d = root / "runs" / "e5" / "pairs" / name
        d.mkdir(parents=True, exist_ok=True)
        ids = [f"{name}-0", f"{name}-1"]
        (d / "ids.json").write_text(json.dumps(ids) + "\n", encoding="utf-8", newline="\n")
        for member in ("a", "b", "solutions"):
            np.save(d / f"{member}.npy", np.zeros((2, 81), dtype=np.uint8))
    _write_json(root / "experiments" / "e5" / "pairs.json",
                {"subsets": {"probe_train": {"seed_namespace": 8, "storage": "runs/e5/pairs/probe_train"},
                            "probe_val": {"seed_namespace": 9, "storage": "runs/e5/pairs/probe_val"}}})

    # lock components and causal heads
    lock_dir = root / "runs" / "e5" / "lock"
    for name in ("z6.pt", "W.npy", "Q.npy", "H.npy", "R.npy", "Pi.npy"):
        (lock_dir / name).write_bytes(f"fake {name}".encode())
    heads_dir = root / "runs" / "e5" / "causal" / "heads"
    heads_dir.mkdir(parents=True, exist_ok=True)
    for rep in ("P2", "P4", "P8"):
        (heads_dir / f"{rep}.pt").write_bytes(f"fake {rep}".encode())
    _write_json(root / "experiments" / "e5" / "lock" / "components.json",
                {"files": {k: {"file": f"runs/e5/lock/{k}.npy" if k != "z6_head" else "runs/e5/lock/z6.pt"}
                          for k in ("z6_head", "W", "Q", "H", "R", "Pi")},
                 "verified_heads": {rep: {"file": f"runs/e5/causal/heads/{rep}.pt"} for rep in ("P2", "P4", "P8")}})

    # extra artifacts the dry-run record's own "hashes" dict names (protocol §9.4): some already
    # covered by an earlier bucket (deduplicated), most not (get their own manifest entry)
    (root / "scripts" / "e5_dry_check.py").write_text("# fake e5_dry_check.py\n", encoding="utf-8")
    _write_json(root / "experiments" / "e5" / "causal" / "heads.json", {"heads": {}})
    _write_json(root / "experiments" / "e5" / "dry" / "results.json", {"mode": "dry"})
    _write_json(root / "experiments" / "e5" / "dry_perm" / "results.json", {"mode": "dry_perm"})
    _write_json(root / "runs" / "e5" / "dry" / "run.json", {"status": "finished"})
    _write_json(root / "runs" / "e5" / "dry_perm" / "run.json", {"status": "finished"})
    pilot_dir = root / "runs" / "e5" / "pilot"
    pilot_dir.mkdir(parents=True, exist_ok=True)
    np.save(pilot_dir / "P2__shared__none.npy", np.zeros((2, 81, 9)))
    np.save(pilot_dir / "z6__shared__none.npy", np.zeros((2, 81, 9)))
    np.savez(root / "runs" / "e5" / "causal" / "primary.npz", directed=np.zeros(3))
    for member in "ab":
        acts_dir = root / "runs" / "e5" / "acts" / "probe_val" / member
        acts_dir.mkdir(parents=True, exist_ok=True)
        for key in ("codes", "solved", "prefix_cells", "z6"):
            np.save(acts_dir / f"{key}.npy", np.zeros(3))

    hashable = {
        # already covered by another bucket: must not get a duplicate entry
        "runs/e5/lock/W.npy": root / "runs" / "e5" / "lock" / "W.npy",
        "runs/e5/pairs/probe_val/ids.json": root / "runs" / "e5" / "pairs" / "probe_val" / "ids.json",
        # not covered anywhere else: each must get its own entry
        "experiments/e5/pairs.json": root / "experiments" / "e5" / "pairs.json",
        "experiments/e5/causal/heads.json": root / "experiments" / "e5" / "causal" / "heads.json",
        "experiments/e5/lock/components.json": root / "experiments" / "e5" / "lock" / "components.json",
        "experiments/e5/dry/results.json": root / "experiments" / "e5" / "dry" / "results.json",
        "experiments/e5/dry_perm/results.json": root / "experiments" / "e5" / "dry_perm" / "results.json",
        "runs/e5/dry/run.json": root / "runs" / "e5" / "dry" / "run.json",
        "runs/e5/dry_perm/run.json": root / "runs" / "e5" / "dry_perm" / "run.json",
        "scripts/e5_dry_check.py": root / "scripts" / "e5_dry_check.py",
        "runs/e5/pilot/P2__shared__none.npy": pilot_dir / "P2__shared__none.npy",
        "runs/e5/pilot/z6__shared__none.npy": pilot_dir / "z6__shared__none.npy",
        "runs/e5/causal/primary.npz": root / "runs" / "e5" / "causal" / "primary.npz",
        "runs/e5/acts/probe_val/a/codes.npy": root / "runs" / "e5" / "acts" / "probe_val" / "a" / "codes.npy",
        "runs/e5/acts/probe_val/b/z6.npy": root / "runs" / "e5" / "acts" / "probe_val" / "b" / "z6.npy",
    }

    # dry-run record
    dry_dir = root / "experiments" / "e5" / "dry"
    dry_dir.mkdir(parents=True, exist_ok=True)
    hashes = {rel: wp2.file_sha256(p) for rel, p in hashable.items()}
    _write_json(dry_dir / "check.json", {"passed": True, "hashes": hashes})
    (dry_dir / "check.sha256").write_text(wp2.file_sha256(dry_dir / "check.json") + "\n", encoding="utf-8")


@pytest.fixture
def fixture_root(tmp_path):
    build_fixture_root(tmp_path)
    return tmp_path


def test_build_manifest_verifies_clean(fixture_root, monkeypatch):
    m = _mod()
    manifest = m.build_manifest(fixture_root)
    assert manifest["entries"]
    p = fixture_root / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(e5run, "ROOT", fixture_root)
    e5run.verify_manifest(p)  # does not raise: --verify passes on a fresh manifest


def test_verify_fails_naming_the_tampered_entry(fixture_root, monkeypatch):
    m = _mod()
    manifest = m.build_manifest(fixture_root)
    p = fixture_root / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(e5run, "ROOT", fixture_root)

    target = next(e for e in manifest["entries"] if e["name"] == "test_runner")
    target_path = fixture_root / target["path"]
    data = bytearray(target_path.read_bytes())
    data[0] ^= 0xFF  # one-byte change
    target_path.write_bytes(bytes(data))

    with pytest.raises(e5run.DataIntegrityError, match="test_runner"):
        e5run.verify_manifest(p)


def test_ids_are_hashed_with_sha256_ids_not_sha256_array(fixture_root):
    m = _mod()
    manifest = m.build_manifest(fixture_root)
    # the id-list buckets (screening corpus, E5 pairs), not the dry record's own plain-file-hash
    # entries at the same paths (a different, deliberately separate, hashing convention)
    ids_entries = [e for e in manifest["entries"]
                   if e["path"].endswith("ids.json") and not e["name"].startswith("dry_hash:")]
    assert ids_entries
    for e in ids_entries:
        assert e["format"] == "sha256_ids"
        ids = json.loads((fixture_root / e["path"]).read_text(encoding="utf-8"))
        assert e["sha256"] == subsets.sha256_ids(ids)
        # never the array hash of the same bytes (different format entirely; sha256_array
        # requires a numeric array and would raise on a list of strings)
        with pytest.raises((ValueError, TypeError)):
            subsets.sha256_array(ids)


def test_entry_names_are_unique(fixture_root):
    m = _mod()
    manifest = m.build_manifest(fixture_root)
    names = [e["name"] for e in manifest["entries"]]
    assert len(names) == len(set(names))


def test_every_entry_has_the_required_shape(fixture_root):
    m = _mod()
    manifest = m.build_manifest(fixture_root)
    for e in manifest["entries"]:
        assert set(e) == {"name", "path", "format", "sha256", "retrieval"}
        assert e["format"] in ("file", "sha256_ids", "sha256_array")
        assert isinstance(e["sha256"], str) and len(e["sha256"]) == 64
        assert "\\" not in e["path"] and not e["path"].startswith("/")


def test_ensure_screening_corpus_is_a_noop_when_already_present(fixture_root, monkeypatch):
    m = _mod()
    called = []
    monkeypatch.setattr(m.subsets, "generate_subset", lambda name, n: called.append(name))
    m.ensure_screening_corpus(fixture_root)
    assert called == []


def test_every_dry_record_hash_is_covered_by_the_manifest(fixture_root):
    """Protocol §10: "the approved dry-run record and the hashes it states" - every path named
    in check.json's own `hashes` dict must appear in the manifest (whether via a dedicated
    dry_hash:* entry or an earlier bucket) with a matching SHA-256."""
    m = _mod()
    manifest = m.build_manifest(fixture_root)
    by_path = {e["path"]: e for e in manifest["entries"]}
    record = json.loads((fixture_root / "experiments" / "e5" / "dry" / "check.json").read_text(encoding="utf-8"))
    assert record["hashes"]
    for rel, expected in record["hashes"].items():
        assert rel in by_path, f"{rel} has no manifest entry"
        assert by_path[rel]["sha256"] == expected, f"{rel}: manifest sha256 differs from the dry record's"
        assert by_path[rel]["format"] == "file"


def test_dry_record_entries_skip_only_matching_hashes(fixture_root):
    """A path already in the manifest is only skipped by `dry_record_hash_entries` when an
    existing entry's SHA-256 already equals the record's value for that path (same hashing
    convention); a different convention at the same path (e.g. `sha256_ids` vs. the record's
    plain file hash) still gets its own `dry_hash:*` entry."""
    m = _mod()
    manifest = m.build_manifest(fixture_root)
    names = [e["name"] for e in manifest["entries"]]
    paths = [e["path"] for e in manifest["entries"]]
    # same convention (plain file hash both times): no duplicate
    assert paths.count("runs/e5/lock/W.npy") == 1
    assert "dry_hash:runs/e5/lock/W.npy" not in names
    # different convention at the same path (sha256_ids vs. the record's plain file hash): the
    # dry record's own entry is still added even though the path already appears elsewhere
    assert paths.count("runs/e5/pairs/probe_val/ids.json") == 2
    assert "dry_hash:runs/e5/pairs/probe_val/ids.json" in names
    # not covered by any other bucket at all: a fresh entry
    assert "dry_hash:experiments/e5/pairs.json" in names


def test_verify_rejects_missing_entry(fixture_root, monkeypatch):
    m = _mod()
    manifest = m.build_manifest(fixture_root)
    (fixture_root / "runs" / "e5" / "lock" / "W.npy").unlink()
    p = fixture_root / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(e5run, "ROOT", fixture_root)
    with pytest.raises(e5run.DataIntegrityError, match="component:W"):
        e5run.verify_manifest(p)


# --- review fix 3: the manifest pins only code the dry-run approval ran ---------------------------


def _git(cwd, *args):
    import subprocess

    return subprocess.check_output(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                                    "-c", "core.autocrlf=false", *args], cwd=cwd, text=True,
                                   stderr=subprocess.DEVNULL).strip()


def _approved_repo(root):
    """A throwaway repo whose dry-run record names the commit of its first (and only) commit."""
    _git(root, "init", "-q")
    for rel in ("src/ncm_sudoku/a.py", "scripts/e5_test.py", "scripts/e5_dry_check.py", "scripts/other.py",
                "pyproject.toml", "uv.lock", "e5_protocol_v1.md", "docs/notes.md"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(f"# {rel}\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "dry runs")
    commit = _git(root, "rev-parse", "HEAD")
    _write_json(root / "experiments" / "e5" / "dry" / "check.json", {"passed": True, "code_state": {"commit": commit}})
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "approval")
    return commit


def test_approved_code_unchanged_passes(tmp_path):
    m = _mod()
    _approved_repo(tmp_path)
    # a later commit outside the approved paths does not block the manifest
    (tmp_path / "scripts" / "other.py").write_text("# changed\n", encoding="utf-8")
    (tmp_path / "docs" / "notes.md").write_text("changed\n", encoding="utf-8")
    _git(tmp_path, "commit", "-qam", "unrelated")
    assert m.approved_code_problem(tmp_path) is None


@pytest.mark.parametrize("rel", ["src/ncm_sudoku/a.py", "scripts/e5_test.py", "scripts/e5_dry_check.py",
                                 "pyproject.toml", "uv.lock", "e5_protocol_v1.md", "src/ncm_sudoku/new.py"])
def test_approved_code_changed_since_the_dry_check_refuses(tmp_path, rel):
    m = _mod()
    commit = _approved_repo(tmp_path)
    (tmp_path / rel).write_text("# changed after the dry check\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "code change")
    problem = m.approved_code_problem(tmp_path)
    assert problem and commit in problem and "changed" in problem


def test_approved_code_doc_only_change_under_src_passes(tmp_path):
    """A markdown-only edit under `src/` (e.g. `src/ncm_sudoku/AGENTS.md`) carries no integrity risk
    and must not block the manifest, while a `.py` change under `src/` still does."""
    m = _mod()
    _approved_repo(tmp_path)
    (tmp_path / "src" / "ncm_sudoku" / "AGENTS.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "ncm_sudoku" / "AGENTS.md").write_text("# doc change\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "doc-only change under src")
    assert m.approved_code_problem(tmp_path) is None


def test_approved_code_record_without_commit_or_unknown_commit_refuses(tmp_path):
    m = _mod()
    _approved_repo(tmp_path)
    rec = tmp_path / "experiments" / "e5" / "dry" / "check.json"
    _write_json(rec, {"passed": True})
    assert "code_state.commit" in m.approved_code_problem(tmp_path)
    _write_json(rec, {"passed": True, "code_state": {"commit": "f" * 40}})
    assert "failed" in m.approved_code_problem(tmp_path)
    rec.unlink()
    assert "missing" in m.approved_code_problem(tmp_path)


def test_main_refuses_to_build_when_approved_code_changed(tmp_path, monkeypatch):
    m = _mod()
    monkeypatch.setattr(m, "OUT", tmp_path / "manifest.json")
    monkeypatch.setattr(m, "approved_code_problem", lambda root: "approved code changed")
    monkeypatch.setattr(m, "build_manifest", lambda root: pytest.fail("manifest built despite a code change"))
    monkeypatch.setattr(m.sys, "argv", ["e5_manifest.py"])
    with pytest.raises(SystemExit, match="approved code changed"):
        m.main()
    assert not (tmp_path / "manifest.json").exists()
