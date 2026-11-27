"""E5 activation-exchange causal pilot (D102): probe heads, subspaces and patch steps.

Heads: the pilot shared own-position heads (D55 linear, state || cell one-hot) are
refitted at their selected pilot configuration with `probes.train_probe` for each
of `probes.SEEDS` (deterministic per configuration and seed) and checked against the
saved pilot predictions before they are used.
"""

import json
from pathlib import Path

import numpy as np
import torch

from ncm_sudoku.e5pilot import load_subset, representation, scatter
from ncm_sudoku.probes import SEEDS, build_inputs, train_probe

STATE_DIM = 512


def compare_predictions(pred: np.ndarray, saved: np.ndarray) -> dict:
    """Protocol §9.1 reproduction check of a refitted head against the saved pilot
    predictions: equal shape, equal NaN pattern (given cells), every evaluable element
    finite on both sides, and exact equality on the evaluable elements."""
    out = {"shape_equal": pred.shape == saved.shape, "nan_pattern_equal": False, "finite": False,
           "n_unequal": None, "max_abs_diff": None}
    if out["shape_equal"]:
        nan_p, nan_s = np.isnan(pred), np.isnan(saved)
        out["nan_pattern_equal"] = bool(np.array_equal(nan_p, nan_s))
        ev = ~nan_s
        out["finite"] = bool(np.isfinite(pred[ev]).all() and np.isfinite(saved[ev]).all())
        if out["nan_pattern_equal"] and out["finite"]:
            out["n_unequal"] = int((pred[ev] != saved[ev]).sum())
            out["max_abs_diff"] = float(np.abs(pred[ev] - saved[ev]).max(initial=0.0))
    out["passed"] = bool(out["shape_equal"] and out["nan_pattern_equal"] and out["finite"] and out["n_unequal"] == 0)
    return out


def refit_head(root: Path, rep: str) -> dict:
    """Refits the pilot head `<rep>__shared__none` and compares its seed-averaged
    PROBE-VAL predictions with the saved pilot predictions (`compare_predictions`)."""
    pilot = json.loads((root / "experiments" / "e5" / "pilot" / f"{rep}__shared__none.json").read_text())
    wd, lr = pilot["summary"]["config"]
    train, val = load_subset(root, "probe_train"), load_subset(root, "probe_val")
    r_tr, r_va = representation(train, rep), representation(val, rep)
    Xtr, _, _ = build_inputs(r_tr, train["empty"])
    Ytr = torch.from_numpy(train["mask"][train["empty"]].astype(np.float32))
    Xva, pz_va, _ = build_inputs(r_va, val["empty"])
    Yva = torch.from_numpy(val["mask"][val["empty"]].astype(np.float32))
    states, preds = [], []
    for seed in SEEDS:
        model, _, _ = train_probe(Xtr, Ytr, Xva, Yva, pz_va.numpy(), len(val["empty"]), "linear", wd, lr, seed)
        with torch.no_grad():
            preds.append(model(Xva.float()).numpy())
        states.append({k: v.detach().cpu().clone() for k, v in model.state_dict().items()})
    pred = scatter(np.mean(preds, axis=0), val["empty"])
    saved = np.load(root / "runs" / "e5" / "pilot" / f"{rep}__shared__none.npy")
    check = compare_predictions(pred, saved)
    return {"rep": rep, "config": [wd, lr], "state_dicts": states, "max_abs_diff_vs_pilot": check["max_abs_diff"],
            "reproduction": check}


def state_weights(state_dicts: list[dict]) -> np.ndarray:
    """Seed-averaged state part of the head weights, (9, 512) float64."""
    return np.mean([sd["0.weight"].double().numpy()[:, :STATE_DIM] for sd in state_dicts], axis=0)


def orthonormal_rows(W: np.ndarray, rtol: float = 1e-8) -> tuple[np.ndarray, np.ndarray]:
    """Orthonormal basis Q (d, r) of the row space of W (r, d) via SVD, with a relative
    rank check; returns (Q, singular values)."""
    _, s, vt = np.linalg.svd(W, full_matrices=False)
    if s[-1] <= rtol * s[0]:
        raise ValueError(f"row space rank deficient: singular values {s}")
    return vt.T.copy(), s


def random_basis(seed: int, d: int = STATE_DIM, r: int = 9) -> np.ndarray:
    """Haar-random orthonormal (d, r): float64 QR of an i.i.d. Gaussian matrix with a positive R diagonal."""
    g = np.random.default_rng(seed).standard_normal((d, r))
    q, rr = np.linalg.qr(g)
    return q * np.sign(np.diag(rr))


# --- D102(2)-(4): patch steps ---------------------------------------------------------

DERANGEMENT = np.roll(np.arange(9), 1)  # fixed digit derangement d -> d + 1 (mod 9)


def project_step(delta: np.ndarray, Q: np.ndarray) -> np.ndarray:
    """(n, d) float64: ((x_d - x_r) Q) Q^T."""
    return (delta @ Q) @ Q.T


