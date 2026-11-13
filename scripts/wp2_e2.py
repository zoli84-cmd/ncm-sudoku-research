"""WP2 E2 confirmatory runner (plan v3.7 §7, §10, §12.2; D76, D78; WP2 plan spec ambiguities 11, 21-24).

Usage: uv run python scripts/wp2_e2.py --role test|dry [--force | --resume]

Runs the locked E2 design once (`e2p2.run_pilot2` with the frozen CAL frequencies, generation
chunk 50, outcome decoding in 50-row batches, D78 diagnostics) on the role's puzzles
(`wp2.load_role`: TEST, or the first 50 CAL puzzles in the dry role).

Order: role data (TEST verified first), frozen-frequency file hash, checkpoint hashes,
`wp2.guard_start`, output clearing (fresh start or dry `--force`), `load_model`, clean codes A
(published as `A.npy` and recorded as `A_sha256` in the run record before any stage), stages.

Outputs (raw, git-ignored) under `runs/wp2/<role>/`: `e2.json` (run_pilot2 output plus run
metadata, `diag_files`, `code_mismatch`, `stage_seconds`, `timing`), `e2/A.npy` (int64 clean
codes), `e2/parts/<stage key with "/" -> "__">.json` (one per stage: key, A_sha256, value and the
stage's technical dict), `e2/diag/<same>.npz` (the stage's D78 arrays), `e2/parts.json` (part and
diag file name -> SHA-256, rewritten after every stage). Run record:
`experiments/wp2/<role>/runs/e2.json` (technical fields only).

`--resume` continues an incomplete run from the stages listed in `parts.json` (each part and diag
file checked against it, each part's A_sha256 against the record); unlisted part files are
recomputed. A resume without a recorded A_sha256 starts the stages afresh (no stage can have run).
The TEST role never deletes outputs: stale unlisted files are replaced by the atomic rewrites.

Identity gate (spec ambiguity 23): any nonzero `level1_noop_mismatch`, `sham_mismatch` or
`code_mismatch` count finishes the record as complete, `valid: false`, status
`identity-failure`; raw artifacts stay in place and the runner exits with code 3.

`timing` (run level): `pilot_seconds` is the wall time of this session's `run_pilot2` call,
`stage_seconds_new` the summed seconds of the stages it computed, `write_seconds` the time spent
writing their parts, and `context_seconds` the rest: `branch_context` (A's decoding, states and
the one-time D78 `code_probs`), which no stage's seconds contain. `A_seconds` (run record, set
with A_sha256) is the clean-generation time.
"""

import json
import sys
import time

import numpy as np
import torch

from ncm_sudoku import e2p2, wp2
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.subsets import sha256_array, sha256_ids

RUNNER = "e2"
FREQS = ROOT / "experiments" / "lock" / "cal_freqs.json"
FREQS_SHA256 = "0cc7292718750754baf27b813a4095e2a7479cf4e480fbed50e43c665c7983fb"
CHUNK = 50
DECODE_CHUNK = 50
CKPT_DIR = ROOT / "checkpoints" / "sudoku" / "hard"


