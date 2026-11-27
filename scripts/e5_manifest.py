"""E5 preregistration hash manifest (`e5_protocol_v1.md` §10; D108-D109).

Usage: uv run --locked python scripts/e5_manifest.py [--force]
       uv run --locked python scripts/e5_manifest.py --verify

Lists the SHA-256 of every artifact `ncm_sudoku.e5run.require_lock` and the TEST runner check
before any TEST data exist: the protocol file; the checkpoint files; the generator guard files
(`subsets.FROZEN_SHA256`, covered by the `src/ncm_sudoku/*.py` sweep below); the screening corpus
(gate, CAL, PROBE-TRAIN, PROBE-VAL, the WP2 TEST set and the released hard set: ids by
`subsets.sha256_ids`, solution arrays by `subsets.sha256_array`); the E5 counterfactual PROBE-TRAIN
and PROBE-VAL pair arrays; the primary heads (Z<=6, P2), the P4/P8 heads, Q, H, R, Pi, W; the
secondary components as the file SHA-256 of `scripts/e5_pilot.py` and `scripts/e5_pilot_ref.py`
(protocol §4.3: they refit the secondary components deterministically on PROBE data); the TEST
runner and every `src/ncm_sudoku/*.py`; `uv.lock`; the approved dry-run record and its sidecar
hash, plus one entry for every path the record's own `hashes` dict (§9.4) names that no earlier
bucket already covers (e.g. `pairs.json`, `causal/heads.json`, `lock/components.json`, both dry
modes' `results.json`/`run.json`, `e5_dry_check.py`, the pilot predictions, `causal/primary.npz`
and the PROBE-VAL activation arrays), so a change to anything the dry-run approval relies on is
caught by `--verify` too.

Every entry is `{name, path (ROOT-relative POSIX), format, sha256, retrieval}` (ruling R4), format
one of `file`, `sha256_ids`, `sha256_array`. Because `runs/`, `checkpoints/` and `data/` are not in
the repository, every such entry's `retrieval` gives a reconstruction recipe (script, function and
seed namespace) or a download location; restoration from a clean environment is checked separately,
by hand, before the lock (§10).

Before building, materializes the gate (1,000) and CAL (300) screening ids and solutions under the
git-ignored `runs/e5/lock/screening/<name>/` with `ncm_sudoku.subsets.generate_subset` (a no-op if
already present); PROBE-TRAIN, PROBE-VAL, the WP2 TEST set and the released hard set are already on
disk from earlier steps and are hashed as-is.

Without --verify: writes `experiments/e5/lock/manifest.json`; refuses to overwrite unless --force,
and refuses to build at all unless the approved code is unchanged since the dry check
(`approved_code_problem`): `git diff --quiet <check.json code_state.commit> HEAD -- src
":(exclude,glob)src/**/*.md" scripts/e5_test.py scripts/e5_dry_check.py pyproject.toml uv.lock
e5_protocol_v1.md` must exit 0, so the manifest never pins code the dry-run approval did not run;
the exclude pathspec lets a doc-only edit under `src/` (e.g. `src/ncm_sudoku/AGENTS.md`) through
without weakening the gate on `.py` changes.
With --verify: recomputes every entry through `ncm_sudoku.e5run.verify_manifest` and exits 0, or
prints the first mismatch (naming the entry) and exits 1.

Every builder function below takes the repository root explicitly (never the bare module `ROOT`),
so the whole assembly is testable against a synthetic root in `tmp_path`.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from ncm_sudoku import e5run, subsets
from ncm_sudoku.model import ROOT
from ncm_sudoku.wp2 import atomic_json, file_sha256

OUT = ROOT / "experiments" / "e5" / "lock" / "manifest.json"
IN_REPO = "committed in this repository"

# Screening-corpus subsets not yet saved anywhere else; materialized by this script.
MATERIALIZE = {"gate": 1000, "cal": 300}
# Paths the dry-run approval must have run unchanged (compared between its commit and HEAD).
# `src` excludes its own markdown docs (e.g. `src/ncm_sudoku/AGENTS.md`): a doc-only edit there
# carries no integrity risk and must not block the manifest.
APPROVED_CODE_PATHS = ("src", ":(exclude,glob)src/**/*.md", "scripts/e5_test.py", "scripts/e5_dry_check.py",
                       "pyproject.toml", "uv.lock", "e5_protocol_v1.md")
EXISTING_COUNTS = {"probe_train": 2000, "probe_val": 500, "test": 600}


def _screening_dir(root: Path, name: str) -> tuple[Path, str]:
    """Directory and recipe script of one screening-corpus subset's ids/solutions, under `root`."""
    if name in MATERIALIZE:
        return root / "runs" / "e5" / "lock" / "screening" / name, "scripts/e5_manifest.py (this script)"
    if name == "test":
        return root / "runs" / "lock" / "test", "scripts/lock_test_set.py"
    return root / "runs" / "e3prep" / name, "scripts/e3_extract.py"


def _rel(root: Path, path: Path) -> str:
    return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()


