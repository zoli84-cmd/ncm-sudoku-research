"""E3 equivariance pilot (plan v3.6 §8.4; D59). Non-confirmatory planning code.

Each predictor maps puzzles [b, 81] to candidate probabilities [b, 81, 9]; the
scripts pass one predictor per seed probe (`model_predict_fn`: level-6 per-cell
probes in `scripts/e3_equiv_power.py`, level-12 whole-layer probes in
`scripts/lock_equiv_l12.py`), tests pass exact predictors.

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
    acceptable: float | None = None,
) -> dict:
    """Uses the first `n` puzzles in the given order (`puzzles[:n]`; on TEST, indices
    0..199 of the TEST generation order). Returns `deviation` {kind: [n]}, `seed_noise`
    [n] (mean pairwise predictor difference on untransformed puzzles), `seed_noise_p95`
    (its 95th percentile), `acceptable` (the tolerance used: the fixed `acceptable`
    when given, e.g. the value measured on PROBE-VAL before the lock, else
    `seed_noise_p95`) and `acceptable_source` ("fixed" or "seed_noise"), `share_within`
    {kind: share of puzzles with deviation <= acceptable}, `brier` {kind: [n]}
    (back-transformed predictions vs. the original's candidate mask), `brier_original`
    [n], and their means."""
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
    seed_noise_p95 = float(np.percentile(seed_noise, 95))
    source = "seed_noise" if acceptable is None else "fixed"
    acceptable = seed_noise_p95 if acceptable is None else float(acceptable)
    return {
        "n": n,
        "k": k,
        "seed": seed,
        "n_predictors": len(predict_fns),
        "deviation": deviation,
        "seed_noise": seed_noise,
        "seed_noise_p95": seed_noise_p95,
        "acceptable": acceptable,
        "acceptable_source": source,
        "share_within": {kind: float(np.mean(v <= acceptable)) for kind, v in deviation.items()},
        "mean_deviation": {kind: float(v.mean()) for kind, v in deviation.items()},
        "brier": brier_t,
        "brier_original": brier_original,
        "mean_brier": {kind: float(v.mean()) for kind, v in brier_t.items()},
        "mean_brier_original": float(brier_original.mean()),
    }


def cell_level_states(m: NcmModel, puzzles: np.ndarray, level: int, batch: int = 50) -> np.ndarray:
    """Generated-branch cumulative state Z_{<=level} at the cell tokens, [b, 81, 256]."""
    out = []
    for i in range(0, len(puzzles), batch):
        codes = generate_codes(m, puzzles[i : i + batch], batch_size=batch)
        out.append(cell_states(cumulative_states(m, codes, upto=level)[level - 1]).numpy())
    return np.concatenate(out)


def level6_states(m: NcmModel, puzzles: np.ndarray, batch: int = 50) -> np.ndarray:
    """Generated-branch cumulative state Z_{<=6} at the cell tokens, [b, 81, 256]."""
    return cell_level_states(m, puzzles, LEVEL, batch)


def model_predict_fn(
    m: NcmModel,
    probe: torch.nn.Module,
    cache: dict | None = None,
    level: int = LEVEL,
    features: Callable[[np.ndarray], np.ndarray] | None = None,
) -> Callable:
    """Default predictor: generate -> level-`level` cell states -> `features` (e.g. the
    D66 whole-layer features; identity when None) -> probe on all 81 cells.
    Predictors sharing `cache` (and the same `level` and `features` object) run the
    model and the feature builder once per puzzle batch."""
    cache = {} if cache is None else cache

    def predict(puzzles: np.ndarray) -> np.ndarray:
        puzzles = np.ascontiguousarray(puzzles)
        key = (level, features, puzzles.tobytes())
        if key not in cache:
            states = level6_states(m, puzzles) if level == LEVEL else cell_level_states(m, puzzles, level)
            cache[key] = states if features is None else features(states)
        feats = cache[key]
        X, _, _ = build_inputs(feats, np.ones(feats.shape[:2], bool))
        with torch.no_grad():
            return probe(X).numpy().reshape(len(puzzles), 81, 9)

    return predict