def _read(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _name(key: str) -> str:
    return key.replace("/", "__")


def _layout(role: str) -> dict:
    raw = wp2.paths(role)[1]
    d = raw / "e2"
    return {"raw": raw, "e2_json": raw / "e2.json", "dir": d, "A": d / "A.npy", "parts": d / "parts",
            "diag": d / "diag", "manifest": d / "parts.json"}


def _discard(role: str, targets: list) -> None:
    """Dry role: deletes the targets. TEST role: never deletes (Task 1 rule); stale files are only
    ever replaced by this run's atomic rewrites and are not read unless listed in parts.json."""
    if role == "dry":
        wp2.clear_outputs(RUNNER, role, targets)


def _load_done(role: str, L: dict, A_sha: str) -> tuple[dict, dict, dict]:
    """Validated stages of an interrupted run: (done values, parts by key, manifest)."""
    manifest = _read(L["manifest"]) if L["manifest"].is_file() else {}
    wp2.check_manifest({name: L["dir"] / name for name in manifest}, manifest)
    done, parts = {}, {}
    for name in manifest:
        if not name.startswith("parts/"):
            continue
        part = _read(L["dir"] / name)
        if f"parts/{_name(part.get('key', ''))}.json" != name:
            raise wp2.DataIntegrityError(f"{RUNNER}: {name} holds stage key {part.get('key')!r}")
        if part.get("A_sha256") != A_sha:
            raise wp2.DataIntegrityError(f"{RUNNER}: {name} has another A_sha256 than the run record")
        done[part["key"]], parts[part["key"]] = part["value"], part
    unlisted = [p for sub in ("parts", "diag") if L[sub].is_dir() for p in sorted(L[sub].iterdir())
                if f"{sub}/{p.name}" not in manifest]
    _discard(role, unlisted)
    return done, parts, manifest


def _code_mismatch(parts: dict) -> dict:
    """Spec ambiguity 23: exact code mismatches summed from the stages' technical counts."""
    out = {"level1_B1": 0, "levels_B": {}, "level1_noop_D": 0}
    for key, part in parts.items():
        is_b = key.endswith("/B")
        if key != "base" and not is_b and not key.startswith("level1/"):
            continue
        n = part["technical"].get("code_mismatch")
        if n is None:
            raise wp2.DataIntegrityError(f"{RUNNER}: stage {key} has no code_mismatch count")
        if key == "base":
            out["level1_B1"] += n
        elif is_b:
            level = str(int(key.split("/")[0][1:]))
            out["levels_B"][level] = out["levels_B"].get(level, 0) + n
        else:
            out["level1_noop_D"] += n
    out["levels_B"] = dict(sorted(out["levels_B"].items(), key=lambda kv: int(kv[0])))
    return out


def run(argv: list[str] | None = None) -> int:
    args = wp2.parse_args(sys.argv[1:] if argv is None else argv)
    role = args.role
    t_start = time.perf_counter()
    data = wp2.load_role(role)
    if wp2.file_sha256(FREQS) != FREQS_SHA256:
        sys.exit(f"{RUNNER}: {FREQS} differs from the locked cal_freqs SHA-256 {FREQS_SHA256}")
    wp2.verify_checkpoints(CKPT_DIR)
    inputs = {"n": len(data.ids), "ids_sha256": sha256_ids(data.ids), "puzzles_sha256": sha256_array(data.puzzles),
              "solutions_sha256": sha256_array(data.solutions), "freqs_sha256": FREQS_SHA256, "chunk": CHUNK,
              "decode_chunk": DECODE_CHUNK}
    rec = wp2.guard_start(RUNNER, role, args.force, args.resume, inputs)
    L = _layout(role)
    stage_outputs = [L["parts"], L["diag"], L["manifest"]]
    if not args.resume:
        wp2.clear_outputs(RUNNER, role, [L["e2_json"], L["A"], *stage_outputs])
    m = load_model(CKPT_DIR)

    A_sha = rec.get("A_sha256")
    if args.resume and A_sha is not None:
        if not L["A"].is_file() or wp2.file_sha256(L["A"]) != A_sha:
            sys.exit(f"{RUNNER}: --resume refused: {L['A']} is missing or differs from the recorded A_sha256")
        A = torch.as_tensor(np.load(L["A"], allow_pickle=False))
        if A.dtype != torch.int64 or len(A) != len(data.ids):
            sys.exit(f"{RUNNER}: --resume refused: {L['A']} has dtype {A.dtype} and {len(A)} rows")
        done, parts, manifest = _load_done(role, L, A_sha)
    else:
        if args.resume:  # crash before A was recorded: no stage can have run
            _discard(role, [L["A"], *stage_outputs])
        t0 = time.perf_counter()
        A = e2p2.clean_codes(m, data.puzzles, CHUNK).to(torch.int64)
        A_seconds = time.perf_counter() - t0
        wp2.atomic_npy(L["A"], A.numpy())
        A_sha = wp2.file_sha256(L["A"])
        wp2.update_run(RUNNER, role, {"A_sha256": A_sha, "A_seconds": A_seconds})
        done, parts, manifest = {}, {}, {}

    write = {"seconds": 0.0}

    def write_part(key, value, diag, technical):
        t0 = time.perf_counter()
        name = _name(key)
        part = {"key": key, "A_sha256": A_sha, "value": value, "technical": technical}
        part_path = L["parts"] / f"{name}.json"
        wp2.atomic_json(part_path, part, indent=None)
        manifest[f"parts/{name}.json"] = wp2.file_sha256(part_path)
        if diag is not None:
            diag_path = L["diag"] / f"{name}.npz"
            wp2.atomic_npz(diag_path, **diag)
            manifest[f"diag/{name}.npz"] = wp2.file_sha256(diag_path)
        wp2.atomic_json(L["manifest"], manifest)
        parts[key] = json.loads(json.dumps(part))
        write["seconds"] += time.perf_counter() - t0

    n_done = len(done)
    t0 = time.perf_counter()
    out = e2p2.run_pilot2(m, data.puzzles, data.solutions, data.ids, chunk=CHUNK,
                          frozen_freqs=e2p2.load_frozen_freqs(FREQS), A=A, done=done, on_stage=write_part,
                          decode_chunk=DECODE_CHUNK, diagnostics=True)
    pilot_seconds = time.perf_counter() - t0
    missing = [k for k in e2p2.stage_keys(m.levels) if k not in parts]
    if missing:
        raise wp2.DataIntegrityError(f"{RUNNER}: stages without a part file: {missing}")
    new_seconds = sum(p["technical"]["seconds"] for k, p in parts.items() if k not in done)
    timing = {"pilot_seconds": pilot_seconds, "stage_seconds_new": new_seconds, "write_seconds": write["seconds"],
              "context_seconds": pilot_seconds - new_seconds - write["seconds"],
              "n_stages_reused": n_done, "n_stages_new": len(parts) - n_done}

    code_mismatch = _code_mismatch(parts)
    sham = e2p2.sham_mismatch_counts(out)
    seconds = time.perf_counter() - t_start
    diag_files = {p["key"]: {"file": f"{_name(p['key'])}.npz", "sha256": manifest[f"diag/{_name(p['key'])}.npz"]}
                  for p in parts.values() if f"diag/{_name(p['key'])}.npz" in manifest}
    wp2.atomic_json(L["e2_json"], {
        **out, "role": role, "ids": data.ids, "note": wp2.DRY_NOTE if role == "dry" else None,
        "date": time.strftime("%Y-%m-%d"), "seconds": seconds, "environment": rec["environment"],
        "code": rec["code"], "freeze": rec["freeze"], "chunk": CHUNK, "decode_chunk": DECODE_CHUNK,
        "freqs_sha256": FREQS_SHA256, "diag_files": diag_files, "code_mismatch": code_mismatch,
        "stage_seconds": {k: {"seconds": p["technical"]["seconds"], "diag_seconds": p["technical"]["diag_seconds"]}
                          for k, p in parts.items()},
        "timing": timing}, indent=None)

    identity_ok = (out["level1_noop_mismatch"] == 0 and sham["level1_B1"] == 0
                   and not any(sham["levels_B"].values()) and code_mismatch["level1_B1"] == 0
                   and not any(code_mismatch["levels_B"].values()) and code_mismatch["level1_noop_D"] == 0)
    extra = {"n_records": len(out["records"]), "n_level1_records": len(out["level1"]),
             "level1_noop_mismatch": out["level1_noop_mismatch"], "sham_mismatch": sham,
             "code_mismatch": code_mismatch, "timing": timing,
             "outputs": wp2.manifest({"e2.json": L["e2_json"], "A.npy": L["A"], "parts.json": L["manifest"]})}
    final = wp2.finish_run(RUNNER, role, rec, seconds, extra, invalid=() if identity_ok else ("identity-failure",))
    wp2.status_line(runner=RUNNER, role=role, complete=final["complete"], valid=final["valid"],
                    status=final["status"], seconds=round(seconds, 1), n_records=extra["n_records"],
                    level1_noop_mismatch=extra["level1_noop_mismatch"], sham_mismatch=sham,
                    code_mismatch=code_mismatch)
    return 0 if identity_ok else 3


def main(argv: list[str] | None = None) -> None:
    try:
        code = run(argv)
    except wp2.DataIntegrityError as e:
        sys.exit(f"{RUNNER}: {e}")
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
