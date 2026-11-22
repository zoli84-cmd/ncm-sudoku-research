"""E5 feasibility: cost of extracting and storing the generator's per-layer activations.

Usage: uv run python scripts/e5_cost.py [--force]

Non-confirmatory measurement on the first 20 released hard puzzles (already used by
G0 and E1, so no fresh puzzle is spent). The upstream generator runs one forward pass
per level: the level-1 query pass and 11 level passes, each over the 91 puzzle-prefix
positions plus that level's query positions. Forward hooks copy the input of block 1
(layer 0, the embedding) and the output of every block (layers 1..8) in every pass.

Writes experiments/e5/cost.json (timings, RSS, tensor bytes, on-disk bytes for fp32
and fp16 layouts, whether hooks change the generated codes, and whether the prefix
activations are identical across the 12 passes) and raw arrays to runs/e5/cost/
(git-ignored). Refuses to overwrite cost.json unless --force.
"""

import argparse
import json
import shutil
import sys
import time

import numpy as np
import psutil
import torch

from ncm_sudoku.g0 import code_state, environment_record
from ncm_sudoku.grid import CELL_TOKEN_INDICES
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.released import load_released
from ncm_sudoku.runner import puzzle_tensor

N = 20
REPS = 3
OUT = ROOT / "experiments" / "e5" / "cost.json"
RAW = ROOT / "runs" / "e5" / "cost"
PREFIX_CELLS = 1 + CELL_TOKEN_INDICES  # prefix = [BOS] + 89 row tokens + [BOS]


def _rss_mb() -> float:
    return round(psutil.Process().memory_info().rss / 2**20, 1)


def _peak_mb():
    peak = getattr(psutil.Process().memory_info(), "peak_wset", None)
    return round(peak / 2**20, 1) if peak else None


@torch.no_grad()
def _generate(net, x):
    return net.generate(None, x, temperature=0.0, top_k=0, top_p=1.0, cfg_scale=0.0)


@torch.no_grad()
def generate_with_capture(net, x):
    """Generate and return (codes, passes); passes[p][layer] is a (B, P + L_p, 512) fp32 copy."""
    passes: list[list[torch.Tensor]] = []
    blocks = net.transformer.blocks

    def pre0(_mod, args, kwargs):
        passes.append([args[0].detach().clone()])

    def post(_mod, _args, out):
        passes[-1].append(out.detach().clone())

    handles = [blocks[0].register_forward_pre_hook(pre0, with_kwargs=True)]
    handles += [b.register_forward_hook(post) for b in blocks]
    try:
        codes = _generate(net, x)
    finally:
        for h in handles:
            h.remove()
    return codes, passes


def _timed(fn):
    t0 = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - t0


