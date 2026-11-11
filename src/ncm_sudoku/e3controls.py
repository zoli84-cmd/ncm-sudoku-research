"""E3 controls (plan v3.6 §8.2; D57) and the secondary unit-digit target (§8.3; D62).

Non-confirmatory planning code: it runs on PROBE-TRAIN/PROBE-VAL only.

`run_controls(train, val)` and `run_unit_digit(train, val)` take one dict per subset
with these keys (arrays may be read-only memmaps from `e3data.load_level`):

- `puzzles` [n, 81] int: initial boards (0 = blank)
- `mask` [n, 81, 9] uint8: `candidate_mask` labels (`e3data.labels`)
- `empty` [n, 81] bool: originally empty cells
- `rep` [n, 81, F]: generated-branch cell states at the H1 level (level 6, plan §8.3)
- `teacher` {2, 6, 12: [n, 81, F]}: teacher cell states (`run_controls` only)

Each trained control goes through `probes.fit_selected` (same GRID x SEEDS and D63
budget as the primary probe); the per-control summary holds `config`,
`val_brier_mean` (scored: nanmean of `per_puzzle`), `tune_brier_mean` (selection
set; differs from the scored value only for the permuted control), `per_puzzle`
(list, PROBE-VAL) and a `budget` summary.
"""

import numpy as np
import torch

from ncm_sudoku.e3data import peer_counts, raw_features, surface_features
from ncm_sudoku.grid import UNITS
from ncm_sudoku.probes import brier_per_puzzle, build_inputs, fit_selected

# Plan §8.2: the permuted-representation probe is tuned on its own permuted PROBE-VAL
# (`train_va`) but scored on the UNPERMUTED PROBE-VAL pairs, as it will be on TEST.
EVAL_ON_UNPERMUTED_VAL = True
PERMUTE_SEED_TRAIN, PERMUTE_SEED_VAL = 11, 12


def permute_puzzles(arr: np.ndarray, seed: int) -> np.ndarray:
    """Permutes along axis 0, so a puzzle's whole 81-cell grid moves together."""
    return np.asarray(arr)[np.random.default_rng(seed).permutation(len(arr))]


def random_features(n: int, seed: int = 0, dim: int = 256) -> np.ndarray:
    """Standard-normal features, fixed per (puzzle, cell) for a given seed."""
    return np.random.default_rng(seed).standard_normal((n, 81, dim)).astype(np.float32)


def permute_labels(mask: np.ndarray, empty: np.ndarray, seed: int = 0) -> np.ndarray:
    """Permutes the 9-bit label vectors across all empty-cell examples; given cells
    keep their (unused) rows."""
    out = np.array(mask, copy=True)
    rows = out[empty]
    out[empty] = rows[np.random.default_rng(seed).permutation(len(rows))]
    return out


def marginal_brier(mask_tr, empty_tr, mask_va, empty_va) -> np.ndarray:
    """Per-puzzle PROBE-VAL Brier of the per-position mean candidate bits on
    PROBE-TRAIN empty cells (§8.2 marginal baseline, §8.3 aggregation). Positions
    never empty in PROBE-TRAIN fall back to the pooled mean."""
    e_tr = np.asarray(empty_tr, bool)
    m_tr = np.asarray(mask_tr, np.float64) * e_tr[..., None]
    counts = e_tr.sum(axis=0)[:, None]  # (81, 1)
    pooled = m_tr.sum(axis=(0, 1)) / max(int(e_tr.sum()), 1)  # (9,)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = np.where(counts > 0, m_tr.sum(axis=0) / counts, pooled)  # (81, 9)
    e_va = np.asarray(empty_va, bool)
    pz, pos = np.nonzero(e_va)
    return brier_per_puzzle(p[pos], np.asarray(mask_va)[e_va], pz, len(e_va))


def unit_digit_labels(puzzles: np.ndarray) -> np.ndarray:
    """[n, 27, 9]: 1 if digit d+1 is placed in unit u on the initial board (D62)."""
    oh = np.eye(10, dtype=np.uint8)[np.asarray(puzzles)[:, UNITS]]  # (n, 27, 9, 10)
    return oh[..., 1:].max(axis=2)


def unit_readout(cell_feats: np.ndarray) -> np.ndarray:
    """[n, 27, F]: mean of the unit's 9 cell features (D62)."""
    return np.asarray(cell_feats, np.float32)[:, UNITS].mean(axis=2)


