"""E2 pilot 2 on CAL: level-1 enumeration, v3.6 dose grid, damage measures (plan v3.6 §7).
Non-confirmatory.

Usage: uv run python scripts/e2_pilot2.py [--force] [--report-only | --from-raw]
Writes runs/e2p2/pilot2.json (the raw run_pilot2 output plus date, seconds, environment,
n_cal), experiments/e2p2/summary.json (summarize2 plus the same four keys) and
experiments/e2p2/report.md (UTF-8, non-confirmatory header). Refuses to run if
experiments/e2p2/summary.json already exists, unless --force is given. --from-raw rebuilds
summary.json and report.md from runs/e2p2/pilot2.json without rerunning the pilot (same
guard). --report-only rebuilds the report from the saved summary.json.
"""

import json
import os
import sys
import time

import numpy as np

from ncm_sudoku.e2p2 import run_pilot2, summarize2
from ncm_sudoku.g0 import environment_record
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.subsets import assert_generator_frozen, generate_subset

N_CAL = 300
OUT = ROOT / "experiments" / "e2p2"
RAW = ROOT / "runs" / "e2p2" / "pilot2.json"


def guard(force: bool) -> None:
    path = OUT / "summary.json"
    if path.exists() and not force:
        sys.exit(f"{path} exists: pilot-2 is a rerun-guarded script; use --force to overwrite")


def _fmt(v, nd: int = 4) -> str:
    return "–" if v is None else f"{v:.{nd}f}"


def _contrast_line(label: str, entry: dict) -> str:
    ci = entry["ci95"]
    line = (f"- {label} (frequency): {_fmt(ci['estimate'])}, 95% {ci['method']} "
            f"[{_fmt(ci['ci'][0])}, {_fmt(ci['ci'][1])}], n={ci['n']}")
    if entry.get("family"):
        fam = entry["family"]
        line += f"; family {fam['level']:.5f} {fam['method']} [{_fmt(fam['ci'][0])}, {_fmt(fam['ci'][1])}]"
    if entry.get("tost90"):
        t = entry["tost90"]
        line += f"; TOST90 {t['method']} [{_fmt(t['ci'][0])}, {_fmt(t['ci'][1])}]"
    return line


def _report(summary: dict) -> str:
    c = summary["contrasts"]
    lines = [
        "# E2 pilot-2 report",
        "",
        "**Non-confirmatory pilot (plan v3.6 §12.1).** These numbers plan the confirmatory "
        "study; they are not evidence for H2 or H3.",
        "",
        f"- CAL puzzles: {summary['n_cal']}; run time {summary['seconds'] / 3600:.2f} h",
        _contrast_line("θ₂", c["theta2"]["frequency"]),
        _contrast_line("θ_comp", c["theta_comp"]["frequency"]),
        _contrast_line("θ₂′", c["theta2_prime"]["frequency"]),
        f"- Equivalence (TOST, θ₂′ frequency inside ±0.03): {summary['equivalence_tost']}",
        "- Sham mismatch (puzzles whose sham solve differs from A; nonzero = instrumentation error): "
        f"B1≠A {summary['sham_mismatch']['level1_B1']}; "
        + ", ".join(f"L{k} {v}" for k, v in summary["sham_mismatch"]["levels_B"].items()),
        "",
        "| AUC pair | AUC A | AUC B | range | reason |",
        "|---|---|---|---|---|",
    ]
    for pair, a in summary["auc"].items():
        rng = "–" if a["range"] is None else f"[{a['range'][0]:.3f}, {a['range'][1]:.3f}]"
        lines.append(f"| {pair} | {_fmt(a['auc_a'])} | {_fmt(a['auc_b'])} | {rng} | {a['reason'] or '–'} |")
    lines += [
        "",
        "| Config | Excluded | Solve A | Solve B | Solve C | Solve D | Median TV |",
        "|---|---|---|---|---|---|---|",
    ]
    for cfg in summary["configurations"]:
        sm, q = cfg["solve_mean"], cfg["quantiles"]["tv"]
        key = f"L{cfg['level']}/{cfg['policy']}/d{cfg['dose']}"
        lines.append(f"| {key} | {_fmt(cfg['excluded_share'], 3)} | {_fmt(sm['A'], 3)} | {_fmt(sm['B'], 3)} | "
                     f"{_fmt(sm['C'], 3)} | {_fmt(sm['D'], 3)} | {_fmt(q[2] if q else None, 3)} |")
    return "\n".join(lines) + "\n"


def write_report(summary: dict, path) -> None:
    path.write_text(_report(summary), encoding="utf-8", newline="\n")


def write_summary(raw: dict) -> None:
    """summarize2 on the raw output plus its run metadata; writes summary.json and report.md."""
    summary = summarize2(raw)
    summary.update({k: raw[k] for k in ("date", "n_cal", "seconds", "environment")})
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = (OUT / "summary.json").with_suffix(".tmp")
    tmp.write_text(json.dumps(summary, indent=2) + "\n", newline="\n")
    os.replace(tmp, OUT / "summary.json")
    write_report(summary, OUT / "report.md")


def main() -> None:
    if "--report-only" in sys.argv:
        summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
        write_report(summary, OUT / "report.md")
        return
    guard(force="--force" in sys.argv)
    if "--from-raw" in sys.argv:
        write_summary(json.loads(RAW.read_text(encoding="utf-8")))
        return
    assert_generator_frozen()
    environment = environment_record()  # before the multi-hour run, so a late failure loses nothing
    batch = generate_subset("cal", N_CAL)
    puzzles = np.stack([g.puzzle for g in batch])
    solutions = np.stack([g.solution for g in batch])
    m = load_model(ROOT / "checkpoints" / "sudoku" / "hard")
    t0 = time.perf_counter()
    out = run_pilot2(m, puzzles, solutions, [g.puzzle_id for g in batch])
    out.update({"date": time.strftime("%Y-%m-%d"), "n_cal": N_CAL,
                "seconds": round(time.perf_counter() - t0, 1), "environment": environment})
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_text(json.dumps(out) + "\n", newline="\n")
    write_summary(out)


if __name__ == "__main__":
    main()
