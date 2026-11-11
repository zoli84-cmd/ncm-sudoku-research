"""E3 PROBE data extraction: generated/teacher cell states, logical labels, and the
§8.2 raw/peer-count/surface control features (plan v3.6 §8, §12.1; D54-D57).

`extract()` is the small-n, fully in-memory form (used directly in tests). For the
full PROBE-TRAIN/PROBE-VAL subsets (2,000 and 500 puzzles), `extract_streamed()`
writes the 12 generated levels and the 3 teacher levels straight to per-level .npy
files via `np.lib.format.open_memmap`, one `batch`-sized chunk at a time, so the
process never holds all 12 x n level arrays in memory at once (about 207 MB per
level per 2,500 puzzles).
"""

import json
from pathlib import Path

import numpy as np

from ncm_sudoku.grid import PEERS
from ncm_sudoku.labels import candidate_mask, inference_waves
from ncm_sudoku.model import NcmModel
from ncm_sudoku.runner import decode_codes, generate_codes, teacher_codes
from ncm_sudoku.states import cell_states, cumulative_states
from ncm_sudoku.validate import evaluate, parse_output_tokens

TEACHER_LEVELS = (2, 6, 12)
_PEERS_IDX = np.array([list(PEERS[c]) for c in range(81)], dtype=np.int64)  # (81, 20)


def _process_chunk(m: NcmModel, p_chunk: np.ndarray, s_chunk: np.ndarray):
    """One batch: generated cell states per level, teacher cell states at
    `TEACHER_LEVELS`, and whether the generated output solves the puzzle."""
    codes = generate_codes(m, p_chunk, batch_size=len(p_chunk))
    gen_states = cumulative_states(m, codes)
    levels = [cell_states(z).numpy() for z in gen_states]
    tokens = decode_codes(m, codes)
    solve = np.array(
        [evaluate(p, parse_output_tokens(t.tolist()), s).solve for p, s, t in zip(p_chunk, s_chunk, tokens)],
        dtype=bool,
    )
    t_states = cumulative_states(m, teacher_codes(m, s_chunk))
    teacher = {lv: cell_states(t_states[lv - 1]).numpy() for lv in TEACHER_LEVELS}
    return levels, teacher, solve


def extract(m: NcmModel, puzzles: np.ndarray, solutions: np.ndarray, batch: int = 50) -> dict:
    puzzles, solutions = np.asarray(puzzles), np.asarray(solutions)
    n = len(puzzles)
    states = [np.empty((n, 81, 256), dtype=np.float32) for _ in range(12)]
    teacher = {lv: np.empty((n, 81, 256), dtype=np.float32) for lv in TEACHER_LEVELS}
    solve = np.empty(n, dtype=bool)
    for i in range(0, n, batch):
        sl = slice(i, min(i + batch, n))
        levels, t_chunk, solve_chunk = _process_chunk(m, puzzles[sl], solutions[sl])
        for lv in range(12):
            states[lv][sl] = levels[lv]
        for lv in TEACHER_LEVELS:
            teacher[lv][sl] = t_chunk[lv]
        solve[sl] = solve_chunk
    return {"states": states, "teacher": teacher, "solve": solve}