def _save(arrays: dict[str, np.ndarray], sub: str) -> dict:
    d = RAW / sub
    d.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    for name, a in arrays.items():
        np.save(d / f"{name}.npy", a)
    dt = time.perf_counter() - t0
    disk = sum(p.stat().st_size for p in d.glob("*.npy"))
    return {"files": len(arrays), "disk_bytes": disk, "disk_bytes_per_puzzle": disk // N,
            "write_seconds": round(dt, 3)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if OUT.exists() and not args.force:
        sys.exit(f"{OUT.relative_to(ROOT)} exists; rerun with --force")

    rss = {"start": _rss_mb()}
    m = load_model(ROOT / "checkpoints" / "sudoku" / "hard")
    rss["after_model_load"] = _rss_mb()
    puzzles, _ = load_released(ROOT / "data" / "released" / "sudoku" / "hard")
    x = puzzle_tensor(puzzles[:N])
    net = m.net
    P = net.prefix_len

    # Warm-up pass (excluded from timing), then REPS alternating plain / instrumented runs.
    _generate(net, x[:2])
    t_plain, t_capture = [], []
    for _ in range(REPS):
        base, dt = _timed(lambda: _generate(net, x))
        t_plain.append(dt)
        (codes, passes), dt = _timed(lambda: generate_with_capture(net, x))
        t_capture.append(dt)
    rss["after_capture"] = _rss_mb()
    t_base, t_cap = float(np.median(t_plain)), float(np.median(t_capture))

    n_layers = len(passes[0])
    pass_lengths = [int(p[0].shape[1]) for p in passes]
    tensor_bytes = int(sum(t.nbytes for p in passes for t in p))

    # Prefix invariance across passes, per layer (max |diff| against pass 0).
    prefix_max_diff = [
        float(max((p[layer][:, :P] - passes[0][layer][:, :P]).abs().max() for p in passes))
        for layer in range(n_layers)
    ]

    def prefix_once(dtype):
        return np.stack([passes[0][l][:, :P].numpy() for l in range(n_layers)], axis=1).astype(dtype)

    def prefix_cells(dtype):
        return np.stack([passes[0][l][:, PREFIX_CELLS].numpy() for l in range(n_layers)], axis=1).astype(dtype)

    def targets(dtype):
        return {f"targets_pass{pi:02d}": np.stack([p[l][:, P:].numpy() for l in range(n_layers)], axis=1).astype(dtype)
                for pi, p in enumerate(passes)}

    def everything(dtype):
        return {f"pass{pi:02d}": np.stack([p[l].numpy() for l in range(n_layers)], axis=1).astype(dtype)
                for pi, p in enumerate(passes)}

    level7 = 6  # pass index 6 generates plan level 7 from Z<=6 (pass 0 = level 1)
    if RAW.exists():
        shutil.rmtree(RAW)
    storage = {
        "all_passes_all_positions_fp32": _save(everything(np.float32), "all_fp32"),
        "all_passes_all_positions_fp16": _save(everything(np.float16), "all_fp16"),
        "prefix_once_plus_targets_fp32": _save({"prefix": prefix_once(np.float32), **targets(np.float32)}, "dedup_fp32"),
        "prefix_once_plus_targets_fp16": _save({"prefix": prefix_once(np.float16), **targets(np.float16)}, "dedup_fp16"),
        "prefix_81_cells_fp32": _save({"prefix_cells": prefix_cells(np.float32)}, "cells_fp32"),
        "prefix_81_cells_fp16": _save({"prefix_cells": prefix_cells(np.float16)}, "cells_fp16"),
        "level7_pass_targets_fp32": _save(
            {"level7": np.stack([passes[level7][l][:, P:].numpy() for l in range(n_layers)], axis=1)}, "level7_fp32"),
    }
    fp16_err = float(max((p[l].half().float() - p[l]).abs().max() for p in passes for l in range(n_layers)))

    summary = {
        "date": time.strftime("%Y-%m-%d"),
        "note": "non-confirmatory E5 feasibility measurement; first 20 released hard puzzles",
        "n_puzzles": N,
        "batch_size": N,
        "environment": environment_record(),
        "code_state": code_state(),
        "model": {"n_layer": len(net.transformer.blocks), "n_embd": int(net.config.n_embd), "prefix_len": P,
                  "levels": list(m.levels), "captured_layers": n_layers,
                  "layer_definition": "0 = input of block 1 (embedding); k = output of block k"},
        "passes": {"count": len(passes), "lengths": pass_lengths, "positions_total": int(sum(pass_lengths))},
        "timing_seconds": {"repetitions": REPS, "plain_runs": [round(t, 3) for t in t_plain],
                           "capture_runs": [round(t, 3) for t in t_capture],
                           "plain_generation_median": round(t_base, 3), "generation_with_capture_median": round(t_cap, 3),
                           "plain_per_puzzle": round(t_base / N, 4), "capture_per_puzzle": round(t_cap / N, 4),
                           "capture_overhead_ratio": round(t_cap / t_base, 3)},
        "codes_identical_with_hooks": bool(torch.equal(base, codes)),
        "prefix_max_abs_diff_across_passes_per_layer": prefix_max_diff,
        "fp16_max_abs_roundtrip_error": fp16_err,
        "rss_mb": rss,
        "peak_working_set_mb": _peak_mb(),
        "in_memory_fp32_bytes": {"total": tensor_bytes, "per_puzzle": tensor_bytes // N},
        "storage": storage,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n", newline="\n")
    print(json.dumps({k: summary[k] for k in ("timing_seconds", "codes_identical_with_hooks",
                                              "prefix_max_abs_diff_across_passes_per_layer", "passes")}, indent=2))
    print(json.dumps(storage, indent=2))


if __name__ == "__main__":
    main()
