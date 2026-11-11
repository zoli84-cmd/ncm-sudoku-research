"""E3 probe training and the Brier endpoint (plan v3.6 §8.1-§8.3; D55, D57, D62).

`build_inputs` turns per-puzzle feature arrays into flat per-(puzzle, position)
examples, restricted to the positions flagged in `empty` and with a position
one-hot appended. The default `n_positions=81` is the primary cell probe; Task 4's
unit-level probe reuses it with `n_positions=27` (D62), running the position index
over `features.shape[1]` instead.

`train_probe` fits one (kind, wd, lr, seed) configuration with early stopping on
PROBE-VAL Brier. `fit_selected` runs the full grid x seeds sweep (D55), selects the
configuration with the lowest mean validation Brier (ties -> earliest GRID entry),
and reports the seed-averaged Brier/predictions at that configuration.

`fit_selected` deviation from the brief's literal signature: the brief lists
`fit_selected(features_tr, lab_tr, features_va, lab_va, kind, train_va=None)`, but
per-puzzle Brier aggregation (§8.3) needs a puzzle index -- and an explicit puzzle
*count* (D63 review round: never inferred from `max(index) + 1`, which silently
drops trailing puzzles with no empty cells) -- for whichever validation set is
used, same as `train_probe`'s `va_puzzle`/`n_va_puzzles`. This module therefore
adds explicit `va_puzzle`/`n_va_puzzles` parameters, and `train_va` (when given) is
a 4-tuple `(features, labels, puzzle_idx, n_puzzles)` rather than a bare
`(features, labels)` pair, for the same reason. `train_va` stands in for
(features_va, lab_va, va_puzzle, n_va_puzzles) only during grid/epoch selection;
`per_puzzle` and `preds` are always computed on the given (features_va, lab_va,
va_puzzle, n_va_puzzles) quadruple, e.g. the unpermuted PROBE-VAL for the
permuted-representation control (D55, §8.2 item 4).

Training budget (D63, amending D55): every probe trains for at least `min_steps`
gradient steps (default 2000, every `train_probe`/`fit_selected` call), so small
training sets do not get a silently smaller step budget than large ones --
`effective_epochs = max(epochs, ceil(min_steps / ceil(n / batch)))`; early stopping
on PROBE-VAL Brier is unaffected, it only runs over more epochs when `n` is small
relative to `batch`. `train_probe` records and returns the realized budget
(`best_epoch`, `epochs_run`, `n_steps`, `hit_cap`) and the trainable parameter
count (`n_params`) alongside the model and Brier; `fit_selected` surfaces these for
every (configuration, seed) pair in its `budget` output field (§8.1: the training
budget is documented for every comparison).
"""

import copy

import numpy as np
import torch

GRID = [(wd, lr) for wd in (0, 1e-4, 1e-3, 1e-2, 1e-1) for lr in (1e-3, 3e-3)]
SEEDS = (0, 1, 2)