def extract_streamed(m: NcmModel, out_dir, puzzles: np.ndarray, solutions: np.ndarray, batch: int = 50) -> np.ndarray:
    """Streaming counterpart of `extract()`: writes L01..L12.npy and T02/T06/T12.npy
    directly into `out_dir` via memmap, `batch` puzzles at a time. Returns `solve`."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    puzzles, solutions = np.asarray(puzzles), np.asarray(solutions)
    n = len(puzzles)
    level_files = [
        np.lib.format.open_memmap(out_dir / f"L{lv:02d}.npy", mode="w+", dtype=np.float32, shape=(n, 81, 256))
        for lv in range(1, 13)
    ]
    teacher_files = {
        lv: np.lib.format.open_memmap(out_dir / f"T{lv:02d}.npy", mode="w+", dtype=np.float32, shape=(n, 81, 256))
        for lv in TEACHER_LEVELS
    }
    solve = np.empty(n, dtype=bool)
    for i in range(0, n, batch):
        sl = slice(i, min(i + batch, n))
        levels, t_chunk, solve_chunk = _process_chunk(m, puzzles[sl], solutions[sl])
        for lv in range(12):
            level_files[lv][sl] = levels[lv]
        for lv in TEACHER_LEVELS:
            teacher_files[lv][sl] = t_chunk[lv]
        solve[sl] = solve_chunk
    for f in level_files:
        f.flush()
    for f in teacher_files.values():
        f.flush()
    return solve


def labels(puzzles: np.ndarray) -> dict:
    """Mask (candidate_mask, 0 on given cells), empty mask, and inference-wave depth
    (0 given, 1..k wave, STUCK, or CENSORED), computed from the puzzle only."""
    puzzles = np.asarray(puzzles)
    n = len(puzzles)
    mask = np.zeros((n, 81, 9), dtype=np.uint8)
    empty = puzzles == 0
    depth = np.empty((n, 81), dtype=np.int16)
    for i, p in enumerate(puzzles):
        mask[i] = candidate_mask(p).astype(np.uint8)
        depth[i] = inference_waves(p).depth
    return {"mask": mask, "empty": empty, "depth": depth}


def raw_features(puzzles: np.ndarray) -> np.ndarray:
    """Own one-hot (10) || the 20 peers' one-hots in `PEERS[c]` order (200)."""
    puzzles = np.asarray(puzzles)
    n = len(puzzles)
    oh = np.eye(10, dtype=np.float32)[puzzles]  # (n, 81, 10)
    peer_oh = oh[:, _PEERS_IDX, :].reshape(n, 81, 200)  # (n, 81, 20, 10) -> (n, 81, 200)
    return np.concatenate([oh, peer_oh], axis=2)


def peer_counts(puzzles: np.ndarray) -> np.ndarray:
    """For each digit 1-9, how many of the cell's 20 peers hold it."""
    puzzles = np.asarray(puzzles)
    peer_digits = puzzles[:, _PEERS_IDX]  # (n, 81, 20)
    return np.stack([(peer_digits == d).sum(axis=2) for d in range(1, 10)], axis=2).astype(np.uint8)


def surface_features(puzzles: np.ndarray) -> np.ndarray:
    """Clue count /81 (1) || clue digit frequencies /81 (9), broadcast over all 81 cells."""
    puzzles = np.asarray(puzzles)
    n = len(puzzles)
    clue_count = (puzzles != 0).sum(axis=1, keepdims=True).astype(np.float32) / 81.0  # (n, 1)
    freq = np.stack([(puzzles == d).sum(axis=1) for d in range(1, 10)], axis=1).astype(np.float32) / 81.0  # (n, 9)
    feat = np.concatenate([clue_count, freq], axis=1)  # (n, 10)
    return np.tile(feat[:, None, :], (1, 81, 1))


def save_subset(dirpath, name: str, ids, puzzles: np.ndarray, solutions: np.ndarray, ext: dict, lab: dict) -> None:
    """Writes the subset directory layout. `L*.npy`/`T*.npy` are skipped when `ext`
    has no "states"/"teacher" key (already written by `extract_streamed`)."""
    out = Path(dirpath) / name
    out.mkdir(parents=True, exist_ok=True)
    (out / "ids.json").write_text(json.dumps(list(ids)) + "\n", encoding="utf-8")
    np.save(out / "puzzles.npy", np.asarray(puzzles))
    np.save(out / "solutions.npy", np.asarray(solutions))
    np.save(out / "solve.npy", np.asarray(ext["solve"]))
    np.save(out / "mask.npy", lab["mask"])
    np.save(out / "empty.npy", lab["empty"])
    np.save(out / "depth.npy", lab["depth"])
    if "states" in ext:
        for lv in range(1, 13):
            np.save(out / f"L{lv:02d}.npy", ext["states"][lv - 1])
    if "teacher" in ext:
        for lv in TEACHER_LEVELS:
            np.save(out / f"T{lv:02d}.npy", ext["teacher"][lv])


def load_level(dirpath, name: str, level: int, teacher: bool = False) -> np.ndarray:
    """Loads one level's array, memory-mapped read-only (load one level at a time)."""
    prefix = "T" if teacher else "L"
    return np.load(Path(dirpath) / name / f"{prefix}{level:02d}.npy", mmap_mode="r")
