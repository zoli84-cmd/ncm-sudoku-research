"""Lock power simulations (D70(1), D70(2); plan v3.6 §11.4, §12.2). Non-confirmatory planning output.

Usage: uv run python scripts/lock_power.py
- E2 levels 2 vs. 11 equivalence: reads runs/e2p2/pilot2.json, builds the frequency-policy
  puzzle-level theta2' values with ncm_sudoku.e2p2.puzzle_values (as scripts/e2_sample_size.py
  does) and simulates the false-equivalence rate of the TOST rule at n = 600 under the
  injection scenario at +0.03 and -0.03 (`power.equivalence_boundary_error`).
- H1 family-level TOST: reads experiments/e3prep/wholelayer_h1_diffs_L06.json (D67 diffs)
  and simulates power at 0 and at the observed mean, false equivalence at +-0.01, and the
  share of runs whose 98.33% interval excludes 0 (`power.h1_tost`).
Writes experiments/lock/power.json (atomic, with code_state and the planning parameters) and
experiments/lock/power.md. Deterministic (fixed seed); safe to rerun.
"""

import json
import os
import time

import numpy as np

from ncm_sudoku.e2p2 import puzzle_values
from ncm_sudoku.g0 import code_state
from ncm_sudoku.model import ROOT
from ncm_sudoku.power import equivalence_boundary_error, h1_tost

RAW = ROOT / "runs" / "e2p2" / "pilot2.json"
DIFFS = ROOT / "experiments" / "e3prep" / "wholelayer_h1_diffs_L06.json"
OUT = ROOT / "experiments" / "lock"
PARAMS = {"n": 600, "reps": 500, "n_boot_sim": 1000, "seed": 0}
NOTE = "non-confirmatory planning output (plan v3.6 §12.1); not evidence for H1, H2 or H3"


def _atomic(path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def _fmt(v) -> str:
    return "n/a" if v is None else f"{v:.3f}"


def report(out: dict) -> str:
    e, h = out["e2_equivalence_boundary"], out["h1_tost"]
    p = out["planning_parameters"]
    lines = [
        "# Lock power simulations (D70)", "",
        f"{NOTE}.", "",
        f"n = {p['n']}, {p['reps']} simulated samples per scenario, {p['n_boot_sim']} bootstrap resamples, seed {p['seed']}.",
        "",
        "## E2 levels 2 vs. 11 equivalence (TOST ±0.03, injection scenario)", "",
        f"Pilot θ₂′: n = {e['n_pilot']}, mean {e['pilot_mean']:.4f}, zero share {e['pilot_zero_share']:.3f}.", "",
        "| True effect | False-equivalence rate |", "|---|---|",
        *[f"| {k} | {_fmt(v)} |" for k, v in e["error"].items()],
        *([""] + [f"- {k}: {v}" for k, v in e["notes"].items()] if e["notes"] else []),
        "",
        "## H1 family-level TOST (±0.01, 96.67% interval)", "",
        f"D67 whole-layer level-6 diffs: n = {h['n_pilot']}, observed mean {h['observed_mean']:.4f}.", "",
        "| Quantity | Share |", "|---|---|",
        f"| Power, true mean 0 | {_fmt(h['power_at_zero'])} |",
        f"| Power, observed mean | {_fmt(h['power_at_observed'])} |",
        *[f"| False equivalence, true mean {k} | {_fmt(v)} |" for k, v in h["false_equivalence"].items()],
        f"| 98.33% interval excludes 0, observed mean | {_fmt(h['excludes_zero_at_observed'])} |",
        f"| Both (inside ±0.01 and above 0), observed mean | {_fmt(h['inside_and_above_zero_at_observed'])} |",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    t0 = time.perf_counter()
    pilot = json.loads(RAW.read_text(encoding="utf-8"))
    xp = np.asarray(list(puzzle_values(pilot, "theta2_prime", "frequency").values()), dtype=float)
    diffs = np.asarray(json.loads(DIFFS.read_text(encoding="utf-8"))["diffs"], dtype=float)
    out = {
        "note": NOTE, "date": time.strftime("%Y-%m-%d"), "code": code_state(),
        "inputs": {"theta2_prime": str(RAW.relative_to(ROOT)) if RAW.is_relative_to(ROOT) else str(RAW),
                   "n_theta2_prime": int(len(xp)),
                   "h1_diffs": str(DIFFS.relative_to(ROOT)) if DIFFS.is_relative_to(ROOT) else str(DIFFS),
                   "n_h1_diffs": int(len(diffs))},
        "planning_parameters": dict(PARAMS),
        "e2_equivalence_boundary": equivalence_boundary_error(xp, **PARAMS),
        "h1_tost": h1_tost(diffs, **PARAMS),
    }
    out["seconds"] = round(time.perf_counter() - t0, 1)
    _atomic(OUT / "power.json", json.dumps(out, indent=2) + "\n")
    _atomic(OUT / "power.md", report(out))


if __name__ == "__main__":
    main()
