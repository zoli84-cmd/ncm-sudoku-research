"""E3 controls (plan v3.6 §8.2; D57) and the secondary unit-digit target (§8.3; D62).

Two-set mode (pre-WP2, D64/D67): train on PROBE-TRAIN, select and score on PROBE-VAL.
Three-set mode (WP2, optional `score` argument): train on PROBE-TRAIN, select on
PROBE-VAL, score on the role's score set (TEST, or PROBE-VAL in the dry run). With
`score=None` every function returns exactly the two-set result.

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
(list, PROBE-VAL or the score set) and a `budget` summary.
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


def marginal_probs(mask_tr, empty_tr) -> np.ndarray:
    """[81, 9] float64: per-position mean candidate bits on PROBE-TRAIN empty cells;
    positions never empty in PROBE-TRAIN fall back to the pooled mean."""
    e_tr = np.asarray(empty_tr, bool)
    m_tr = np.asarray(mask_tr, np.float64) * e_tr[..., None]
    counts = e_tr.sum(axis=0)[:, None]  # (81, 1)
    pooled = m_tr.sum(axis=(0, 1)) / max(int(e_tr.sum()), 1)  # (9,)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(counts > 0, m_tr.sum(axis=0) / counts, pooled)  # (81, 9)


def marginal_brier(mask_tr, empty_tr, mask_va, empty_va) -> np.ndarray:
    """Per-puzzle PROBE-VAL (or score-set) Brier of `marginal_probs` (§8.2 marginal
    baseline, §8.3 aggregation)."""
    p = marginal_probs(mask_tr, empty_tr)
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


def _cell_set(f, d, n_positions) -> tuple:
    """(X, Y, puzzle_idx, n_puzzles) for the empty cells of subset `d`, true labels."""
    X, pz, _ = build_inputs(f, d["empty"], n_positions)
    Y = torch.from_numpy(np.asarray(d["mask"])[d["empty"]].astype(np.float32))
    return X, Y, pz.numpy(), len(d["empty"])


def fit_cells(
    f_tr, f_va, train, val, kind, mask_tr=None, f_tune=None, n_positions=81, f_score=None, score=None, **kw
) -> dict:
    """Builds cell examples from [n, 81, F] features and runs `fit_selected`.
    `mask_tr` overrides the training labels; `f_tune` is the selection-set feature
    array (labels stay the true PROBE-VAL labels).

    Without `score` (two-set, pre-WP2): selection and scoring on PROBE-VAL (selection
    on `f_tune` rows when given). With `score` (dict with `empty`, `mask`) and its
    features `f_score` (three-set, WP2): selection on (`f_tune` or `f_va`, true
    PROBE-VAL labels), passed as `train_va`; `per_puzzle`, `preds` and `seed_preds`
    are on the score set."""
    mask_tr = train["mask"] if mask_tr is None else mask_tr
    Xtr, _, _ = build_inputs(f_tr, train["empty"], n_positions)
    Ytr = torch.from_numpy(np.asarray(mask_tr)[train["empty"]].astype(np.float32))
    if score is not None:
        if f_score is None:
            raise ValueError("fit_cells: `score` needs its features `f_score`")
        train_va = _cell_set(f_va if f_tune is None else f_tune, val, n_positions)
        return fit_selected(Xtr, Ytr, *_cell_set(f_score, score, n_positions), kind, train_va=train_va, **kw)
    Xva, pz_va, _ = build_inputs(f_va, val["empty"], n_positions)
    Yva = torch.from_numpy(np.asarray(val["mask"])[val["empty"]].astype(np.float32))
    n_va = len(val["empty"])
    train_va = None
    if f_tune is not None:
        Xt, pz_t, _ = build_inputs(f_tune, val["empty"], n_positions)
        train_va = (Xt, Yva, pz_t.numpy(), n_va)
    return fit_selected(Xtr, Ytr, Xva, Yva, pz_va.numpy(), n_va, kind, train_va=train_va, **kw)


def permuted_control(rep_tr, rep_va, train, val, rep_score=None, score=None, **kw) -> dict:
    """Permuted-representation linear probe (§8.2 item 4): whole grids permuted with
    independent train/val seeds, tuned on permuted val, scored on unpermuted val
    (with `score`: on the unpermuted score set `rep_score`).
    Returns the raw `fit_selected` dict (used by `run_controls` at the H1 level and
    by the probe-suite script at levels 2 and 12)."""
    return fit_cells(
        permute_puzzles(rep_tr, PERMUTE_SEED_TRAIN),
        rep_va,
        train,
        val,
        "linear",
        f_tune=permute_puzzles(rep_va, PERMUTE_SEED_VAL),
        f_score=rep_score,
        score=score,
        **kw,
    )


def first_n(train: dict, n: int) -> dict:
    """The first `n` PROBE-TRAIN puzzles of `puzzles`, `mask`, `empty` (and `rep` when
    present), as the training-size curve slices them."""
    return {k: train[k][:n] for k in ("puzzles", "mask", "empty", "rep") if k in train}


def random_rows(n_train: int, val_ids: list[str], score_ids: list[str]) -> np.ndarray:
    """Rows of one seed-0 `random_features(n_train + n_val + n_new)` stream for the
    score puzzles (spec ambiguity 17): the stream is train, then val, then the score
    puzzles not in val. Score puzzles in val reuse their val rows; new ones take
    `n_train + n_val + j` in score order. A longer stream leaves the train/val rows
    unchanged (same generator, sequential draws)."""
    score_ids = list(score_ids)
    if len(set(score_ids)) != len(score_ids):
        raise ValueError("random_rows: duplicate score ids")
    val_ids = list(val_ids)
    val_pos = {pid: i for i, pid in enumerate(val_ids)}
    rows, j = [], 0
    for pid in score_ids:
        if pid in val_pos:
            rows.append(n_train + val_pos[pid])
        else:
            rows.append(n_train + len(val_ids) + j)
            j += 1
    return np.asarray(rows, dtype=np.int64)


def _clue_count(puzzles) -> int:
    """The single clue-count stratum of the permutation (§8.2); raises if mixed."""
    counts = np.unique((np.asarray(puzzles) != 0).sum(axis=1))
    if len(counts) != 1:
        raise ValueError(f"permutation control expects one clue-count stratum, got {counts.tolist()}")
    return int(counts[0])


def run_controls(
    train: dict,
    val: dict,
    score: dict | None = None,
    epochs: int = 50,
    batch: int = 4096,
    min_steps: int = 2000,
    fits: dict | None = None,
) -> dict:
    """All seven §8.2 controls (D57) plus the rule ceiling and the marginal baseline.
    See the module docstring for the dict keys.

    Without `score`: selected and scored on PROBE-VAL (pre-WP2, unchanged). With
    `score` (keys `ids`, `puzzles`, `mask`, `empty`, `rep`, `teacher`; `train` and
    `val` must carry `ids`, and the score ids must not overlap the train ids):
    trained on `train`, selected on `val`, scored on `score`; rule and marginal are
    computed on `score`; random features for the score puzzles come from
    `random_rows` (spec ambiguity 17).

    `fits` (optional dict, filled in place): the raw `fit_selected` dict per trained
    control name; `fits["rule"] = {"preds"}` (peer count == 0 as float32 0/1) and
    `fits["marginal"] = {"preds", "probs"}` (float32 `marginal_probs` rows of the
    scored cells, and the [81, 9] table)."""
    kw = dict(epochs=epochs, batch=batch, min_steps=min_steps)
    if _clue_count(train["puzzles"]) != _clue_count(val["puzzles"]):
        raise ValueError("PROBE-TRAIN and PROBE-VAL clue-count strata differ")
    if score is not None:
        if any("ids" not in d for d in (train, val, score)):
            raise ValueError("run_controls: train, val and score need `ids` when a score set is given")
        if set(train["ids"]) & set(score["ids"]):
            raise ValueError("run_controls: score puzzles overlap PROBE-TRAIN")
    sc = val if score is None else score
    p_tr, p_va, p_sc = (np.asarray(d["puzzles"]) for d in (train, val, sc))
    rep_tr, rep_va = np.asarray(train["rep"], np.float32), np.asarray(val["rep"], np.float32)
    rep_sc = np.asarray(sc["rep"], np.float32)
    out = {}

    def keep(name, res):
        if fits is not None:
            fits[name] = res
        out[name] = summarize_fit(res)

    def fit(name, f_tr, f_va, f_sc, kind="linear", **extra):
        if score is None:
            keep(name, fit_cells(f_tr, f_va, train, val, kind, **extra, **kw))
        else:
            keep(name, fit_cells(f_tr, f_va, train, val, kind, f_score=f_sc, score=score, **extra, **kw))

    # 1. Raw puzzle: own one-hot || 20 peer one-hots (|| position, added by build_inputs).
    raw_tr, raw_va, raw_sc = raw_features(p_tr), raw_features(p_va), raw_features(p_sc)
    for kind in ("linear", "mlp"):
        fit(f"raw_{kind}", raw_tr, raw_va, raw_sc, kind)
    del raw_tr, raw_va, raw_sc

    # 2. Peer digit counts, and the exact candidate_mask rule (count == 0) as the ceiling.
    pc_tr, pc_va, pc_sc = peer_counts(p_tr), peer_counts(p_va), peer_counts(p_sc)
    fit("peer_counts_linear", pc_tr, pc_va, pc_sc)
    e_sc = np.asarray(sc["empty"], bool)
    pz, pos = np.nonzero(e_sc)
    rule = brier_per_puzzle((pc_sc == 0)[e_sc], np.asarray(sc["mask"])[e_sc], pz, len(e_sc))
    out["rule"] = {"config": None, "val_brier_mean": float(np.nanmean(rule)), "per_puzzle": rule.tolist(), "budget": None}
    if fits is not None:
        fits["rule"] = {"preds": (pc_sc == 0)[e_sc].astype(np.float32)}

    # 3. Surface: clue count, global clue digit frequencies (|| position).
    fit("surface_linear", surface_features(p_tr), surface_features(p_va), surface_features(p_sc))

    # 4. Permuted representation (primary H1 control): one clue-count stratum, whole
    # grids permuted, independent seeds; tuned on permuted val, scored unpermuted.
    if score is None:
        keep("permuted_linear", permuted_control(rep_tr, rep_va, train, val, **kw))
    else:
        keep("permuted_linear", permuted_control(rep_tr, rep_va, train, val, rep_score=rep_sc, score=score, **kw))

    # 5. Random size-matched features, one seed-0 stream: train puzzles first, then val,
    # then the score puzzles not in val (score puzzles in val reuse their val rows).
    n_tr, n_va = len(p_tr), len(p_va)
    if score is None:
        rows, n_new = None, 0
    else:
        rows = random_rows(n_tr, val["ids"], score["ids"])
        n_new = int((rows >= n_tr + n_va).sum())
    rnd = random_features(n_tr + n_va + n_new, seed=0, dim=rep_tr.shape[-1])
    fit("random_linear", rnd[:n_tr], rnd[n_tr : n_tr + n_va], None if rows is None else rnd[rows])
    del rnd

    # 6. Label permutation across PROBE-TRAIN empty-cell examples; true val/score labels.
    fit("label_permuted_linear", rep_tr, rep_va, rep_sc, mask_tr=permute_labels(train["mask"], train["empty"], 0))

    # 7. Teacher representation at levels 2, 6, 12 (one level loaded at a time).
    for lv in (2, 6, 12):
        fit(f"teacher_L{lv:02d}_linear", train["teacher"][lv], val["teacher"][lv], sc["teacher"][lv])

    mb = marginal_brier(train["mask"], train["empty"], sc["mask"], sc["empty"])
    out["marginal"] = {"config": None, "val_brier_mean": float(np.nanmean(mb)), "per_puzzle": mb.tolist(), "budget": None}
    if fits is not None:
        probs = marginal_probs(train["mask"], train["empty"])
        fits["marginal"] = {"preds": probs[pos].astype(np.float32), "probs": probs}
    return out


def _fit_unit(f_tr, f_va, p_tr, p_va, f_sc=None, p_sc=None, **kw) -> tuple[dict, dict]:
    """Unit-level linear probe: unit readout || unit one-hot (27), labels [n, 27, 9].
    With `f_sc`/`p_sc`: selected on the val units, scored on the score units.
    Returns (summary with `unit_metrics` on the scored predictions, raw fit dict)."""

    def units(f, p):
        X, pz, _ = build_inputs(unit_readout(f), np.ones((len(p), 27), bool), 27)
        return X, unit_digit_labels(p).reshape(-1, 9).astype(np.float32), pz.numpy(), len(p)

    Xtr, _, _ = build_inputs(unit_readout(f_tr), np.ones((len(p_tr), 27), bool), 27)
    Ytr = torch.from_numpy(unit_digit_labels(p_tr).reshape(-1, 9).astype(np.float32))
    Xva, y_va, pz_va, n_va = units(f_va, p_va)
    if p_sc is None:
        X, y, pz, n, train_va = Xva, y_va, pz_va, n_va, None
    else:
        X, y, pz, n = units(f_sc, p_sc)
        train_va = (Xva, torch.from_numpy(y_va), pz_va, n_va)
    fit = fit_selected(Xtr, Ytr, X, torch.from_numpy(y), pz, n, "linear", train_va=train_va, **kw)
    # "brier" = mean of the per-seed Briers (scale of every other Brier); exact match,
    # ROC-AUC and brier_ensemble use the seed-averaged predictions.
    summary = {**summarize_fit(fit), **unit_metrics(fit["preds"], y, pz, n), "brier": float(fit["val_brier_mean"])}
    return summary, fit


def run_unit_digit(
    train: dict,
    val: dict,
    score: dict | None = None,
    epochs: int = 50,
    batch: int = 4096,
    min_steps: int = 2000,
    fits: dict | None = None,
) -> dict:
    """D62 unit-digit target on `rep` ("generated") and on the raw own-cell one-hots
    ("raw", reported next to it because the label is readable from the clues).
    With `score` (keys `puzzles`, `rep`): selected on the val units, scored on the
    score units. `fits` (optional, filled in place) gets the raw `fit_selected` dicts."""
    kw = dict(epochs=epochs, batch=batch, min_steps=min_steps)
    p_tr, p_va = np.asarray(train["puzzles"]), np.asarray(val["puzzles"])
    p_sc = None if score is None else np.asarray(score["puzzles"])
    own = lambda p: np.eye(10, dtype=np.float32)[p]  # noqa: E731  own-cell one-hot (10)
    inputs = {
        "generated": (train["rep"], val["rep"], None if score is None else score["rep"]),
        "raw": (own(p_tr), own(p_va), None if score is None else own(p_sc)),
    }
    out = {}
    for name, (f_tr, f_va, f_sc) in inputs.items():
        out[name], fit = _fit_unit(f_tr, f_va, p_tr, p_va, f_sc=f_sc, p_sc=p_sc, **kw)
        if fits is not None:
            fits[name] = fit
    return out
