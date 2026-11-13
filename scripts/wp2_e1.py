"""WP2 E1 confirmatory runner (plan v3.7 §6, §10; D76; WP2 plan spec ambiguities 12, 13, 21).

Usage: uv run python scripts/wp2_e1.py --role test|dry [--force | --resume]

Runs the tokenizer/generator breakdown once (`e1.e1_records`, batch size 50, spec ambiguity
13) on the role's puzzles (`wp2.load_role`: TEST, or the first 50 CAL puzzles in the dry role).

Order: role data (TEST verified first), checkpoints, `wp2.guard_start`, output clearing, model,
`e1_records`, atomic write, finish, `status_line`.

E1 keeps no partial stage state (spec ambiguity 21): `--resume` restarts it from scratch after
the guard's input, code and environment checks pass. Output clearing only runs on a fresh start
(`wp2_e2.py`'s rule): on `--resume`, `e1.json` is simply recomputed and the atomic write replaces
it in place, so a TEST-role resume works even though `clear_outputs` never deletes TEST outputs
(a resume that first tried to clear an existing `e1.json` would fail permanently in the TEST
role). The TEST role never deletes outputs, so a complete TEST record refuses a rerun outright
(single-look); an interrupted TEST run can only continue with `--resume`, and a fresh TEST start
over existing outputs is refused.

A fresh start marks the record with `wp2.mark_outputs_started` right after `clear_outputs`
succeeds, before `e1.json` is computed. `--resume` checks that marker with
`wp2.prepare_resume_outputs` before touching `e1_json`: `guard_start` writes the (incomplete) run
record before a fresh start's `clear_outputs` call, so a refused fresh TEST start over an
unrecorded leftover `e1.json` (e.g. a complete prior run whose record was separately lost, say to
`git clean`) still leaves an incomplete, markerless record behind; a later `--resume` must not
read that leftover as this run's own partial state and overwrite it.

Outputs (raw, git-ignored) under `runs/wp2/<role>/`: `e1.json` (`role`, `ids`, `note`, `records`,
`batch_size`). Run record: `experiments/wp2/<role>/runs/e1.json` (technical fields only: `n`,
`batch_size`, `outputs` SHA-256 of `e1.json`). No outcome metric (solve share, format-error
share, Hamming, `e1_table`) is printed or written to the run record (D76(5)); that aggregation
is left to the evaluation script, which reads `e1.json` after TEST runs are complete.
"""

import sys
import time

from ncm_sudoku import wp2
from ncm_sudoku.e1 import e1_records
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.subsets import sha256_array, sha256_ids

RUNNER = "e1"
BATCH_SIZE = 50
CKPT_DIR = ROOT / "checkpoints" / "sudoku" / "hard"


def _layout(role: str) -> dict:
    return {"e1_json": wp2.paths(role)[1] / "e1.json"}


def run(argv: list[str] | None = None) -> int:
    args = wp2.parse_args(sys.argv[1:] if argv is None else argv)
    role = args.role
    t_start = time.perf_counter()
    data = wp2.load_role(role)
    wp2.verify_checkpoints(CKPT_DIR)
    inputs = {"n": len(data.ids), "ids_sha256": sha256_ids(data.ids), "puzzles_sha256": sha256_array(data.puzzles),
              "solutions_sha256": sha256_array(data.solutions), "batch_size": BATCH_SIZE}
    rec = wp2.guard_start(RUNNER, role, args.force, args.resume, inputs)
    L = _layout(role)
    if args.resume:
        wp2.prepare_resume_outputs(RUNNER, role, rec, [L["e1_json"]])
    else:
        wp2.clear_outputs(RUNNER, role, [L["e1_json"]])
        rec = wp2.mark_outputs_started(RUNNER, role)
    m = load_model(CKPT_DIR)

    records = e1_records(m, data.puzzles, data.solutions, data.ids, batch_size=BATCH_SIZE)
    wp2.atomic_json(L["e1_json"], {"role": role, "ids": data.ids, "note": wp2.DRY_NOTE if role == "dry" else None,
                                   "records": records, "batch_size": BATCH_SIZE}, indent=None)

    seconds = time.perf_counter() - t_start
    extra = {"n": len(records), "batch_size": BATCH_SIZE, "outputs": wp2.manifest({"e1.json": L["e1_json"]})}
    final = wp2.finish_run(RUNNER, role, rec, seconds, extra)
    wp2.status_line(runner=RUNNER, role=role, complete=final["complete"], valid=final["valid"],
                    status=final["status"], seconds=round(seconds, 1), n=extra["n"])
    return 0


def main(argv: list[str] | None = None) -> None:
    try:
        code = run(argv)
    except wp2.DataIntegrityError as e:
        sys.exit(f"{RUNNER}: {e}")
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
