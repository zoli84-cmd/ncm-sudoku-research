"""E2 pilot on CAL (plan §7, §12.1; D38, D39). Non-confirmatory.

Usage: uv run python scripts/wp1_pilot.py
Writes runs/wp1/pilot_records.jsonl, experiments/wp1/pilot_summary.json and
experiments/wp1/pilot_report.md.
"""

import json
import time

import numpy as np

from ncm_sudoku.e2 import PILOT_LEVELS, POLICIES, N_SEEDS, run_pilot, summarize
from ncm_sudoku.g0 import environment_record
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.subsets import generate_subset

N_CAL = 300


def _report(summary: dict, seconds: float) -> str:
    t2, tc = summary["theta2"], summary["theta_comp_level2"]
    lines = [
        "# E2 pilot report",
        "",
        "**Non-confirmatory pilot (plan §12.1).** These numbers plan the confirmatory study; they are not evidence for H2 or H3.",
        "",
        f"- CAL puzzles: {N_CAL}; levels {list(PILOT_LEVELS)}; policies {list(POLICIES)}; seeds {N_SEEDS}; run time {seconds / 3600:.2f} h",
        f"- θ₂ (level 2 vs 11, frequency, dose 1): {t2['estimate']:.4f}, 95% cluster-bootstrap {t2['ci95'][0]:.4f} to {t2['ci95'][1]:.4f}, n={t2['n_puzzles']}",
        f"- θ_comp (level 2, frequency, dose 1): {tc['estimate']:.4f}, 95% cluster-bootstrap {tc['ci95'][0]:.4f} to {tc['ci95'][1]:.4f}, n={tc['n_puzzles']}",
        f"- Dose overlap (median C–A cell Hamming, levels 2 vs 11): {summary['dose_overlap']['levels_2_11_overlap']}",
        "",
        "| Config | Excluded | Solve A | Solve B | Solve C | Solve D | Median C–A Hamming |",
        "|---|---|---|---|---|---|---|",
    ]
    for key, c in summary["by_config"].items():
        sm, q = c["solve_mean"], c["hamming_CA_quantiles"]
        fmt = lambda v: "–" if v is None else f"{v:.3f}"
        lines.append(f"| {key} | {c['exclusion_share']:.3f} | {fmt(sm['A'])} | {fmt(sm['B'])} | {fmt(sm['C'])} | "
                     f"{fmt(sm['D'])} | {fmt(q[2] if q else None)} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    batch = generate_subset("cal", N_CAL)
    puzzles = np.stack([g.puzzle for g in batch])
    solutions = np.stack([g.solution for g in batch])
    m = load_model(ROOT / "checkpoints" / "sudoku" / "hard")
    t0 = time.perf_counter()
    records = run_pilot(m, puzzles, solutions, [g.puzzle_id for g in batch])
    seconds = time.perf_counter() - t0
    raw = ROOT / "runs" / "wp1" / "pilot_records.jsonl"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("".join(json.dumps(r) + "\n" for r in records))
    summary = summarize(records)
    summary.update({"date": time.strftime("%Y-%m-%d"), "n_cal": N_CAL, "seconds": round(seconds, 1),
                    "environment": environment_record()})
    out = ROOT / "experiments" / "wp1"
    out.mkdir(parents=True, exist_ok=True)
    (out / "pilot_summary.json").write_text(json.dumps(summary, indent=2) + "\n", newline="\n")
    (out / "pilot_report.md").write_text(_report(summary, seconds), newline="\n")
    print(_report(summary, seconds))


if __name__ == "__main__":
    main()