def norm_matched(raw: np.ndarray, target_norm: np.ndarray, tol: float = 1e-12) -> tuple[np.ndarray, np.ndarray]:
    """Rescales each row of `raw` to `target_norm`; a zero target gives an exact zero
    step; a positive target with a numerically zero raw step is an error. Returns
    (step, scale)."""
    n = np.linalg.norm(raw, axis=1)
    scale = np.zeros_like(n)
    pos = target_norm > 0
    if np.any(pos & (n <= tol * np.maximum(target_norm, 1.0))):
        raise ValueError("control projection numerically zero for a positive target norm")
    scale[pos] = target_norm[pos] / n[pos]
    return raw * scale[:, None], scale


def shuffled_raw(delta: np.ndarray, W: np.ndarray, perm: np.ndarray = DERANGEMENT) -> np.ndarray:
    """W^+ Pi (W delta): the state step whose head-logit change is the digit-permuted
    logit change of the full difference (W: (9, d) seed-averaged state weights)."""
    logits = delta @ W.T  # (n, 9)
    return logits[:, perm] @ np.linalg.pinv(W).T


def high_variance_basis(diffs: np.ndarray, Q: np.ndarray, r: int = 9) -> np.ndarray:
    """First r principal directions (uncentred SVD) of `diffs` (n, d) after projecting
    them off Q; orthonormal (d, r), orthogonal to Q."""
    off = diffs - (diffs @ Q) @ Q.T
    _, _, vt = np.linalg.svd(off, full_matrices=False)
    B = vt[:r].T
    return B - Q @ (Q.T @ B)


# --- D102(2), (4)(f): hooked level-7 call ------------------------------------------------

def isolation_check(out: torch.Tensor, new: torch.Tensor, cells, rows: np.ndarray, values: np.ndarray) -> tuple[bool, bool]:
    """Protocol §6 patch checks for one hooked output (B, T, d): (written_ok,
    untouched_ok). Written: every targeted cell row of `new` equals the expected float32
    row in `values` bit for bit. Untouched: every other row of the sequence (query, BOS,
    separator, clue and non-targeted cell rows) is bit-identical to `out`."""
    rows_t = torch.as_tensor(rows, dtype=torch.bool)
    targeted = torch.zeros(new.shape[:2], dtype=torch.bool)
    targeted[:, torch.as_tensor(cells)] = rows_t
    written = bool(torch.equal(new[:, torch.as_tensor(cells)][rows_t],
                               torch.as_tensor(values, dtype=new.dtype)[rows_t]))
    untouched = bool(torch.equal(new[~targeted], out[~targeted]))
    return written, untouched


class Level7Hooks:
    """Forward hooks for one `intervene.level_logits(..., level=7)` call: optionally
    replaces prefix cell rows at the output of blocks[1] and captures the outputs of
    blocks[1], blocks[3] and blocks[7]. Counts hook applications; after a patch,
    `written_ok` and `untouched_ok` hold the `isolation_check` flags."""

    def __init__(self, net, prefix_cells: np.ndarray):
        self.net, self.cells = net, torch.as_tensor(prefix_cells)
        self.patch = None  # (rows (B, 81) bool, values (B, 81, d) float32) or None
        self.captured, self.applied, self.written_ok, self.untouched_ok = {}, 0, None, None

    def _patch(self, _m, _a, out):
        self.applied += 1
        self.captured["L2_before"] = out.detach().clone()
        if self.patch is None:
            return out
        rows, values = self.patch
        new = out.clone()
        cells = new[:, self.cells]  # (B, 81, d)
        mask = torch.as_tensor(rows)[..., None]
        cells = torch.where(mask, torch.as_tensor(values, dtype=new.dtype), cells)
        new[:, self.cells] = cells
        self.written_ok, self.untouched_ok = isolation_check(out, new, self.cells, rows, values)
        self.captured["L2_after"] = new.detach().clone()
        return new

    def _capture(self, name):
        def hook(_m, _a, out):
            self.captured[name] = out.detach().clone()
        return hook

    def __enter__(self):
        b = self.net.transformer.blocks
        self.handles = [b[1].register_forward_hook(self._patch),
                        b[3].register_forward_hook(self._capture("L4")),
                        b[7].register_forward_hook(self._capture("L8"))]
        return self

    def __exit__(self, *exc):
        for h in self.handles:
            h.remove()


def head_logits(states: np.ndarray, state_dicts: list[dict]) -> np.ndarray:
    """Seed-averaged pre-sigmoid logits (n, 81, 9) float64 of a shared head on cell
    states (n, 81, d): mean over seeds of W [state || one-hot(cell)] + b."""
    states = np.asarray(states, np.float64)
    out = 0.0
    for sd in state_dicts:
        W = sd["0.weight"].double().numpy()
        b = sd["0.bias"].double().numpy()
        out = out + states @ W[:, :STATE_DIM].T + W[:, STATE_DIM:].T[None] + b
    return out / len(state_dicts)


def code_probs(logits: torch.Tensor) -> np.ndarray:
    """T = 1 softmax over the 16 codes, float64 (B, 18, 16)."""
    return torch.softmax(logits.double(), dim=-1).numpy()


def tv(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Total variation per recipient, averaged over the query positions: (B,)."""
    return 0.5 * np.abs(p - q).sum(axis=-1).mean(axis=-1)
