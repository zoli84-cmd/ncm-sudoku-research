"""E3 equivariance pilot (plan v3.6 §8.4; D59). Non-confirmatory planning code.

Each predictor maps puzzles [b, 81] to candidate probabilities [b, 81, 9]; the
script passes one predictor per selected level-6 linear seed probe
(`model_predict_fn`), tests pass exact predictors.

Per puzzle i (first `n`), one `np.random.default_rng(seed)` stream draws, in this
fixed order: `k` elements of the full group, then 2 digit-only, then 2
geometric-only elements. Each transformed puzzle is predicted, the prediction is
brought back with the inverse element, and compared with the prediction on the
original puzzle: mean absolute difference over the original's empty cells x 9
digits, averaged over the elements of a kind and over predictors.

Predictive performance (§8.4) is reported next to the deviation: the Brier of the
back-transformed predictions against `candidate_mask` of the original puzzle over
its empty cells (mean over 9 bits, then cells; §8.3), per puzzle, averaged over the
elements of a kind and then over predictors (the per-seed scale used elsewhere),
and the same Brier on the untransformed puzzles (`brier_original`).
"""

from collections.abc import Callable
from itertools import combinations

import numpy as np
import torch

from ncm_sudoku.labels import candidate_mask
from ncm_sudoku.model import NcmModel
from ncm_sudoku.probes import build_inputs
from ncm_sudoku.runner import generate_codes
from ncm_sudoku.states import cell_states, cumulative_states
from ncm_sudoku.symmetry import apply_symmetry, inverse, random_symmetry, transform_predictions

KINDS = ("all", "digit", "geometric")
N_SUBSET = 2  # extra digit-only and geometric-only elements per puzzle (D59)
LEVEL = 6


def equivariance_pilot(
    puzzles: np.ndarray,
    predict_fns: list[Callable[[np.ndarray], np.ndarray]],
    n: int = 200,
    k: int = 4,
    seed: int = 0,
) -> dict:
    """Returns `deviation` {kind: [n]}, `seed_noise` [n] (mean pairwise predictor
    difference on untransformed puzzles), `acceptable` (95th percentile of
    `seed_noise`), `share_within` {kind: share of puzzles with deviation <=
    acceptable}, `brier` {kind: [n]} (back-transformed predictions vs. the
    original's candidate mask), `brier_original` [n], and their means."""
    if len(predict_fns) < 2:
        raise ValueError("seed noise needs at least two predictors")
    puzzles = np.asarray(puzzles)[:n]
    n = len(puzzles)
    rng = np.random.default_rng(seed)
    counts = {"all": k, "digit": N_SUBSET, "geometric": N_SUBSET}
    syms = [(i, kind, random_symmetry(rng, kind)) for i in range(n) for kind in KINDS for _ in range(counts[kind])]
    transformed = np.stack([apply_symmetry(puzzles[i], s) for i, _, s in syms])
    empty = puzzles == 0
    truth = np.stack([candidate_mask(p) for p in puzzles]).astype(float)

    def mad(a, b, i):
        return float(np.abs(a - b)[empty[i]].mean())

    def brier(a, i):
        return float(((a - truth[i]) ** 2)[empty[i]].mean())

    originals = [np.asarray(f(puzzles), float) for f in predict_fns]
    dev = {kind: np.zeros(n) for kind in KINDS}
    bri = {kind: np.zeros(n) for kind in KINDS}
    for f, orig in zip(predict_fns, originals):
        pred_t = np.asarray(f(transformed), float)
        for (i, kind, s), p in zip(syms, pred_t):
            back = transform_predictions(p, inverse(s))
            dev[kind][i] += mad(back, orig[i], i) / counts[kind]
            bri[kind][i] += brier(back, i) / counts[kind]
    deviation = {kind: v / len(predict_fns) for kind, v in dev.items()}
    brier_t = {kind: v / len(predict_fns) for kind, v in bri.items()}
    brier_original = np.mean([[brier(o[i], i) for i in range(n)] for o in originals], axis=0)

    pairs = list(combinations(originals, 2))
    seed_noise = np.array([np.mean([mad(a[i], b[i], i) for a, b in pairs]) for i in range(n)])
    acceptable = float(np.percentile(seed_noise, 95))
    return {
        "n": n,
        "k": k,
        "seed": seed,
        "n_predictors": len(predict_fns),
        "deviation": deviation,
        "seed_noise": seed_noise,
        "acceptable": acceptable,
        "share_within": {kind: float(np.mean(v <= acceptable)) for kind, v in deviation.items()},
        "mean_deviation": {kind: float(v.mean()) for kind, v in deviation.items()},
        "brier": brier_t,
        "brier_original": brier_original,
        "mean_brier": {kind: float(v.mean()) for kind, v in brier_t.items()},
        "mean_brier_original": float(brier_original.mean()),
    }


def level6_states(m: NcmModel, puzzles: np.ndarray, batch: int = 50) -> np.ndarray:
    """Generated-branch cumulative state Z_{<=6} at the cell tokens, [b, 81, 256]."""
    out = []
    for i in range(0, len(puzzles), batch):
        codes = generate_codes(m, puzzles[i : i + batch], batch_size=batch)
        out.append(cell_states(cumulative_states(m, codes, upto=LEVEL)[LEVEL - 1]).numpy())
    return np.concatenate(out)


def model_predict_fn(m: NcmModel, probe: torch.nn.Module, cache: dict | None = None) -> Callable:
    """Default predictor: generate -> level-6 cell states -> probe on all 81 cells.
    Predictors sharing `cache` run the model once per puzzle batch."""
    cache = {} if cache is None else cache

    def predict(puzzles: np.ndarray) -> np.ndarray:
        puzzles = np.ascontiguousarray(puzzles)
        key = puzzles.tobytes()
        if key not in cache:
            cache[key] = level6_states(m, puzzles)
        states = cache[key]
        X, _, _ = build_inputs(states, np.ones(states.shape[:2], bool))
        with torch.no_grad():
            return probe(X).numpy().reshape(len(puzzles), 81, 9)

    return predict
