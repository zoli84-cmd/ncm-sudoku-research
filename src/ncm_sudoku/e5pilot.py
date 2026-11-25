"""E5 pilot probes on the counterfactual pairs (D100; non-confirmatory).

Rows of every array are the pair members stacked as [a_0..a_{n-1}, b_0..b_{n-1}], so
row i and row i + n are the two members of pair i. Representations: "z6" and
"z6_teacher" (Z<=6 cell states), "P<k>" (prefix cell positions of the level-7 pass,
layer k), "B<k>" (closing prefix BOS, layer k).

The within-pair AUC (`w_auc`) is the primary pilot quantity: over (cell, digit) bits
with the cell empty in both members and the digit a candidate in exactly one, the
share of bits where the candidate member gets the higher probability (ties 0.5).
"""

import json
from pathlib import Path

import numpy as np
import torch

from ncm_sudoku.e3controls import fit_cells, permute_labels, permuted_control, roc_auc, summarize_fit
from ncm_sudoku.e3metrics import THRESHOLD
from ncm_sudoku.e5probes import candidate_targets, fit_selected_untied
from ncm_sudoku.wholelayer import cell_pca_features

LEVELS_1_6 = 1 + 2 + 4 + 6 + 9 + 13  # code count of levels 1..6
PCA_K = 256


def load_subset(root: Path, subset: str) -> dict:
    """Labels and metadata of one pair subset (members stacked a then b)."""
    pairs = root / "runs" / "e5" / "pairs" / subset
    acts = root / "runs" / "e5" / "acts" / subset
    a, b = np.load(pairs / "a.npy"), np.load(pairs / "b.npy")
    puzzles = np.concatenate([a, b]).astype(np.int8)
    mask, empty = candidate_targets(puzzles)
    ca, cb = np.load(acts / "a" / "codes.npy"), np.load(acts / "b" / "codes.npy")
    return {"subset": subset, "n_pairs": len(a), "puzzles": puzzles, "mask": mask, "empty": empty,
            "codes_same_1_6": (ca[:, :LEVELS_1_6] == cb[:, :LEVELS_1_6]).all(axis=1),
            "solved": np.concatenate([np.load(acts / "a" / "solved.npy"), np.load(acts / "b" / "solved.npy")]),
            "acts": acts}


def representation(d: dict, name: str) -> np.ndarray:
    def load(member, file):
        return np.load(d["acts"] / member / f"{file}.npy", mmap_mode="r")

    if name in ("z6", "z6_teacher"):
        parts = [load(m, name) for m in "ab"]
    elif name[0] in "PB" and name[1:].isdigit():
        k = int(name[1:])
        parts = [load(m, "prefix_cells" if name[0] == "P" else "prefix_bos")[:, k] for m in "ab"]
    else:
        raise ValueError(f"unknown representation {name!r}")
    return np.concatenate([np.asarray(p, dtype=np.float32) for p in parts])


def scatter(rows: np.ndarray, empty: np.ndarray) -> np.ndarray:
    """Row predictions (row-major over np.nonzero(empty)) -> (n, 81, 9), NaN on given cells."""
    out = np.full((*empty.shape, 9), np.nan, dtype=np.float64)
    out[empty] = rows
    return out


def w_auc(pred: np.ndarray, d: dict) -> dict:
    """Within-pair AUC overall, per pair (NaN for a pair without a discordant bit), and
    split by whether the pair's level 1-6 codes are identical."""
    n = d["n_pairs"]
    pa, pb, ya, yb = pred[:n], pred[n:], d["mask"][:n] > 0.5, d["mask"][n:] > 0.5
    both = (d["empty"][:n] & d["empty"][n:])[..., None]
    disc = both & (ya != yb)  # (n, 81, 9)
    p_cand = np.where(ya, pa, pb)
    p_non = np.where(ya, pb, pa)
    score = np.where(p_cand > p_non, 1.0, np.where(p_cand == p_non, 0.5, 0.0))
    num = (score * disc).sum(axis=(1, 2))
    cnt = disc.sum(axis=(1, 2))
    with np.errstate(invalid="ignore"):
        per_pair = num / cnt
    same = d["codes_same_1_6"]

    def pooled(sel):
        return float(num[sel].sum() / cnt[sel].sum()) if cnt[sel].sum() else None

    return {"overall": pooled(np.ones(n, bool)), "codes_same": pooled(same), "codes_differ": pooled(~same),
            "n_bits": int(cnt.sum()), "per_pair": per_pair.tolist()}