def roc_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Rank-based (Mann-Whitney) ROC-AUC pooled over all entries; ties get average
    ranks. NaN when a class is missing (not interpretable, §8.3)."""
    s = np.asarray(scores, np.float64).ravel()
    y = np.asarray(labels).ravel().astype(bool)
    n1 = int(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    _, inv, counts = np.unique(s, return_inverse=True, return_counts=True)
    avg_rank = np.cumsum(counts) - (counts - 1) / 2.0  # 1-based average rank per value
    ranks = avg_rank[inv]
    return float((ranks[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def unit_metrics(pred: np.ndarray, y: np.ndarray, puzzle_idx: np.ndarray, n_puzzles: int) -> dict:
    """Exact match (all 9 digits correct at threshold 0.5) over (puzzle, unit) rows,
    pooled ROC-AUC over units x digits, and `brier_ensemble` (§8.3 aggregation) of
    the given (seed-averaged) predictions."""
    pred, y = np.asarray(pred), np.asarray(y)
    return {
        "exact_match": float(((pred >= 0.5) == (y >= 0.5)).all(axis=1).mean()),
        "roc_auc": roc_auc(pred, y),
        "brier_ensemble": float(np.nanmean(brier_per_puzzle(pred, y, puzzle_idx, n_puzzles))),
    }


def _budget_summary(fit: dict) -> dict:
    """Training budget at the selected configuration (one dict per seed), plus the
    trainable parameter count and whether any grid run hit the epoch cap (D63)."""
    cfg = tuple(fit["config"])
    selected = [info for (wd, lr, _), info in fit["budget"].items() if (wd, lr) == cfg]
    return {
        "n_params": selected[0]["n_params"] if selected else None,
        "selected": selected,
        "any_hit_cap": any(info["hit_cap"] for info in fit["budget"].values()),
    }


def summarize_fit(fit: dict) -> dict:
    """JSON-ready summary of a `fit_selected` result (preds dropped)."""
    return {
        "config": list(fit["config"]),
        "val_brier_mean": float(fit["val_brier_mean"]),
        "tune_brier_mean": float(fit["tune_brier_mean"]),
        "per_puzzle": np.asarray(fit["per_puzzle"], np.float64).tolist(),
        "budget": _budget_summary(fit),
    }


def fit_cells(f_tr, f_va, train, val, kind, mask_tr=None, f_tune=None, n_positions=81, **kw) -> dict:
    """Builds cell examples from [n, 81, F] features and runs `fit_selected`.
    `mask_tr` overrides the training labels; `f_tune` is the selection-set feature
    array (labels stay the true PROBE-VAL labels)."""
    mask_tr = train["mask"] if mask_tr is None else mask_tr
    Xtr, _, _ = build_inputs(f_tr, train["empty"], n_positions)
    Ytr = torch.from_numpy(np.asarray(mask_tr)[train["empty"]].astype(np.float32))
    Xva, pz_va, _ = build_inputs(f_va, val["empty"], n_positions)
    Yva = torch.from_numpy(np.asarray(val["mask"])[val["empty"]].astype(np.float32))
    n_va = len(val["empty"])
    train_va = None
    if f_tune is not None:
        Xt, pz_t, _ = build_inputs(f_tune, val["empty"], n_positions)
        train_va = (Xt, Yva, pz_t.numpy(), n_va)
    return fit_selected(Xtr, Ytr, Xva, Yva, pz_va.numpy(), n_va, kind, train_va=train_va, **kw)


def permuted_control(rep_tr, rep_va, train, val, **kw) -> dict:
    """Permuted-representation linear probe (§8.2 item 4): whole grids permuted with
    independent train/val seeds, tuned on permuted val, scored on unpermuted val.
    Returns the raw `fit_selected` dict (used by `run_controls` at the H1 level and
    by the probe-suite script at levels 2 and 12)."""
    return fit_cells(
        permute_puzzles(rep_tr, PERMUTE_SEED_TRAIN),
        rep_va,
        train,
        val,
        "linear",
        f_tune=permute_puzzles(rep_va, PERMUTE_SEED_VAL),
        **kw,
    )


def _clue_count(puzzles) -> int:
    """The single clue-count stratum of the permutation (§8.2); raises if mixed."""
    counts = np.unique((np.asarray(puzzles) != 0).sum(axis=1))
    if len(counts) != 1:
        raise ValueError(f"permutation control expects one clue-count stratum, got {counts.tolist()}")
    return int(counts[0])


def run_controls(train: dict, val: dict, epochs: int = 50, batch: int = 4096, min_steps: int = 2000) -> dict:
    """All seven §8.2 controls (D57) plus the rule ceiling and the marginal baseline,
    each scored on PROBE-VAL. See the module docstring for the dict keys."""
    kw = dict(epochs=epochs, batch=batch, min_steps=min_steps)
    if _clue_count(train["puzzles"]) != _clue_count(val["puzzles"]):
        raise ValueError("PROBE-TRAIN and PROBE-VAL clue-count strata differ")
    p_tr, p_va = np.asarray(train["puzzles"]), np.asarray(val["puzzles"])
    rep_tr, rep_va = np.asarray(train["rep"], np.float32), np.asarray(val["rep"], np.float32)
    out = {}

    # 1. Raw puzzle: own one-hot || 20 peers' one-hots (|| position, added by build_inputs).
    raw_tr, raw_va = raw_features(p_tr), raw_features(p_va)
    for kind in ("linear", "mlp"):
        out[f"raw_{kind}"] = summarize_fit(fit_cells(raw_tr, raw_va, train, val, kind, **kw))
    del raw_tr, raw_va

    # 2. Peer digit counts, and the exact candidate_mask rule (count == 0) as the ceiling.
    pc_tr, pc_va = peer_counts(p_tr), peer_counts(p_va)
    out["peer_counts_linear"] = summarize_fit(fit_cells(pc_tr, pc_va, train, val, "linear", **kw))
    e_va = np.asarray(val["empty"], bool)
    pz, _ = np.nonzero(e_va)
    rule = brier_per_puzzle((pc_va == 0)[e_va], np.asarray(val["mask"])[e_va], pz, len(e_va))
    out["rule"] = {"config": None, "val_brier_mean": float(np.nanmean(rule)), "per_puzzle": rule.tolist(), "budget": None}

    # 3. Surface: clue count, global clue digit frequencies (|| position).
    out["surface_linear"] = summarize_fit(
        fit_cells(surface_features(p_tr), surface_features(p_va), train, val, "linear", **kw)
    )

    # 4. Permuted representation (primary H1 control): one clue-count stratum, whole
    # grids permuted, independent seeds; tuned on permuted val, scored on unpermuted val.
    out["permuted_linear"] = summarize_fit(permuted_control(rep_tr, rep_va, train, val, **kw))

    # 5. Random size-matched features, one seed-0 stream: train puzzles first, then val.
    rnd = random_features(len(p_tr) + len(p_va), seed=0, dim=rep_tr.shape[-1])
    out["random_linear"] = summarize_fit(fit_cells(rnd[: len(p_tr)], rnd[len(p_tr) :], train, val, "linear", **kw))
    del rnd

    # 6. Label permutation across PROBE-TRAIN empty-cell examples; true val labels.
    out["label_permuted_linear"] = summarize_fit(
        fit_cells(rep_tr, rep_va, train, val, "linear", mask_tr=permute_labels(train["mask"], train["empty"], 0), **kw)
    )

    # 7. Teacher representation at levels 2, 6, 12 (one level loaded at a time).
    for lv in (2, 6, 12):
        out[f"teacher_L{lv:02d}_linear"] = summarize_fit(
            fit_cells(train["teacher"][lv], val["teacher"][lv], train, val, "linear", **kw)
        )

    mb = marginal_brier(train["mask"], train["empty"], val["mask"], val["empty"])
    out["marginal"] = {"config": None, "val_brier_mean": float(np.nanmean(mb)), "per_puzzle": mb.tolist(), "budget": None}
    return out


def _fit_unit(f_tr, f_va, p_tr, p_va, **kw) -> dict:
    """Unit-level linear probe: unit readout || unit one-hot (27), labels [n, 27, 9]."""
    Xtr, _, _ = build_inputs(unit_readout(f_tr), np.ones((len(p_tr), 27), bool), 27)
    Xva, pz, _ = build_inputs(unit_readout(f_va), np.ones((len(p_va), 27), bool), 27)
    Ytr = torch.from_numpy(unit_digit_labels(p_tr).reshape(-1, 9).astype(np.float32))
    y_va = unit_digit_labels(p_va).reshape(-1, 9).astype(np.float32)
    fit = fit_selected(Xtr, Ytr, Xva, torch.from_numpy(y_va), pz.numpy(), len(p_va), "linear", **kw)
    # "brier" = mean of the per-seed Briers (scale of every other Brier); exact match,
    # ROC-AUC and brier_ensemble use the seed-averaged predictions.
    return {**summarize_fit(fit), **unit_metrics(fit["preds"], y_va, pz.numpy(), len(p_va)),
            "brier": float(fit["val_brier_mean"])}


def run_unit_digit(train: dict, val: dict, epochs: int = 50, batch: int = 4096, min_steps: int = 2000) -> dict:
    """D62 unit-digit target on `rep` ("generated") and on the raw own-cell one-hots
    ("raw", reported next to it because the label is readable from the clues)."""
    kw = dict(epochs=epochs, batch=batch, min_steps=min_steps)
    p_tr, p_va = np.asarray(train["puzzles"]), np.asarray(val["puzzles"])
    own = lambda p: np.eye(10, dtype=np.float32)[p]  # noqa: E731  own-cell one-hot (10)
    return {
        "generated": _fit_unit(train["rep"], val["rep"], p_tr, p_va, **kw),
        "raw": _fit_unit(own(p_tr), own(p_va), p_tr, p_va, **kw),
    }
