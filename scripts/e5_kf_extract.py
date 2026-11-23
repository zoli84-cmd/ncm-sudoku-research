"""E5 positive control, step 1: activations of the Kniazev & Fijalkow model at [clues_end].

Runs in the separate KF environment, not in the project environment (D94):

    UV_PROJECT_ENVIRONMENT=.venv-kf PYTHONPATH=third_party/sudoku-residual \
        .venv-kf/Scripts/python.exe scripts/e5_kf_extract.py --dtype bfloat16 [--force]

Uses only the upstream code at the pinned commit (third_party/sudoku-residual, a9b2069):
`load_checkpoint` restores the released step-25452 checkpoint, `make_intermediates_fn`
runs the same full-sequence forward pass as their `collect_activations`, on the
token sequences stored in the released `activations.npz` (clue order as the model saw
it), padded with PAD to 300 tokens, batch 64. The anchor is the SEP position
`n_clues[i]` (their `anchor_positions(..., "sep")`), and `post_mlp` of block i is
the residual stream after block i (layers 1..8 of the paper).

Also writes the per-cell candidate split exactly as their
`plots/scripts/fig_probe_acc_by_layer.py` draws it: for each cell, the puzzles where
the cell is empty, `train_test_split(arange(n), test_size=0.2, random_state=42)`.

Outputs (git-ignored): runs/e5/kf/acts_<dtype>.npy (6400, 8, 576) float32 and
runs/e5/kf/split.npy (6400, 81) int8 (0 = cell filled, 1 = train, 2 = test);
record: experiments/e5/kf_extract_<dtype>.json. Refuses to overwrite unless --force.
"""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import jax
import jax.numpy as jnp
import numpy as np
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
KF = ROOT / "third_party" / "sudoku-residual"
ART = ROOT / "data" / "kf" / "artifacts"
CKPT = ART / "results" / "3M-backtracking-packing" / "checkpoint"
META = ART / "results" / "3M-backtracking-packing" / "activations.npz"
OUT = ROOT / "runs" / "e5" / "kf"
REC = ROOT / "experiments" / "e5"
PINNED_COMMIT = "a9b206955bfd1089a7253511fa9371066ecca570"
BATCH = 64


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args, cwd=ROOT) -> str:
    return subprocess.check_output(["git", "-C", str(cwd), *args], text=True).strip()


def candidate_split(puzzles) -> np.ndarray:
    """(n, 81) int8: 0 = cell filled, 1 = train, 2 = test, per their figure script."""
    split = np.zeros((len(puzzles), 81), dtype=np.int8)
    for c in range(81):
        rel = np.array([i for i, p in enumerate(puzzles) if p[c] not in "123456789"])
        idx_train, idx_test = train_test_split(np.arange(len(rel)), test_size=0.2, random_state=42)
        split[rel[idx_train], c] = 1
        split[rel[idx_test], c] = 2
    return split


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dtype", choices=["bfloat16", "float32"], default="bfloat16")
    ap.add_argument("--limit", type=int, default=None, help="first n puzzles only (timing checks)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    suffix = args.dtype if args.limit is None else f"{args.dtype}_first{args.limit}"
    acts_path = OUT / f"acts_{suffix}.npy"
    rec_path = REC / f"kf_extract_{suffix}.json"
    if rec_path.exists() and not args.force:
        sys.exit(f"{rec_path.relative_to(ROOT)} exists; rerun with --force")

    commit = git("rev-parse", "HEAD", cwd=KF)
    if commit != PINNED_COMMIT or git("status", "--porcelain", cwd=KF):
        sys.exit(f"third_party/sudoku-residual must be clean at {PINNED_COMMIT}, found {commit}")
    sys.path.insert(0, str(KF))
    from sudoku.activations import anchor_positions, load_checkpoint, make_intermediates_fn
    from sudoku.data import SEP_TOKEN
    from sudoku.model import GPT2Model, TransformerConfig

    meta = np.load(META, allow_pickle=False)
    puzzles = [str(p) for p in meta["puzzles"]]
    seqs = meta["sequences"].astype(np.int32)
    n_clues = meta["n_clues"].astype(np.int64)
    if args.limit is not None:
        puzzles, seqs, n_clues = puzzles[: args.limit], seqs[: args.limit], n_clues[: args.limit]
    anchors = np.array(anchor_positions(n_clues, "sep"))
    if not np.all(seqs[np.arange(len(seqs)), anchors] == SEP_TOKEN):
        sys.exit("anchor is not the SEP token in every stored sequence")

    t0 = time.perf_counter()
    params, model = load_checkpoint(str(CKPT))
    if args.dtype != model.config.dtype:
        cfg = TransformerConfig(**{**model.config.__dict__, "dtype": args.dtype})
        model = GPT2Model(cfg)
    t_load = time.perf_counter() - t0
    fwd = make_intermediates_fn(model)
    n_layers = model.config.n_layers

    acts = np.zeros((len(seqs), n_layers, model.config.d_model), dtype=np.float32)
    t0 = time.perf_counter()
    for start in range(0, len(seqs), BATCH):
        batch = jnp.asarray(seqs[start : start + BATCH])
        _, inter = fwd(params, batch)
        rows = np.arange(batch.shape[0])
        pos = anchors[start : start + BATCH]
        for i in range(n_layers):
            acts[start : start + batch.shape[0], i] = np.asarray(inter[f"layer_{i}_post_mlp"], dtype=np.float32)[rows, pos]
        print(f"forward {min(start + BATCH, len(seqs))}/{len(seqs)} ({time.perf_counter() - t0:.0f} s)", flush=True)
    t_fwd = time.perf_counter() - t0

    OUT.mkdir(parents=True, exist_ok=True)
    np.save(acts_path, acts)
    split_info = None
    if args.limit is None:
        split = candidate_split(puzzles)
        split_path = OUT / "split.npy"
        np.save(split_path, split)
        split_info = {"path": str(split_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(split_path),
                      "n_train_entries": int((split == 1).sum()), "n_test_entries": int((split == 2).sum()),
                      "rule": "per cell: puzzles with the cell empty, train_test_split(arange(n), test_size=0.2, random_state=42)"}

    record = {
        "date": time.strftime("%Y-%m-%d"),
        "note": "E5 positive control (D94), non-confirmatory; activations of the Kniazev & Fijalkow model",
        "dtype": args.dtype,
        "n_puzzles": len(seqs),
        "batch": BATCH,
        "anchor": "SEP position n_clues[i]",
        "layers": "post_mlp of blocks 1..8 (index 0..7)",
        "upstream_commit": commit,
        "checkpoint_step": 25452,
        "inputs": {"activations_npz_sha256": sha256(META)},
        "outputs": {"acts": {"path": str(acts_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(acts_path),
                             "shape": list(acts.shape)}, "split": split_info},
        "seconds": {"load": round(t_load, 1), "forward": round(t_fwd, 1)},
        "environment": {"python": sys.version.split()[0], "jax": jax.__version__, "numpy": np.__version__,
                        "devices": [str(d) for d in jax.devices()], "platform": platform.platform()},
        "code_state": {"commit": git("rev-parse", "HEAD"),
                       "dirty": bool(git("status", "--porcelain", "--", "scripts", "src"))},
    }
    REC.mkdir(parents=True, exist_ok=True)
    rec_path.write_text(json.dumps(record, indent=2) + "\n", newline="\n")
    print(json.dumps(record["seconds"]), acts.shape)


if __name__ == "__main__":
    main()