def cell_metrics(pred: np.ndarray, d: dict) -> dict:
    e = d["empty"]
    p, y = pred[e], d["mask"][e]
    return {"exact_match": float(((p >= THRESHOLD) == (y >= THRESHOLD)).all(axis=1).mean()),
            "roc_auc": roc_auc(p, y)}


def _sets(train: dict, val: dict) -> tuple[dict, dict]:
    return ({"mask": train["mask"], "empty": train["empty"]}, {"mask": val["mask"], "empty": val["empty"]})


def run_cell(rep_tr, rep_va, train, val, readout: str, control: str | None = None, **kw) -> dict:
    """Cell-level probe: readout "shared" (state || cell one-hot, D55) or "whole"
    (D66 peer PCA || state); control None, "permuted" or "labels"."""
    info = None
    if readout == "whole":
        _, info, rep_tr, rep_va, _ = cell_pca_features(rep_tr, rep_va, train["empty"], val["empty"], PCA_K)
    elif readout != "shared":
        raise ValueError(readout)
    tr, va = _sets(train, val)
    if control is None:
        fit = fit_cells(rep_tr, rep_va, tr, va, "linear", **kw)
    elif control == "permuted":
        fit = permuted_control(rep_tr, rep_va, tr, va, **kw)
    elif control == "labels":
        fit = fit_cells(rep_tr, rep_va, tr, va, "linear", mask_tr=permute_labels(tr["mask"], tr["empty"]), **kw)
    else:
        raise ValueError(control)
    pred = scatter(fit["preds"], val["empty"])
    return {"summary": summarize_fit(fit), "pca": info, "w_auc": w_auc(pred, val),
            "metrics": cell_metrics(pred, val), "pred": pred}


def run_global(rep_tr, rep_va, train, val, **kw) -> dict:
    """Global (BOS) probe with the D95 untied head: fit on the PROBE-TRAIN empty cells,
    select and score on the PROBE-VAL empty cells."""
    X = torch.from_numpy(np.concatenate([rep_tr, rep_va]).astype(np.float32))
    Y = torch.from_numpy(np.concatenate([train["mask"], val["mask"]]).astype(np.float32))
    n_tr = len(rep_tr)
    fit = np.zeros((len(X), 81), bool)
    sel = np.zeros_like(fit)
    fit[:n_tr] = train["empty"]
    sel[n_tr:] = val["empty"]
    res = fit_selected_untied(X, Y, fit, sel, **kw)
    pred = res["preds"][n_tr:].astype(np.float64)
    pred[~val["empty"]] = np.nan
    budget = {f"{wd}_{lr}_{s}": v for (wd, lr, s), v in res["budget"].items()}
    return {"summary": {"config": list(res["config"]), "val_brier_mean": res["val_brier_mean"], "budget": budget},
            "w_auc": w_auc(pred, val), "metrics": cell_metrics(pred, val), "pred": pred}


def save(result: dict, out_json: Path, out_npy: Path) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_npy.parent.mkdir(parents=True, exist_ok=True)
    np.save(out_npy, result["pred"].astype(np.float32))
    body = {k: v for k, v in result.items() if k != "pred"}
    out_json.write_text(json.dumps(body, indent=1) + "\n", encoding="utf-8", newline="\n")


# --- D101(6): converged L-BFGS reference and online MDL on the shared own-position readout ---

LBFGS_CS = (0.01, 0.1, 1.0, 10.0, 100.0)
MDL_BLOCKS = (10, 20, 40, 80, 160, 320, 640, 1280, 2000)  # cumulative PROBE-TRAIN puzzles


def standardized_rows(rep, empty, mean=None, std=None):
    """Own-position rows (state standardized with PROBE-TRAIN statistics || cell one-hot),
    row-major over np.nonzero(empty); returns (X, puzzle_idx, mean, std)."""
    pz, pos = np.nonzero(empty)
    state = np.asarray(rep, np.float64)[pz, pos]
    if mean is None:
        mean, std = state.mean(axis=0), state.std(axis=0)
        std = np.where(std > 0, std, 1.0)
    X = np.concatenate([(state - mean) / std, np.eye(81)[pos]], axis=1)
    return torch.from_numpy(X), pz, mean, std