def build_inputs(
    features: np.ndarray, empty: np.ndarray, n_positions: int = 81
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Flattens `features[n, n_positions, F]` to rows for the empty positions only,
    each row = feature vector || one-hot position index (width `n_positions`).

    Returns (X[N, F + n_positions] float32, puzzle_idx[N] long, position_idx[N] long).
    """
    features = np.asarray(features, dtype=np.float32)
    empty = np.asarray(empty, dtype=bool)
    puzzle_idx, pos_idx = np.nonzero(empty)
    feat = features[empty]  # (N, F), row-major over (puzzle, position) like nonzero()
    onehot = np.eye(n_positions, dtype=np.float32)[pos_idx]  # (N, n_positions)
    X = torch.from_numpy(np.concatenate([feat, onehot], axis=1))
    return X, torch.from_numpy(puzzle_idx).long(), torch.from_numpy(pos_idx).long()


def brier_per_puzzle(pred: np.ndarray, y: np.ndarray, puzzle_idx: np.ndarray, n_puzzles: int) -> np.ndarray:
    """Mean over the 9 bits per cell, then mean over each puzzle's empty cells (§8.3)."""
    pred = np.asarray(pred, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    cell_brier = ((pred - y) ** 2).mean(axis=1)  # (N,)
    puzzle_idx = np.asarray(puzzle_idx)
    sums = np.bincount(puzzle_idx, weights=cell_brier, minlength=n_puzzles)
    counts = np.bincount(puzzle_idx, minlength=n_puzzles)
    with np.errstate(invalid="ignore"):
        return sums / counts


def _make_model(kind: str, in_dim: int) -> torch.nn.Module:
    if kind == "linear":
        return torch.nn.Sequential(torch.nn.Linear(in_dim, 9), torch.nn.Sigmoid())
    if kind == "mlp":
        return torch.nn.Sequential(
            torch.nn.Linear(in_dim, 64), torch.nn.ReLU(), torch.nn.Linear(64, 9), torch.nn.Sigmoid()
        )
    raise ValueError(f"unknown probe kind: {kind!r}")


def _ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def train_probe(
    Xtr: torch.Tensor,
    Ytr: torch.Tensor,
    Xva: torch.Tensor,
    Yva: torch.Tensor,
    va_puzzle: np.ndarray,
    n_va_puzzles: int,
    kind: str,
    wd: float,
    lr: float,
    seed: int,
    epochs: int = 50,
    batch: int = 4096,
    min_steps: int = 2000,
) -> tuple[torch.nn.Module, float, dict]:
    """Trains one (kind, wd, lr, seed) configuration with AdamW, BCE loss, minibatch
    `batch`; keeps the epoch with the best PROBE-VAL Brier (D55). `n_va_puzzles` is
    the puzzle count for `va_puzzle` (passed explicitly, not inferred, so trailing
    puzzles with no empty cells are not silently dropped).

    Training runs for `effective_epochs = max(epochs, ceil(min_steps / steps_per_epoch))`
    full epochs (D63), so small training sets still get at least `min_steps`
    gradient steps; early stopping on PROBE-VAL Brier still picks the best epoch
    within that budget.

    Returns (model in eval mode, its Brier, budget dict with `best_epoch`,
    `epochs_run`, `n_steps`, `hit_cap` (best epoch was the last one run) and
    `n_params` (trainable parameter count)).
    """
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(seed)
    Xtr, Ytr = Xtr.float(), Ytr.float()
    Xva, Yva = Xva.float(), Yva.float()
    va_puzzle = np.asarray(va_puzzle)
    n = Xtr.shape[0]
    steps_per_epoch = _ceil_div(n, batch)
    epochs_run = max(epochs, _ceil_div(min_steps, steps_per_epoch))
    n_steps = epochs_run * steps_per_epoch

    model = _make_model(kind, Xtr.shape[1])
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd)
    loss_fn = torch.nn.BCELoss()
    gen = torch.Generator().manual_seed(seed)

    best_brier = float("inf")
    best_state = copy.deepcopy(model.state_dict())
    best_epoch = -1
    for epoch in range(epochs_run):
        model.train()
        perm = torch.randperm(n, generator=gen)
        for i in range(0, n, batch):
            idx = perm[i : i + batch]
            opt.zero_grad()
            loss = loss_fn(model(Xtr[idx]), Ytr[idx])
            loss.backward()
            opt.step()

        model.eval()
        with torch.no_grad():
            pred_va = model(Xva).numpy()
        brier = float(np.nanmean(brier_per_puzzle(pred_va, Yva.numpy(), va_puzzle, n_va_puzzles)))
        if brier < best_brier:
            best_brier = brier
            best_state = copy.deepcopy(model.state_dict())
            best_epoch = epoch

    model.load_state_dict(best_state)
    model.eval()
    info = {
        "best_epoch": best_epoch,
        "epochs_run": epochs_run,
        "n_steps": n_steps,
        "hit_cap": best_epoch == epochs_run - 1,
        "n_params": n_params,
    }
    return model, best_brier, info


def select(results: dict) -> tuple[float, float]:
    """Configuration with the lowest mean val Brier over seeds; ties go to the
    earliest GRID entry. Raises ValueError if no configuration has a usable
    (present, non-empty, non-NaN) mean Brier."""
    best_cfg, best_mean = None, float("inf")
    for cfg in GRID:
        if cfg not in results or len(results[cfg]) == 0:
            continue
        mean_brier = float(np.mean(results[cfg]))
        if np.isnan(mean_brier):
            continue
        if mean_brier < best_mean:
            best_mean, best_cfg = mean_brier, cfg
    if best_cfg is None:
        raise ValueError("select: no configuration has a usable (non-NaN) validation Brier")
    return best_cfg


def fit_selected(
    features_tr: torch.Tensor,
    lab_tr: torch.Tensor,
    features_va: torch.Tensor,
    lab_va: torch.Tensor,
    va_puzzle: np.ndarray,
    n_va_puzzles: int,
    kind: str,
    train_va: tuple[torch.Tensor, torch.Tensor, np.ndarray, int] | None = None,
    epochs: int = 50,
    batch: int = 4096,
    min_steps: int = 2000,
) -> dict:
    """Runs the GRID x SEEDS sweep (D55, D63) and the selection.

    `features_tr`/`lab_tr`: built (X, Y) training examples (output of `build_inputs`
    plus the matching label rows, e.g. `mask[empty]`).
    `features_va`/`lab_va`/`va_puzzle`/`n_va_puzzles`: the primary validation
    quadruple that `per_puzzle` and `preds` are reported on (always the given,
    unpermuted PROBE-VAL for the permuted-representation control). `n_va_puzzles`
    is passed explicitly, not inferred, so trailing puzzles with no empty cells
    still get a (NaN) row in `per_puzzle`.
    `train_va`: optional (features, labels, puzzle_idx, n_puzzles) quadruple used
    instead of (features_va, lab_va, va_puzzle, n_va_puzzles) for model selection
    (grid config and early-stopping epoch) -- the permuted control's own permuted
    PROBE-VAL.

    Returns dict with `config`, `val_brier_mean` (selection-set mean over seeds),
    `per_puzzle` (per-puzzle Brier on features_va, averaged over the 3 seed models
    at the selected config), `preds` (seed-averaged val predictions) and `budget`
    (dict keyed by (wd, lr, seed), one training-budget dict per `train_probe` call,
    §8.1: the training budget is documented for every comparison).
    """
    if train_va is not None:
        tune_X, tune_Y, tune_puzzle, tune_n_puzzles = train_va
    else:
        tune_X, tune_Y, tune_puzzle, tune_n_puzzles = features_va, lab_va, va_puzzle, n_va_puzzles

    results: dict[tuple[float, float], list[float]] = {cfg: [] for cfg in GRID}
    models: dict[tuple[float, float, int], torch.nn.Module] = {}
    budget: dict[tuple[float, float, int], dict] = {}
    for wd, lr in GRID:
        for seed in SEEDS:
            model, brier, info = train_probe(
                features_tr,
                lab_tr,
                tune_X,
                tune_Y,
                tune_puzzle,
                tune_n_puzzles,
                kind,
                wd,
                lr,
                seed,
                epochs=epochs,
                batch=batch,
                min_steps=min_steps,
            )
            results[(wd, lr)].append(brier)
            models[(wd, lr, seed)] = model
            budget[(wd, lr, seed)] = info

    cfg = select(results)
    val_brier_mean = float(np.mean(results[cfg]))

    va_puzzle_arr = np.asarray(va_puzzle)
    features_va = features_va.float()
    lab_va_np = lab_va.numpy() if isinstance(lab_va, torch.Tensor) else np.asarray(lab_va)

    preds_sum, per_puzzle_sum = None, None
    for seed in SEEDS:
        model = models[(cfg[0], cfg[1], seed)]
        model.eval()
        with torch.no_grad():
            pred = model(features_va).numpy()
        pb = brier_per_puzzle(pred, lab_va_np, va_puzzle_arr, n_va_puzzles)
        preds_sum = pred if preds_sum is None else preds_sum + pred
        per_puzzle_sum = pb if per_puzzle_sum is None else per_puzzle_sum + pb

    return {
        "config": cfg,
        "val_brier_mean": val_brier_mean,
        "per_puzzle": per_puzzle_sum / len(SEEDS),
        "preds": preds_sum / len(SEEDS),
        "budget": budget,
    }
