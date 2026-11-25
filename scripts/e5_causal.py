"""E5 causal pilot, primary one-pass evaluation (D102; non-confirmatory).

Usage: uv run --locked python scripts/e5_causal.py [--limit N] [--draws 20] [--batch 50] [--force]

For every PROBE-VAL pair and both orders (recipient a/donor b, then b/a), with the
recipient's clean level 1-6 codes fixed, runs `intervene.level_logits(..., level=7)`
with `e5causal.Level7Hooks` patching the layer-2 prefix rows (output of blocks[1]) at
cells empty in both members. Conditions: Q (P2 head row space), norm-matched random
subspaces (`--draws`), the high-variance control, the shuffled-digit control, the
both-empty full swap, the full donor input, and the self-donor identity check (must
equal the clean logits bit for bit, or the run stops). Donor activations are captured
online, fp32, in the same call layout.

Outcomes per recipient: directed TV movement towards the both-empty full swap
(T = 1 softmax over 16 codes, 18 level-7 queries), undirected TV, argmax changes,
P4/P8 seed-averaged logit shifts on discordant bits, flip rates, step norms and cosines.
Per-pair results (orders averaged) and pair-level bootstrap summaries go to
experiments/e5/causal/primary.json; per-recipient arrays to runs/e5/causal/primary.npz.
"""

import argparse
import json
import sys
import time

import numpy as np
import torch

from ncm_sudoku.e5causal import (
    Level7Hooks,
    code_probs,
    head_logits,
    high_variance_basis,
    norm_matched,
    orthonormal_rows,
    project_step,
    random_basis,
    shuffled_raw,
    state_weights,
    tv,
)
from ncm_sudoku.e5extract import PREFIX_CELLS
from ncm_sudoku.e5pilot import load_subset
from ncm_sudoku.g0 import code_state, environment_record
from ncm_sudoku.intervene import level_logits
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.runner import puzzle_tensor

OUT = ROOT / "experiments" / "e5" / "causal" / "primary.json"
RAW = ROOT / "runs" / "e5" / "causal" / "primary.npz"
HEADS = ROOT / "runs" / "e5" / "causal" / "heads"
LEVELS_1_6 = 35
N_BOOT, BOOT_SEED = 10000, 0