def file_entry(name: str, root: Path, path: Path, retrieval: str) -> dict:
    return {"name": name, "path": _rel(root, path), "format": "file", "sha256": file_sha256(path),
            "retrieval": retrieval}


def ids_entry(name: str, root: Path, path: Path, retrieval: str) -> dict:
    ids = json.loads(Path(path).read_text(encoding="utf-8"))
    return {"name": name, "path": _rel(root, path), "format": "sha256_ids", "sha256": subsets.sha256_ids(ids),
            "retrieval": retrieval}


def array_entry(name: str, root: Path, path: Path, retrieval: str) -> dict:
    arr = np.load(path, allow_pickle=False)
    return {"name": name, "path": _rel(root, path), "format": "sha256_array", "sha256": subsets.sha256_array(arr),
            "retrieval": retrieval}


def ensure_screening_corpus(root: Path) -> None:
    """Writes the gate and CAL ids/solutions under `root` if not already there; a no-op otherwise.
    The generator is frozen (`subsets.assert_generator_frozen`), so a regeneration would reproduce
    the same bytes anyway, but existing files are reused as-is to avoid the generation cost."""
    for name, n in MATERIALIZE.items():
        d, _ = _screening_dir(root, name)
        ids_p, sol_p = d / "ids.json", d / "solutions.npy"
        if ids_p.is_file() and sol_p.is_file():
            continue
        puzzles = subsets.generate_subset(name, n)
        d.mkdir(parents=True, exist_ok=True)
        ids = [p.puzzle_id for p in puzzles]
        solutions = np.stack([p.solution for p in puzzles]).astype(np.uint8)
        ids_p.write_text(json.dumps(ids) + "\n", encoding="utf-8", newline="\n")
        np.save(sol_p, solutions)


def screening_entries(root: Path) -> list[dict]:
    out = []
    for name in (*MATERIALIZE, *EXISTING_COUNTS):
        d, script = _screening_dir(root, name)
        ns = subsets.SEEDS[name]
        n = MATERIALIZE.get(name) or EXISTING_COUNTS[name]
        recipe = f"ncm_sudoku.subsets.generate_subset({name!r}, {n}) (seed namespace {ns}); {script}"
        out.append(ids_entry(f"screening_{name}_ids", root, d / "ids.json", recipe))
        out.append(array_entry(f"screening_{name}_solutions", root, d / "solutions.npy", recipe))
    return out


def released_entries(root: Path) -> list[dict]:
    rec = json.loads((root / "experiments" / "provenance" / "released_data.json").read_text(encoding="utf-8"))["hard"]
    retrieval = (f"Hugging Face {rec['repo_id']} ({rec['repo_type']}) revision {rec['revision']}; "
                 "scripts/fetch_released_data.py")
    return [file_entry(f"released:{key}", root, root / "data" / "released" / key, retrieval) for key in rec["files"]]


def checkpoint_entries(root: Path) -> list[dict]:
    rec = json.loads((root / "experiments" / "provenance" / "checkpoints.json").read_text(encoding="utf-8"))
    retrieval = f"Hugging Face {rec['repo_id']} revision {rec['revision']}; scripts/fetch_checkpoints.py"
    return [file_entry(f"checkpoint:{key}", root, root / "checkpoints" / key, retrieval) for key in rec["files"]]


def pair_entries(root: Path) -> list[dict]:
    pairs = json.loads((root / "experiments" / "e5" / "pairs.json").read_text(encoding="utf-8"))
    out = []
    for name, info in pairs["subsets"].items():
        d = root / info["storage"]
        recipe = (f"ncm_sudoku.e5pairs (seed namespace {info['seed_namespace']}); scripts/e5_pairs.py "
                  f"({info['storage']}/)")
        out.append(ids_entry(f"e5_pairs_{name}_ids", root, d / "ids.json", recipe))
        for member in ("a", "b", "solutions"):
            out.append(array_entry(f"e5_pairs_{name}_{member}", root, d / f"{member}.npy", recipe))
    return out


def component_entries(root: Path) -> list[dict]:
    components = json.loads((root / "experiments" / "e5" / "lock" / "components.json").read_text(encoding="utf-8"))
    out = []
    for key, info in components["files"].items():
        out.append(file_entry(f"component:{key}", root, root / info["file"], "scripts/e5_lock_components.py"))
    for rep, info in components["verified_heads"].items():
        out.append(file_entry(f"head:{rep}", root, root / info["file"], "scripts/e5_causal_heads.py"))
    return out


def secondary_entries(root: Path) -> list[dict]:
    retrieval = "refit deterministically on PROBE data by this script at the locked commit"
    return [file_entry("secondary:e5_pilot.py", root, root / "scripts" / "e5_pilot.py", retrieval),
            file_entry("secondary:e5_pilot_ref.py", root, root / "scripts" / "e5_pilot_ref.py", retrieval)]


def code_entries(root: Path) -> list[dict]:
    out = [file_entry("test_runner", root, root / "scripts" / "e5_test.py", IN_REPO)]
    for p in sorted((root / "src" / "ncm_sudoku").glob("*.py")):
        out.append(file_entry(f"src:{p.name}", root, p, IN_REPO))
    return out


