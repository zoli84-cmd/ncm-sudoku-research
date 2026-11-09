"""Terminal distribution gate on the frozen generator (plan §4.1; D27, D33-D36).

Usage: uv run python scripts/wp1_gate.py
Single look: refuses to run when experiments/wp1/gate.json already exists.
"""

import json
import sys
import time

import numpy as np

from ncm_sudoku.gate import GATE_N, depth_profile, model_free_gate, model_gate
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.released import load_released
from ncm_sudoku.runner import decode_codes, generate_codes
from ncm_sudoku.subsets import SEEDS, generate_subset, screen
from ncm_sudoku.validate import evaluate, parse_output_tokens

OUT = ROOT / "experiments" / "wp1" / "gate.json"


def main() -> None:
    if OUT.exists():
        sys.exit(f"{OUT} exists: the gate is a single look (D27); refusing to rerun")
    t0 = time.perf_counter()
    released_p, released_s = load_released(ROOT / "data" / "released" / "sudoku" / "hard")
    batch = generate_subset("gate", GATE_N)
    puzzles = np.stack([g.puzzle for g in batch])
    solutions = np.stack([g.solution for g in batch])
    t_gen = time.perf_counter()
    prof_fresh, prof_released = depth_profile(puzzles), depth_profile(released_p)
    mf = model_free_gate(prof_fresh, prof_released)
    t_mf = time.perf_counter()
    m = load_model(ROOT / "checkpoints" / "sudoku" / "hard")
    tokens = []
    for i in range(0, GATE_N, 128):
        tokens.append(decode_codes(m, generate_codes(m, puzzles[i : i + 128], batch_size=128)))
    tokens = np.concatenate([t.numpy() for t in tokens])
    solves = np.array([evaluate(p, parse_output_tokens(t.tolist()), s).solve
                       for p, t, s in zip(puzzles, tokens, solutions)])
    mg = model_gate(solves)
    t_model = time.perf_counter()
    scr = screen({"gate": batch}, released_s)
    result = {
        "date": time.strftime("%Y-%m-%d"),
        "seed_namespace": SEEDS["gate"],
        "n": GATE_N,
        "attempts_total": int(sum(g.attempts for g in batch)),
        "profiles": {"gate": prof_fresh, "released": prof_released},
        "model_free_gate": mf,
        "model_gate": mg,
        "passed": bool(mf["passed"] and mg["outcome"] == "equivalent"),
        "screen": {"n_entries": scr["n_entries"], "exact_duplicates": scr["exact_duplicates"],
                   "signature_collisions": scr["signature_collisions"]},
        "seconds": {"generate": round(t_gen - t0, 1), "model_free": round(t_mf - t_gen, 1),
                    "model": round(t_model - t_mf, 1)},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", newline="\n")
    print(json.dumps({k: result[k] for k in ("model_free_gate", "model_gate", "passed")}, indent=2))


if __name__ == "__main__":
    main()