def fit_lbfgs(X: torch.Tensor, Y: torch.Tensor, C: float, max_iter: int = 1000, tol: float = 1e-7):
    """L2 logistic regression, sklearn objective scaled by 1/n:
    mean BCE + ||W||^2 / (2 C n), bias unpenalized; full-batch L-BFGS in float64.
    Returns (W, b, n_iter, converged)."""
    torch.manual_seed(0)
    n, d = X.shape
    W = torch.zeros(d, Y.shape[1], dtype=torch.float64, requires_grad=True)
    b = torch.zeros(Y.shape[1], dtype=torch.float64, requires_grad=True)
    opt = torch.optim.LBFGS([W, b], lr=1.0, max_iter=max_iter, tolerance_grad=tol, tolerance_change=1e-12,
                            history_size=50, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = torch.nn.functional.binary_cross_entropy_with_logits(X @ W + b, Y) * Y.shape[1]
        loss = loss + (W ** 2).sum() / (2 * C * n)
        loss.backward()
        return loss

    opt.step(closure)
    n_iter = opt.state[opt._params[0]]["n_iter"]
    with torch.no_grad():
        grad = torch.cat([W.grad.flatten(), b.grad])
    return W.detach(), b.detach(), int(n_iter), bool(grad.abs().max() <= tol * 10 or n_iter < max_iter)


def run_lbfgs(rep_tr, rep_va, train, val, Cs=LBFGS_CS) -> dict:
    Xtr, _, mean, std = standardized_rows(rep_tr, train["empty"])
    Xva, pz_va, _, _ = standardized_rows(rep_va, val["empty"], mean, std)
    Ytr = torch.from_numpy(train["mask"][train["empty"]].astype(np.float64))
    yva = val["mask"][val["empty"]]
    grid, best = [], None
    for C in Cs:
        W, b, n_iter, conv = fit_lbfgs(Xtr, Ytr, C)
        p = torch.sigmoid(Xva @ W + b).numpy()
        brier = float(np.nanmean([((p[pz_va == i] - yva[pz_va == i]) ** 2).mean() for i in np.unique(pz_va)]))
        grid.append({"C": C, "val_brier": brier, "n_iter": n_iter, "converged": conv})
        if best is None or brier < best[0]:
            best = (brier, C, p)
    pred = scatter(best[2], val["empty"])
    return {"summary": {"config": ["lbfgs", best[1]], "val_brier_mean": best[0], "grid": grid},
            "w_auc": w_auc(pred, val), "metrics": cell_metrics(pred, val), "pred": pred}


def online_mdl(rep_tr, train, C: float = 1.0, blocks=MDL_BLOCKS) -> dict:
    """Online code length (Voita & Titov 2020) of the PROBE-TRAIN candidate bits over
    cumulative puzzle blocks: the first block is sent with the uniform code (1 bit per
    label bit); each later block with -log2 p of an L-BFGS logistic probe fitted on all
    earlier blocks (inputs standardized on the earlier blocks)."""
    empty, mask = train["empty"], train["mask"]
    bits = []
    first_bits = float(mask[: blocks[0]][empty[: blocks[0]]].size)
    total = first_bits
    for lo, hi in zip(blocks[:-1], blocks[1:]):
        Xa, _, mean, std = standardized_rows(rep_tr[:lo], empty[:lo])
        Ya = torch.from_numpy(mask[:lo][empty[:lo]].astype(np.float64))
        W, b, _, _ = fit_lbfgs(Xa, Ya, C)
        Xb, _, _, _ = standardized_rows(rep_tr[lo:hi], empty[lo:hi], mean, std)
        yb = mask[lo:hi][empty[lo:hi]]
        p = torch.sigmoid(Xb @ W + b).numpy().clip(1e-12, 1 - 1e-12)
        block_bits = float(-(yb * np.log2(p) + (1 - yb) * np.log2(1 - p)).sum())
        bits.append({"from": int(lo), "to": int(hi), "bits": block_bits, "labels": int(yb.size)})
        total += block_bits
    uniform = float(mask[: blocks[-1]][empty[: blocks[-1]]].size)
    return {"C": C, "blocks": list(blocks), "first_block_uniform_bits": first_bits, "block_bits": bits,
            "online_codelength_bits": total, "uniform_codelength_bits": uniform, "compression": uniform / total}
