"""CAL validation of the full-batch level-1 enumeration (v3.7 Final ASTRA-1; plan §2.2 item 5, §7).
Non-confirmatory.

Usage: uv run python scripts/lock_level1_check.py [--force]
Regenerates the 300 CAL puzzles and their clean codes A exactly as scripts/lock_cal_freqs.py and
`run_pilot2` do (frozen-generator guard, `generate_subset("cal", 300)`, `load_model`, environment
recorded after `load_model`, `e2p2.clean_codes` with chunks of 50), runs the sham B1
(`e2p2.baseline_b1`) and the full-batch `e2p2.level1_enumeration` with the frozen CAL level-1
frequencies from experiments/lock/cal_freqs.json, and compares with the pilot-2 level-1 records
in runs/e2p2/pilot2.json (subset batches): matched on (puzzle_id, value) for the non-no-op rows,
per field (outcomes, damage measures and the two policy weights) the number of differing records
and, for floats, the maximum absolute difference; whether the frozen level-1 frequencies equal the
pilot's `freqs_level1` and the ones re-estimated from A;
the base (solve_A, solve_B1) differences; the recomputed level-1 quantities next to the pilot
values per policy (level-1 term of theta2, theta_comp, and theta2 with the pilot's level-11
term, set to None when solve_A differs from the pilot), all through the `e2p2` estimator path;
and `level1_noop_mismatch` with the largest no-op tv and tv_empty.
Writes experiments/lock/level1_check.json (atomic) and the new raw level-1 records to
runs/lock/level1_full_batch.json. Refuses to overwrite level1_check.json unless --force.
"""

import json
import os
import sys
import time

import numpy as np
import torch

from ncm_sudoku import e2p2
from ncm_sudoku.e2 import POLICIES
from ncm_sudoku.e2p2 import (
    baseline_b1, branch_context, clean_codes, level1_enumeration, level1_noop_max_tv, level1_noop_mismatch,
    load_frozen_freqs,
    puzzle_values,
)
from ncm_sudoku.g0 import code_state, environment_record
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.perturb import code_frequencies
from ncm_sudoku.subsets import assert_generator_frozen, generate_subset

N_CAL = 300
CHUNK = 50  # run_pilot2 default
FREQS = ROOT / "experiments" / "lock" / "cal_freqs.json"
PILOT = ROOT / "runs" / "e2p2" / "pilot2.json"
OUT = ROOT / "experiments" / "lock" / "level1_check.json"
RAW = ROOT / "runs" / "lock" / "level1_full_batch.json"
FIELDS = ("solve_C", "solve_D", "well_formed_C", "well_formed_D", "tv", "tv_empty", "latent", "requant_ratio",
          "downstream_changes_D", "w_frequency", "w_uniform")
FLOAT_FIELDS = ("tv", "tv_empty", "latent", "requant_ratio", "w_frequency", "w_uniform")
MAX_LISTED = 50
NOTE = ("non-confirmatory validation (v3.7 Final ASTRA-1): full-batch level-1 enumeration on CAL compared "
        "with the pilot-2 subset-batch level-1 records")


def guard(force: bool) -> None:
    if OUT.exists() and not force:
        sys.exit(f"{OUT} exists: lock_level1_check is a rerun-guarded script; use --force to overwrite")


