"""Lock power simulations (D70(1), D70(2); plan v3.6 §11.4, §12.2). Non-confirmatory planning output.

Usage: uv run python scripts/lock_power.py
- E2 levels 2 vs. 11 equivalence: reads runs/e2p2/pilot2.json, builds the frequency-policy
  puzzle-level theta2' values with ncm_sudoku.e2p2.puzzle_values (as scripts/e2_sample_size.py
  does) and simulates the false-equivalence rate of the TOST rule at n = 600 under the
  injection scenario at +0.03 and -0.03 (`power.equivalence_boundary_error`, 2,000 samples;
  bound-path share, per-path rates and Monte Carlo SE).
- H1 family-level TOST: reads experiments/e3prep/wholelayer_h1_diffs_L06.json (D67 diffs)
  and simulates power at 0 and at the observed mean, false equivalence at +-0.01, and the
  share of runs whose 98.33% interval excludes 0 (`power.h1_tost`, 2,000 bootstrap resamples).
Both use the function defaults. Records the SHA-256, quantity and ids count of the inputs
(asserts one diff per id).
Writes experiments/lock/power.json (atomic, with code_state and the planning parameters) and
experiments/lock/power.md. Deterministic (fixed seed); safe to rerun.
"""

import hashlib
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
EQ_KW: dict = {}  # equivalence_boundary_error overrides; empty = function defaults (tests shrink it)
H1_KW: dict = {}  # h1_tost overrides; empty = function defaults
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
    pe, ph = e["planning_parameters"], h["planning_parameters"]

    def path_row(k, v):
        dt = e["detail"].get(k)
        if dt is None:
            return f"| {k} | {_fmt(v)} | n/a | n/a | n/a | n/a |"
        by = dt["error_by_path"]
        return (f"| {k} | {_fmt(v)} | {_fmt(dt['mc_se'])} | {_fmt(dt['bound_share'])} | "
                f"{_fmt(by['bound'])} | {_fmt(by['bootstrap'])} |")

    lines = [
        "# Lock power simulations (D70)", "",
        f"{NOTE}.", "",
        "## E2 levels 2 vs. 11 equivalence (TOST ±0.03, injection scenario)", "",
        f"n = {pe['n']}, {pe['reps']} simulated samples per scenario, {pe['n_boot_sim']} bootstrap resamples, "
        f"seed {pe['seed']}. Pilot θ₂′: n = {e['n_pilot']}, mean {e['pilot_mean']:.4f}, "
        f"zero share {e['pilot_zero_share']:.3f}.", "",
        "| True effect | False-equivalence rate | MC SE | Share on bound path | Rate, bound path | Rate, bootstrap path |",
        "|---|---|---|---|---|---|",
        *[path_row(k, v) for k, v in e["error"].items()],
        *([""] + [f"- {k}: {v}" for k, v in e["notes"].items()] if e["notes"] else []),
        "",
        "## H1 family-level TOST (±0.01, 96.67% interval)", "",
        f"n = {ph['n']}, {ph['reps']} simulated samples per scenario, {ph['n_boot_sim']} bootstrap resamples, "
        f"seed {ph['seed']}. D67 whole-layer level-6 diffs: n = {h['n_pilot']}, observed mean "
        f"{h['observed_mean']:.4f}.", "",
        "| Quantity | Share |", "|---|---|",
        f"| Power, true mean 0 | {_fmt(h['power_at_zero'])} |",
        f"| Power, observed mean | {_fmt(h['power_at_observed'])} |",
        *[f"| False equivalence, true mean {k} | {_fmt(v)} |" for k, v in h["false_equivalence"].items()],
        f"| 98.33% interval excludes 0, observed mean | {_fmt(h['excludes_zero_at_observed'])} |",
        f"| Both (inside ±0.01 and 98.33% lower limit > 0), observed mean | "
        f"{_fmt(h['inside_and_above_zero_at_observed'])} |",
        "",
    ]
    return "\n".join(lines)


def _rel(path) -> str:
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def main() -> None:
    t0 = time.perf_counter()
    raw_bytes, diffs_bytes = RAW.read_bytes(), DIFFS.read_bytes()
    pilot = json.loads(raw_bytes.decode("utf-8"))
    xp = np.asarray(list(puzzle_values(pilot, "theta2_prime", "frequency").values()), dtype=float)
    d = json.loads(diffs_bytes.decode("utf-8"))
    diffs = np.asarray(d["diffs"], dtype=float)
    assert len(diffs) == len(d["ids"]), f"{DIFFS}: {len(diffs)} diffs but {len(d['ids'])} ids"
    e = equivalence_boundary_error(xp, **EQ_KW)
    h = h1_tost(diffs, **H1_KW)
    out = {
        "note": NOTE, "date": time.strftime("%Y-%m-%d"), "code": code_state(),
        "inputs": {"theta2_prime": _rel(RAW), "theta2_prime_sha256": hashlib.sha256(raw_bytes).hexdigest(),
                   "n_theta2_prime": int(len(xp)),
                   "h1_diffs": _rel(DIFFS), "h1_diffs_sha256": hashlib.sha256(diffs_bytes).hexdigest(),
                   "h1_diffs_quantity": d.get("quantity"), "n_h1_diffs": int(len(diffs)),
                   "n_h1_diffs_ids": int(len(d["ids"]))},
        "planning_parameters": {"e2_equivalence_boundary": e["planning_parameters"],
                                "h1_tost": h["planning_parameters"]},
        "e2_equivalence_boundary": e,
        "h1_tost": h,
    }
    out["seconds"] = round(time.perf_counter() - t0, 1)
    _atomic(OUT / "power.json", json.dumps(out, indent=2) + "\n")
    _atomic(OUT / "power.md", report(out))


if __name__ == "__main__":
    main()
