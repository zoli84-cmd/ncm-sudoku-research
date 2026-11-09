"""G0 running-cost measurement on 20 released puzzles (plan §2.2 item 9).

Usage: uv run python scripts/g0_cost.py
Writes experiments/g0/cost.json. Time is wall-clock; memory is process RSS from
psutil (torch allocates natively, so tracemalloc would miss it); tensor bytes are
the sizes of the produced tensors; storage compares codes with saved states.
"""

import json
import time

import psutil
import torch

from ncm_sudoku.g0 import environment_record
from ncm_sudoku.intervene import continue_generation
from ncm_sudoku.model import ROOT, level_slices, load_model
from ncm_sudoku.released import load_released
from ncm_sudoku.runner import decode_codes, generate_codes, puzzle_tensor
from ncm_sudoku.states import cumulative_states

N = 20


def _rss() -> int:
    return psutil.Process().memory_info().rss


def _measure(name, fn, results):
    rss0 = _rss()
    t0 = time.perf_counter()
    out = fn()
    dt = time.perf_counter() - t0
    tensors = out if isinstance(out, (list, tuple)) else [out]
    info = psutil.Process().memory_info()
    results[name] = {
        "seconds_total": round(dt, 3),
        "seconds_per_puzzle": round(dt / N, 4),
        "rss_before_mb": round(rss0 / 2**20, 1),
        "rss_after_mb": round(info.rss / 2**20, 1),
        "peak_working_set_mb": round(getattr(info, "peak_wset", 0) / 2**20, 1) or None,
        "output_tensor_bytes": int(sum(t.nbytes for t in tensors)),
    }
    return out


def main() -> None:
    rss_start = _rss()
    m = load_model(ROOT / "checkpoints" / "sudoku" / "hard")
    rss_model = _rss()
    puzzles, _ = load_released(ROOT / "data" / "released" / "sudoku" / "hard")
    puzzles = puzzles[:N]
    prefix = puzzle_tensor(puzzles)
    res: dict = {}
    clean = _measure("baseline_generation", lambda: generate_codes(m, puzzles, batch_size=N), res)
    _measure("cumulative_states", lambda: cumulative_states(m, clean), res)
    _measure("decode_only_branch_c", lambda: decode_codes(m, clean), res)
    end = [s.stop for s in level_slices(m.levels)]
    for lv in (2, 6, 11):
        _measure(f"regenerate_branch_d_level_{lv}", lambda lv=lv: continue_generation(m, prefix, clean[:, : end[lv - 1]], lv), res)
    n_codes = sum(m.levels)
    state_bytes = len(m.levels) * m.levels[-1] * m.vqvae.embed_dim * 4
    summary = {
        "date": time.strftime("%Y-%m-%d"),
        "n_puzzles": N,
        "batch_size": N,
        "environment": environment_record(),
        "rss_mb": {"start": round(rss_start / 2**20, 1), "after_model_load": round(rss_model / 2**20, 1)},
        "steps": res,
        "storage_bytes_per_puzzle": {
            "codes_int8": n_codes,
            "codes_int64": n_codes * 8,
            "cumulative_states_fp32_all_12_levels": state_bytes,
        },
    }
    out = ROOT / "experiments" / "g0" / "cost.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n", newline="\n")
    print(json.dumps(summary["steps"], indent=2))


if __name__ == "__main__":
    torch.set_grad_enabled(False)
    main()