def _atomic(path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def compare_records(new: list[dict], old: list[dict]) -> dict:
    """Non-no-op new records against the pilot records, matched on (puzzle_id, value)."""
    new_by = {(r["puzzle_id"], r["value"]): r for r in new if not r.get("noop", False)}
    old_by = {(r["puzzle_id"], r["value"]): r for r in old if not r.get("noop", False)}
    keys = [k for k in new_by if k in old_by]
    fields, differing = {}, []
    for f in FIELDS:
        diff = [k for k in keys if new_by[k][f] != old_by[k][f]]
        entry = {"n_diff": len(diff)}
        if f in FLOAT_FIELDS:
            entry["max_abs_diff"] = max((abs(new_by[k][f] - old_by[k][f]) for k in keys), default=0.0)
        fields[f] = entry
    for k in keys:
        changed = [f for f in FIELDS if new_by[k][f] != old_by[k][f]]
        if changed and len(differing) < MAX_LISTED:
            differing.append({"puzzle_id": k[0], "value": k[1], "fields": changed})
    return {"n_matched": len(keys), "n_missing_in_pilot": sum(k not in old_by for k in new_by),
            "n_missing_in_new": sum(k not in new_by for k in old_by), "fields": fields,
            "differing": differing, "differing_listed_max": MAX_LISTED}


def _summary(new: dict[str, float], old: dict[str, float]) -> dict:
    common = [p for p in new if p in old]
    mean = lambda d: float(np.mean(list(d.values()))) if d else None  # noqa: E731
    return {"new": mean(new), "pilot": mean(old), "n_new": len(new), "n_pilot": len(old),
            "max_abs_diff": max((abs(new[p] - old[p]) for p in common), default=0.0)}


def theta_comparison(new: dict, pilot: dict, theta2_valid: bool = True) -> dict:
    """Per policy: mean level-1 term of theta2 (sum_v w (D - A)), theta_comp, and theta2 with the
    pilot's level-11 term, from the new and the pilot level-1 records (`e2p2` estimator path).
    theta2 is None (with `theta2_note`) when `theta2_valid` is False: the pilot's level-11 term
    uses the pilot's solve_A, so a different A makes the mixed theta2 meaningless."""
    out = {}
    for policy in POLICIES:
        lt = {k: {pid: da for pid, (da, _) in e2p2._level1_terms(d, policy).items()} for k, d in
              (("new", new), ("pilot", pilot))}
        out[policy] = {
            "level1_term_theta2": _summary(lt["new"], lt["pilot"]),
            "theta_comp": _summary(puzzle_values(new, "theta_comp", policy), puzzle_values(pilot, "theta_comp", policy)),
            "theta2": (_summary(puzzle_values(new, "theta2", policy), puzzle_values(pilot, "theta2", policy))
                       if theta2_valid else None),
        }
        if not theta2_valid:
            out[policy]["theta2_note"] = ("invalid: base_diff solve_A != 0, so the pilot's level-11 term "
                                          "does not match the regenerated A")
    return out


def main() -> None:
    guard(force="--force" in sys.argv)
    assert_generator_frozen()
    batch = generate_subset("cal", N_CAL)
    puzzles = np.stack([g.puzzle for g in batch])
    solutions = np.stack([g.solution for g in batch])
    ids = [g.puzzle_id for g in batch]
    m = load_model(ROOT / "checkpoints" / "sudoku" / "hard")
    environment = environment_record()  # after load_model, which enables deterministic algorithms
    freqs1 = torch.as_tensor(load_frozen_freqs(FREQS)[1])
    pilot = json.loads(PILOT.read_text(encoding="utf-8"))
    t0 = time.perf_counter()
    A = clean_codes(m, puzzles, CHUNK)
    ctx = branch_context(m, puzzles, solutions, A, CHUNK)
    base = baseline_b1(m, puzzles, solutions, ids, ctx)
    level1 = level1_enumeration(m, puzzles, solutions, ids, A, freqs1, CHUNK, ctx)
    mismatch, max_tv = level1_noop_mismatch(level1, base), level1_noop_max_tv(level1)
    seconds = round(time.perf_counter() - t0, 1)
    _atomic(RAW, json.dumps({"freqs_level1": freqs1.tolist(), "freq_source": "frozen", "ids": ids, "base": base,
                             "level1": level1, "level1_noop_mismatch": mismatch}) + "\n")

    new = {"base": base, "level1": level1, "records": pilot["records"]}  # level-11 term from the pilot
    pilot_base = {b["puzzle_id"]: b for b in pilot["base"]}
    base_diff = {k: sum(b[k] != pilot_base[b["puzzle_id"]][k] for b in base if b["puzzle_id"] in pilot_base)
                 for k in ("solve_A", "solve_B1")}
    out = {
        "note": NOTE, "non_confirmatory": True, "date": time.strftime("%Y-%m-%d"), "code": code_state(),
        "environment": environment, "n_cal": len(ids), "chunk": CHUNK,
        "freqs_level1_match_input": freqs1.tolist() == code_frequencies(A, m.levels)[0].tolist(),
        "freqs_level1_match_pilot": freqs1.tolist() == pilot["freqs_level1"],
        "level1_noop_mismatch": mismatch, "level1_noop_max_tv": max_tv, "n_noop": sum(r["noop"] for r in level1),
        "n_level1_records": len(level1),
        "base_diff": base_diff,
        "comparison": compare_records(level1, pilot["level1"]),
        "theta": theta_comparison(new, pilot, theta2_valid=base_diff["solve_A"] == 0),
        "raw": str(RAW.relative_to(ROOT)) if RAW.is_relative_to(ROOT) else str(RAW),
        "seconds": seconds,
    }
    _atomic(OUT, json.dumps(out, indent=2) + "\n")
    print(json.dumps({"level1_noop_mismatch": mismatch, "n_matched": out["comparison"]["n_matched"],
                      "n_diff": {f: v["n_diff"] for f, v in out["comparison"]["fields"].items()},
                      "seconds": seconds}))


if __name__ == "__main__":
    main()