def bootstrap(x: np.ndarray) -> dict:
    x = np.asarray(x, np.float64)
    x = x[np.isfinite(x)]
    rng = np.random.default_rng(BOOT_SEED)
    means = rng.choice(x, size=(N_BOOT, len(x)), replace=True).mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return {"mean": float(x.mean()), "ci95": [float(lo), float(hi)], "n": int(len(x)),
            "degenerate": bool(hi - lo == 0)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--draws", type=int, default=20)
    ap.add_argument("--batch", type=int, default=50)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    out = OUT if args.limit is None else OUT.with_name(f"primary_first{args.limit}.json")
    if out.exists() and not args.force:
        sys.exit(f"{out.relative_to(ROOT)} exists; use --force")
    t_start = time.perf_counter()
    m = load_model(ROOT / "checkpoints" / "sudoku" / "hard")
    heads = {k: torch.load(HEADS / f"{k}.pt", weights_only=True) for k in ("P2", "P4", "P8")}
    W = state_weights(heads["P2"])
    Q, _ = orthonormal_rows(W)
    R = [random_basis(1000 + j) for j in range(args.draws)]

    tr = load_subset(ROOT, "probe_train")
    nt = tr["n_pairs"]
    ta = np.load(tr["acts"] / "a" / "prefix_cells.npy", mmap_mode="r")[:, 2].astype(np.float64)
    tb = np.load(tr["acts"] / "b" / "prefix_cells.npy", mmap_mode="r")[:, 2].astype(np.float64)
    be_tr = tr["empty"][:nt] & tr["empty"][nt:]
    B = high_variance_basis((tb - ta)[be_tr], Q)

    val = load_subset(ROOT, "probe_val")
    n = val["n_pairs"] if args.limit is None else args.limit
    puzzles = val["puzzles"]
    codes = np.concatenate([np.load(val["acts"] / mm / "codes.npy") for mm in "ab"]).astype(np.int64)
    N = val["n_pairs"]
    mask, empty = val["mask"] > 0.5, val["empty"]
    cond_names = ["Q"] + [f"rand{j}" for j in range(args.draws)] + ["hv", "shuf", "full_be", "full_input"]
    res = {k: [] for k in ("directed", "undirected", "argmax_changes", "shift4", "shift8", "flip4", "flip8")}
    diag = {"target_norm": [], "cos_Q": [], "cos_shuf": [], "applied_ok": True, "query_isolation_ok": True,
            "self_donor_max_abs": 0.0, "tv_clean_full": []}
    rows_meta = []

    def call(prefix, cds, patch=None):
        with Level7Hooks(m.net, PREFIX_CELLS) as h:
            h.patch = patch
            logits = level_logits(m, prefix, torch.as_tensor(cds), 7)
            if h.applied != 1:
                diag["applied_ok"] = False
            if patch is not None and not h.query_unchanged:
                diag["query_isolation_ok"] = False
            cells = torch.as_tensor(PREFIX_CELLS)
            return logits, {k: h.captured[k][:, cells].numpy() for k in ("L2_before", "L4", "L8")}

    for order in ("ab", "ba"):
        for s in range(0, n, args.batch):
            idx = np.arange(s, min(s + args.batch, n))
            r_rows = idx if order == "ab" else idx + N
            d_rows = idx + N if order == "ab" else idx
            pr, pd = puzzle_tensor(puzzles[r_rows]), puzzle_tensor(puzzles[d_rows])
            cr, cd = codes[r_rows][:, :LEVELS_1_6], codes[d_rows][:, :LEVELS_1_6]
            lg_c, cap_r = call(pr, cr)
            _, cap_d = call(pd, cd)
            xr, xd = cap_r["L2_before"].astype(np.float64), cap_d["L2_before"].astype(np.float64)
            both = empty[r_rows] & empty[d_rows]
            disc = both[..., None] & (mask[r_rows] != mask[d_rows])
            yd = mask[d_rows]
            p_clean = code_probs(lg_c)
            z_clean = {k: head_logits(cap_r[k], heads["P" + k[1]]) for k in ("L4", "L8")}

            delta = (xd - xr)[both]
            stepQ = project_step(delta, Q)
            target = np.linalg.norm(stepQ, axis=1)
            dn = np.linalg.norm(delta, axis=1)
            diag["target_norm"].append(float(target.mean()))
            diag["cos_Q"].append(float(np.mean((stepQ * delta).sum(1) / np.maximum(target * dn, 1e-30))))
            steps = {"Q": stepQ, "hv": norm_matched(project_step(delta, B), target)[0]}
            sh = norm_matched(shuffled_raw(delta, W), target)[0]
            steps["shuf"] = sh
            diag["cos_shuf"].append(float(np.mean((sh * delta).sum(1) / np.maximum(np.linalg.norm(sh, axis=1) * dn, 1e-30))))
            for j, Rj in enumerate(R):
                steps[f"rand{j}"] = norm_matched(project_step(delta, Rj), target)[0]

            def values_for(step=None, full=False):
                v = xr.copy()
                v[both] = xd[both] if full else xr[both] + step
                return v.astype(np.float32)

            # identity: self-donor writes the recipient's own values back
            lg_self, _ = call(pr, cr, (both, xr.astype(np.float32)))
            diag["self_donor_max_abs"] = max(diag["self_donor_max_abs"], float((lg_self - lg_c).abs().max()))
            if not torch.equal(lg_self, lg_c):
                sys.exit("self-donor identity check failed")
            lg_full, cap_full = call(pr, cr, (both, values_for(full=True)))
            p_full = code_probs(lg_full)
            diag["tv_clean_full"] += tv(p_clean, p_full).tolist()
            per = {}
            for name in cond_names:
                if name == "full_be":
                    lg, cap = lg_full, cap_full
                elif name == "full_input":
                    lg, cap = call(pd, cr)
                else:
                    lg, cap = call(pr, cr, (both, values_for(steps[name])))
                p = code_probs(lg)
                rec = {"directed": tv(p_clean, p_full) - tv(p, p_full), "undirected": tv(p, p_clean),
                       "argmax_changes": (lg.argmax(-1) != lg_c.argmax(-1)).sum(-1).numpy().astype(float)}
                for k, key in (("L4", "4"), ("L8", "8")):
                    z = head_logits(cap[k], heads["P" + k[1]])
                    sgn = 2.0 * yd - 1.0
                    sh_ = (sgn * (z - z_clean[k]) * disc).sum((1, 2)) / np.maximum(disc.sum((1, 2)), 1)
                    flip = (((z >= 0) == yd) & ~((z_clean[k] >= 0) == yd) & disc).sum((1, 2)) / np.maximum(disc.sum((1, 2)), 1)
                    rec["shift" + key], rec["flip" + key] = sh_, flip
                per[name] = rec
            for key in res:
                res[key].append(np.stack([per[c][key] for c in cond_names], axis=1))
            rows_meta.append(np.stack([idx, np.full_like(idx, 0 if order == "ab" else 1)], axis=1))
            print(f"{order} {s + len(idx)}/{n} ({time.perf_counter() - t_start:.0f} s)", flush=True)

    arr = {k: np.concatenate(v) for k, v in res.items()}  # (2n, n_cond)
    meta = np.concatenate(rows_meta)
    RAW.parent.mkdir(parents=True, exist_ok=True)
    raw_path = RAW if args.limit is None else RAW.with_name(f"primary_first{args.limit}.npz")
    np.savez(raw_path, conditions=np.array(cond_names), meta=meta, **arr)

    def per_pair(a):
        out = np.zeros((n, a.shape[1]))
        for o in (0, 1):
            out += a[meta[:, 1] == o][np.argsort(meta[meta[:, 1] == o, 0])]
        return out / 2

    ci = {c: i for i, c in enumerate(cond_names)}
    rand = [ci[f"rand{j}"] for j in range(args.draws)]
    summary = {}
    for key in ("directed", "shift4", "shift8", "flip4", "flip8", "undirected", "argmax_changes"):
        pp = per_pair(arr[key])
        summary[key] = {
            "per_condition_mean": {c: float(pp[:, i].mean()) for c, i in ci.items()},
            "random_draw_spread": {"min": float(pp[:, rand].mean(0).min()), "max": float(pp[:, rand].mean(0).max()),
                                   "sd": float(pp[:, rand].mean(0).std())},
            "Q": bootstrap(pp[:, ci["Q"]]),
            "Q_minus_random_mean": bootstrap(pp[:, ci["Q"]] - pp[:, rand].mean(1)),
            "Q_minus_high_variance": bootstrap(pp[:, ci["Q"]] - pp[:, ci["hv"]]),
            "Q_minus_shuffled_digit": bootstrap(pp[:, ci["Q"]] - pp[:, ci["shuf"]]),
        }
    tvcf = np.array(diag.pop("tv_clean_full"))
    record = {
        "note": "E5 causal pilot (D102), primary one-pass level-7 evaluation with fixed Z<=6; non-confirmatory; "
                "bootstrap intervals are conditional on the drawn random bases",
        "date": time.strftime("%Y-%m-%d"), "n_pairs": int(n), "draws": args.draws, "batch": args.batch,
        "conditions": cond_names,
        "diagnostics": {**{k: (float(np.mean(v)) if isinstance(v, list) else v) for k, v in diag.items()},
                        "tv_clean_full": {"mean": float(tvcf.mean()), "median": float(np.median(tvcf)),
                                          "share_below_0.01": float((tvcf < 0.01).mean())}},
        "summary": summary, "seconds": round(time.perf_counter() - t_start, 1),
        "environment": environment_record(), "code_state": code_state(),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: {"Q": v["Q"], "Q-rand": v["Q_minus_random_mean"]["mean"], "Q-hv": v["Q_minus_high_variance"]["mean"],
                          "Q-shuf": v["Q_minus_shuffled_digit"]["mean"]} for k, v in summary.items() if k in ("directed", "shift4", "shift8")}, indent=1))
    print(json.dumps(record["diagnostics"]))


if __name__ == "__main__":
    main()
