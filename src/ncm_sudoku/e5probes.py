"""E5 global-position candidate probes (D95).

A single activation vector per puzzle (one sequence position, e.g. the [clues_end]
token of the Kniazev & Fijalkow model) is read by an untied linear head with one
sigmoid output per (cell, digit), 81 x 9 = 729 outputs: the joint form of 729
independent logistic probes. The loss and every metric use only the (puzzle, cell)
entries selected by a boolean mask, so per-cell train/validation/test assignments
(as in Kniazev & Fijalkow's per-cell splits) are honoured exactly: the parameters of
cell c only ever see cell c's entries.

Training follows the E3 probe procedure (D55, D63): AdamW, BCE, the `probes.GRID`
x `probes.SEEDS` sweep, early stopping on the validation Brier, at least
`min_steps` optimizer steps, selection by `probes.select`. Labels come from
`labels.candidate_mask`; thresholds from `e3metrics.THRESHOLD`.
"""

import copy

import numpy as np
import torch

from ncm_sudoku.e3metrics import THRESHOLD
from ncm_sudoku.labels import candidate_mask
from ncm_sudoku.probes import GRID, SEEDS, _ceil_div, select


def candidate_targets(grids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(n, 81) digit grids (0 = empty) -> (mask (n, 81, 9) float32, empty (n, 81) bool)."""
    grids = np.asarray(grids)
    mask = np.stack([candidate_mask(g) for g in grids]).astype(np.float32)
    return mask, grids == 0


def grids_from_strings(puzzles) -> np.ndarray:
    """81-character puzzle strings ('0' or '.' = empty) -> (n, 81) int8."""
    out = np.zeros((len(puzzles), 81), dtype=np.int8)
    for i, p in enumerate(puzzles):
        if len(p) != 81:
            raise ValueError(f"puzzle {i} has length {len(p)}")
        out[i] = [int(ch) if ch in "123456789" else 0 for ch in p]
    return out


def validation_carve(train: np.ndarray, share: float = 0.125, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Splits each cell's training entries (bool (n, 81)) into fit and validation
    entries: a seeded permutation per cell, the first ceil(share * n_c) go to validation."""
    rng = np.random.default_rng(seed)
    fit, val = train.copy(), np.zeros_like(train)
    for c in range(train.shape[1]):
        rows = np.flatnonzero(train[:, c])
        if len(rows) == 0:
            continue
        perm = rng.permutation(rows)
        k = int(np.ceil(share * len(rows)))
        val[perm[:k], c] = True
        fit[perm[:k], c] = False
    return fit, val


def masked_brier(pred: np.ndarray, y: np.ndarray, sel: np.ndarray) -> float:
    """Mean 9-bit Brier per selected cell, averaged per puzzle, then over puzzles with
    at least one selected cell (the §8.3 order: cells within a puzzle, then puzzles)."""
    cell = ((np.asarray(pred, np.float64) - np.asarray(y, np.float64)) ** 2).mean(axis=2)  # (n, 81)
    counts = sel.sum(axis=1)
    keep = counts > 0
    return float(((cell * sel).sum(axis=1)[keep] / counts[keep]).mean())


class UntiedLinear(torch.nn.Module):
    def __init__(self, in_dim: int, n_cells: int = 81, n_digits: int = 9):
        super().__init__()
        self.shape = (n_cells, n_digits)
        self.linear = torch.nn.Linear(in_dim, n_cells * n_digits)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(self.linear(x)).view(x.shape[0], *self.shape)


def _predict(model: torch.nn.Module, X: torch.Tensor) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        return model(X).numpy()


def train_untied(
    X: torch.Tensor,
    Y: torch.Tensor,
    fit: np.ndarray,
    val: np.ndarray,
    wd: float,
    lr: float,
    seed: int,
    epochs: int = 50,
    batch: int = 256,
    min_steps: int = 2000,
) -> tuple[torch.nn.Module, float, dict]:
    """One (wd, lr, seed) fit. X (n, d), Y (n, 81, 9); `fit`/`val` bool (n, 81) select
    the training and validation entries. Rows without a fit entry are dropped from the
    minibatches. Keeps the epoch with the best validation Brier."""
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(seed)
    X, Y = X.float(), Y.float()
    rows = np.flatnonzero(fit.any(axis=1))
    Xf, Yf = X[rows], Y[rows]
    Mf = torch.from_numpy(fit[rows]).float().unsqueeze(-1).expand(-1, -1, Y.shape[2])
    n = len(rows)
    steps_per_epoch = _ceil_div(n, batch)
    epochs_run = max(epochs, _ceil_div(min_steps, steps_per_epoch))

    model = UntiedLinear(X.shape[1], *Y.shape[1:])
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd)
    gen = torch.Generator().manual_seed(seed)
    yv = Y.numpy()
    best_brier, best_state, best_epoch = float("inf"), copy.deepcopy(model.state_dict()), -1
    for epoch in range(epochs_run):
        model.train()
        perm = torch.randperm(n, generator=gen)
        for i in range(0, n, batch):
            idx = perm[i : i + batch]
            opt.zero_grad()
            m = Mf[idx]
            loss = (torch.nn.functional.binary_cross_entropy(model(Xf[idx]), Yf[idx], reduction="none") * m).sum() / m.sum()
            loss.backward()
            opt.step()
        brier = masked_brier(_predict(model, X), yv, val)
        if brier < best_brier:
            best_brier, best_state, best_epoch = brier, copy.deepcopy(model.state_dict()), epoch
    model.load_state_dict(best_state)
    model.eval()
    info = {"best_epoch": best_epoch, "epochs_run": epochs_run, "n_steps": epochs_run * steps_per_epoch,
            "hit_cap": best_epoch == epochs_run - 1, "n_params": sum(p.numel() for p in model.parameters())}
    return model, best_brier, info


def fit_selected_untied(X: torch.Tensor, Y: torch.Tensor, fit: np.ndarray, val: np.ndarray, **kw) -> dict:
    """GRID x SEEDS sweep, selection on the mean validation Brier (`probes.select`);
    returns the selected config, the seed-averaged predictions on every row, the
    per-seed predictions and the training budget of every fit."""
    results: dict = {cfg: [] for cfg in GRID}
    models, budget = {}, {}
    for wd, lr in GRID:
        for seed in SEEDS:
            model, brier, info = train_untied(X, Y, fit, val, wd, lr, seed, **kw)
            results[(wd, lr)].append(brier)
            models[(wd, lr, seed)] = model
            budget[(wd, lr, seed)] = info
    cfg = select(results)
    seed_preds = [_predict(models[(*cfg, s)], X.float()) for s in SEEDS]
    return {"config": cfg, "val_brier_mean": float(np.mean(results[cfg])),
            "preds": np.mean(seed_preds, axis=0), "seed_preds": seed_preds, "budget": budget}


def exact_match_per_cell(pred: np.ndarray, y: np.ndarray, sel: np.ndarray) -> np.ndarray:
    """(81,) share of selected entries whose thresholded 9-bit prediction equals the
    label exactly; NaN for a cell without selected entries."""
    hit = ((np.asarray(pred) >= THRESHOLD) == (np.asarray(y) >= THRESHOLD)).all(axis=2)  # (n, 81)
    counts = sel.sum(axis=0)
    with np.errstate(invalid="ignore"):
        return np.where(counts > 0, (hit & sel).sum(axis=0) / np.maximum(counts, 1), np.nan)
