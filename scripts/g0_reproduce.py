"""G0 reproduction on the 2,000 released hard boards (plan §2.2 items 1, 2, 5; D20).

Usage: uv run python scripts/g0_reproduce.py
Writes experiments/g0/reproduction.json (committed) and runs/g0/per_puzzle.json (ignored).
"""

import json
import time

from ncm_sudoku.g0 import environment_record, g0_rule, identity_checks, reproduce
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.released import load_released


def main() -> None:
    m = load_model(ROOT / "checkpoints" / "sudoku" / "hard")
    puzzles, solutions = load_released(ROOT / "data" / "released" / "sudoku" / "hard")
    t0 = time.perf_counter()
    identity = identity_checks(m, puzzles[:8])
    t1 = time.perf_counter()
    result = reproduce(m, puzzles, solutions, batch_size=128)
    t2 = time.perf_counter()
    per_puzzle = result.pop("per_puzzle")
    summary = {
        "date": time.strftime("%Y-%m-%d"),
        "environment": environment_record(),
        "identity_checks": identity,
        "identity_seconds": round(t1 - t0, 1),
        "reproduction": result,
        "reproduction_seconds": round(t2 - t1, 1),
        "rule": g0_rule(result["official"]["solved_pct"], identity),
    }
    out = ROOT / "experiments" / "g0" / "reproduction.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n", newline="\n")
    raw = ROOT / "runs" / "g0" / "per_puzzle.json"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(json.dumps(per_puzzle) + "\n")
    print(json.dumps({"rule": summary["rule"], "official": result["official"]}, indent=2))


if __name__ == "__main__":
    main()