def misc_entries(root: Path) -> list[dict]:
    return [
        file_entry("protocol", root, root / "e5_protocol_v1.md", IN_REPO),
        file_entry("uv.lock", root, root / "uv.lock", IN_REPO),
        file_entry("dry_run_record", root, root / "experiments" / "e5" / "dry" / "check.json", IN_REPO),
        file_entry("dry_run_record_sha256", root, root / "experiments" / "e5" / "dry" / "check.sha256", IN_REPO),
    ]


def _dry_record_retrieval(rel: str) -> str:
    """Reconstruction recipe for a path named in the dry-run record's own `hashes` dict (§9.4)
    that no other bucket already covers; committed paths need none."""
    if rel.startswith("runs/e5/dry_perm/"):
        return "scripts/e5_test.py --mode dry_perm"
    if rel.startswith("runs/e5/dry/"):
        return "scripts/e5_test.py --mode dry"
    if rel.startswith("runs/e5/pilot/"):
        return "scripts/e5_pilot.py"
    if rel == "runs/e5/causal/primary.npz":
        return "scripts/e5_causal.py"
    if rel.startswith("runs/e5/acts/"):
        return "scripts/e5_extract.py"
    return IN_REPO


def dry_record_hash_entries(root: Path, covered: dict[str, str]) -> list[dict]:
    """Protocol §10: "the approved dry-run record and the hashes it states". `check.json`'s own
    `hashes` dict (§9.4) hashes every path - ids and arrays included - as plain file bytes
    (`wp2.file_sha256`), not through `subsets.sha256_ids`/`sha256_array`: those give a different
    value for the same path (an id list's canonical JSON re-dump, or an array's raw buffer, differ
    from the file's own bytes). So a path already in the manifest under one of those formats is
    *not* covered here unless its value happens to equal the record's (`covered` maps path ->
    sha256 of every entry already built); every other path named in `hashes`, covered or not, gets
    its own `file` entry, so a change to anything the dry-run approval relies on - not just the
    record's own bytes - is caught by `--verify`."""
    rec = json.loads((root / "experiments" / "e5" / "dry" / "check.json").read_text(encoding="utf-8"))
    out = []
    for rel, expected in rec["hashes"].items():
        if covered.get(rel) == expected:
            continue
        out.append(file_entry(f"dry_hash:{rel}", root, root / rel, _dry_record_retrieval(rel)))
    return out


def approved_code_problem(root: Path) -> str | None:
    """None if `APPROVED_CODE_PATHS` are identical at the dry-run record's `code_state.commit` and at
    HEAD (`git diff --quiet <commit> HEAD -- ...` exits 0); otherwise the reason the build is refused
    (record or commit missing, code changed since the approval, or git failing)."""
    rec_path = Path(root) / "experiments" / "e5" / "dry" / "check.json"
    if not rec_path.is_file():
        return f"{rec_path}: missing"
    commit = (json.loads(rec_path.read_text(encoding="utf-8")).get("code_state") or {}).get("commit")
    if not isinstance(commit, str) or not commit:
        return f"{rec_path}: no code_state.commit"
    r = subprocess.run(["git", "-C", str(root), "diff", "--quiet", commit, "HEAD", "--", *APPROVED_CODE_PATHS],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if r.returncode == 1:
        return (f"approved code changed between the dry-run commit {commit} and HEAD "
                f"({', '.join(APPROVED_CODE_PATHS)}); redo the dry runs and the dry check first")
    if r.returncode != 0:
        return f"git diff {commit} HEAD failed (exit {r.returncode}): {r.stderr.strip()}"
    return None


def build_manifest(root: Path) -> dict:
    root = Path(root)
    ensure_screening_corpus(root)
    entries = (misc_entries(root) + checkpoint_entries(root) + screening_entries(root) + released_entries(root)
              + pair_entries(root) + component_entries(root) + secondary_entries(root) + code_entries(root))
    covered = {e["path"]: e["sha256"] for e in entries}
    entries += dry_record_hash_entries(root, covered)
    names = [e["name"] for e in entries]
    dupes = sorted({n for n in names if names.count(n) > 1})
    assert not dupes, f"duplicate manifest entry name(s): {dupes}"
    return {"note": "E5 preregistration hash manifest (e5_protocol_v1.md §10)",
            "date": time.strftime("%Y-%m-%d"), "entries": entries}


def main() -> None:
    if "--verify" in sys.argv:
        try:
            e5run.verify_manifest(OUT)
        except e5run.DataIntegrityError as e:
            sys.exit(f"e5_manifest --verify: {e}")
        print("e5_manifest --verify: ok", flush=True)
        return
    if OUT.exists() and "--force" not in sys.argv:
        sys.exit(f"{OUT.relative_to(ROOT)} exists; use --force")
    problem = approved_code_problem(ROOT)
    if problem:
        sys.exit(f"e5_manifest: refused, nothing written: {problem}")
    manifest = build_manifest(ROOT)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(OUT, manifest)
    print(json.dumps({"n_entries": len(manifest["entries"])}), flush=True)


if __name__ == "__main__":
    main()
