"""E5 TEST causal batch with every claim-B check of protocol §6 (§5.2 conditions).

`evaluate_batch` runs one batch of recipients r with donors d through the pilot's
level-7 activation exchange (`scripts/e5_causal.py`), in the same call order,
operation order and dtypes, so its per-recipient outcomes equal the pilot's bit for
bit: Delta = x_d - x_r in float64 from fp32 captures at the output of blocks[1];
the value written at a both-empty cell is `(x_r64 + step).astype(np.float32)` (x_d
for the both-empty full swap, x_r elsewhere); directed = tv(p_clean, p_full) -
tv(p_cond, p_full) with p_clean from the capture-call logits.

Call order per batch (fixed): plain clean `level_logits` (no hook anywhere on the
model); capture-only call on the recipient (its logits must equal the plain call bit
for bit); capture-only call on the donor with its own codes; self-donor at the
both-empty cells (d := r through the donor indexing path); self-donor at all 91
prefix positions; the both-empty full swap; every condition in `CONDITIONS` order
(`full_be` reuses the full swap, `full_input` is `level_logits(m, pd, cr, 7)` under a
capture-only hook).

A failed check never stops the batch and never drops a pair: it appends its reason
(each at most once per batch, first-seen order) to `invalid_reasons`, which makes
claim B invalid. A zero-rule failure (`norm_matched` raising) gives that cell a zero
step. A non-finite logits, probability, step or outcome array raises
`e5test.NonFiniteError` (protocol §6: both claims invalid). Codes that do not cover
exactly the 35 codes of levels 1-6 are a programming error (`ValueError`).
"""

import numpy as np
import torch

from ncm_sudoku.e5causal import (
    Level7Hooks,
    code_probs,
    head_logits,
    norm_matched,
    project_step,
    shuffled_raw,
    tv,
)
from ncm_sudoku.e5extract import PREFIX_CELLS
from ncm_sudoku.e5test import check_finite
from ncm_sudoku.intervene import level_logits

LEVEL = 7
LEVELS_1_6 = 35
N_DRAWS = 20
PREFIX_LEN = 91  # [BOS] + 89 row tokens + [BOS]
CONDITIONS = ["Q"] + [f"rand{j}" for j in range(N_DRAWS)] + ["hv", "shuf", "full_be", "full_input"]
OUTCOMES = ("directed", "undirected", "argmax_changes", "shift4", "shift8", "flip4", "flip8")
HV_TOL = 1e-8  # §6 high-variance invariance: max_d |(W step)_d| <= HV_TOL ||W||_F ||step||
SHUF_TOL = 1e-8  # §6 shuffled direction: cos(W step, Pi(W Delta)) >= 1 - SHUF_TOL
REASONS = ("hook_count", "capture_only_identity", "self_donor_cells", "self_donor_prefix91", "written_rows",
           "untouched_rows", "zero_rule", "hv_invariance", "shuffled_direction")


def _patch_values(xr: np.ndarray, both: np.ndarray, step: np.ndarray | None = None,
                  donor: np.ndarray | None = None) -> np.ndarray:
    """Values (B, 81, d) float32 written by the hook: x_r + step (float64, rounded to
    float32) at the both-empty cells, or the donor rows for a full swap; x_r elsewhere
    (the pilot's `values_for`)."""
    v = xr.copy()
    v[both] = donor[both] if donor is not None else xr[both] + step
    return v.astype(np.float32)


def _same_bits(a: np.ndarray, b: np.ndarray) -> bool:
    a, b = np.ascontiguousarray(a, np.float32), np.ascontiguousarray(b, np.float32)
    return a.shape == b.shape and np.array_equal(a.view(np.uint32), b.view(np.uint32))


def _per_recipient(values: np.ndarray, owner: np.ndarray, n: int) -> np.ndarray:
    """Mean of per-cell `values` per recipient (NaN for a recipient without cells)."""
    cnt = np.bincount(owner, minlength=n).astype(np.float64)
    tot = np.bincount(owner, weights=values, minlength=n)
    out = np.full(n, np.nan)
    out[cnt > 0] = tot[cnt > 0] / cnt[cnt > 0]
    return out


def evaluate_batch(m, comps: dict, heads: dict, pr, pd, cr, cd, empty_r, empty_d, mask_r, mask_d) -> dict:
    """One causal batch (protocol §5.2) with every claim-B check of §6.

    comps: `W` (9, 512), `Q`/`H` (512, 9), `R` (20, 512, 9) float64 and `Pi` (9,);
    heads: `P4`, `P8` seed state dicts; pr/pd: prefix token tensors (B, 91); cr/cd:
    level 1-6 codes (B, 35); empty_*: (B, 81) bool; mask_*: (B, 81, 9) candidate masks.
    Returns the outcome arrays (B, 25) float64 in `CONDITIONS` order, `invalid_reasons`
    and per-recipient `diagnostics` (target norms, actual norms ||x_after - x_before||,
    scale factors, step-Delta cosines; NaN where a quantity does not apply)."""
    cr, cd = np.asarray(cr), np.asarray(cd)
    for name, c in (("cr", cr), ("cd", cd)):
        if c.ndim != 2 or c.shape[1] != LEVELS_1_6:
            raise ValueError(f"{name} must hold exactly the {LEVELS_1_6} codes of levels 1-6, got shape {c.shape}")
    if LEVEL != 7:
        raise ValueError("the causal batch patches the level-7 call only")
    cr_t, cd_t = torch.as_tensor(cr, dtype=torch.long), torch.as_tensor(cd, dtype=torch.long)
    W, Q, H, R, Pi = (np.asarray(comps[k]) for k in ("W", "Q", "H", "R", "Pi"))
    reasons: list[str] = []

    def fail(reason):
        if reason not in reasons:
            reasons.append(reason)

    blocks = m.net.transformer.blocks
    cells_t = torch.as_tensor(PREFIX_CELLS)

    def no_hooks() -> bool:
        return all(len(b._forward_hooks) == 0 for b in blocks)

    def call(prefix, codes, patch=None, expected=None, cells=PREFIX_CELLS):
        """Hooked level-7 call (one hooked forward at a time); checks the hook count,
        written rows (against the hook flag and the independently computed `expected`
        rows (rows, values)) and untouched rows."""
        if not no_hooks():
            fail("hook_count")
        with Level7Hooks(m.net, cells) as h:
            if len(blocks[1]._forward_hooks) != 1:
                fail("hook_count")
            h.patch = patch
            logits = level_logits(m, prefix, codes, LEVEL)
        if h.applied != 1:
            fail("hook_count")
        if patch is not None:
            if not h.untouched_ok:
                fail("untouched_rows")
            rows, values = expected
            after = h.captured["L2_after"][:, torch.as_tensor(cells)].numpy()
            if not (h.written_ok and _same_bits(after[rows], values)):
                fail("written_rows")
        check_finite("logits", logits)
        return logits, h.captured

    # 1. plain clean call: no hook object on the model (application count 0)
    if not no_hooks():
        fail("hook_count")
    lg_plain = level_logits(m, pr, cr_t, LEVEL)
    check_finite("logits", lg_plain)
    # 2.-3. capture-only calls on recipient and donor
    lg_c, cap_r = call(pr, cr_t)
    if not torch.equal(lg_c, lg_plain):
        fail("capture_only_identity")
    _, cap_d = call(pd, cd_t)
    sub = lambda cap, k: cap[k][:, cells_t].numpy()  # noqa: E731
    xr32, xd32 = sub(cap_r, "L2_before"), sub(cap_d, "L2_before")
    check_finite("activations", xr32, xd32)
    xr, xd = xr32.astype(np.float64), xd32.astype(np.float64)
    both = np.asarray(empty_r) & np.asarray(empty_d)
    mask_r, mask_d = np.asarray(mask_r) > 0.5, np.asarray(mask_d) > 0.5
    disc = both[..., None] & (mask_r != mask_d)
    yd = mask_d
    p_clean = code_probs(lg_c)
    check_finite("probabilities", p_clean)
    z_clean = {k: head_logits(sub(cap_r, k), heads["P" + k[1]]) for k in ("L4", "L8")}
    check_finite("head_logits", *z_clean.values())

    # 4. self-donor at the both-empty cells, through the donor indexing path (d := r)
    lg_self, _ = call(pr, cr_t, (both, _patch_values(xr, both, donor=xr)), (both, xr32[both]))
    if not torch.equal(lg_self, lg_c):
        fail("self_donor_cells")
    # 5. self-donor at all 91 prefix positions
    own91 = cap_r["L2_before"][:, :PREFIX_LEN].numpy().copy()
    all91 = np.ones(own91.shape[:2], dtype=bool)
    lg_self91, _ = call(pr, cr_t, (all91, own91), (all91, own91[all91]), cells=np.arange(PREFIX_LEN))
    if not torch.equal(lg_self91, lg_c):
        fail("self_donor_prefix91")

    # steps (float64, the pilot's operation order)
    owner = np.nonzero(both)[0]
    n = len(both)
    delta = (xd - xr)[both]
    stepQ = project_step(delta, Q)
    target = np.linalg.norm(stepQ, axis=1)
    dn = np.linalg.norm(delta, axis=1)

    def matched(raw):
        try:
            return norm_matched(raw, target)
        except ValueError:
            fail("zero_rule")
        step, scale = np.zeros_like(raw), np.zeros(len(raw))
        for i in range(len(raw)):
            try:
                s_i, sc_i = norm_matched(raw[i:i + 1], target[i:i + 1])
            except ValueError:
                continue
            step[i], scale[i] = s_i[0], sc_i[0]
        return step, scale

    steps, scales = {"Q": stepQ}, {"Q": np.ones(len(stepQ))}
    for j in range(N_DRAWS):
        steps[f"rand{j}"], scales[f"rand{j}"] = matched(project_step(delta, R[j]))
    steps["hv"], scales["hv"] = matched(project_step(delta, H))
    steps["shuf"], scales["shuf"] = matched(shuffled_raw(delta, W, Pi))
    check_finite("steps", target, *steps.values())

    # §6 high-variance invariance (float64, scaled step; zero steps skipped)
    hv_norm = np.linalg.norm(steps["hv"], axis=1)
    hv_logit = np.abs(steps["hv"] @ W.T).max(axis=1, initial=0.0)
    nz = hv_norm > 0
    if np.any(hv_logit[nz] > HV_TOL * np.linalg.norm(W) * hv_norm[nz]):
        fail("hv_invariance")
    # §6 shuffled direction (float64): cos(W step_shuf, Pi(W Delta)) for Pi(W Delta) != 0
    want = (delta @ W.T)[:, Pi]
    got = steps["shuf"] @ W.T
    wn, gn = np.linalg.norm(want, axis=1), np.linalg.norm(got, axis=1)
    sel = wn > 0
    cos = np.zeros(len(want))
    ok = sel & (gn > 0)
    cos[ok] = (want[ok] * got[ok]).sum(1) / (wn[ok] * gn[ok])
    if np.any(cos[sel] < 1 - SHUF_TOL):
        fail("shuffled_direction")

    # 6. both-empty full swap
    lg_full, cap_full = call(pr, cr_t, (both, _patch_values(xr, both, donor=xd)), (both, xd32[both]))
    p_full = code_probs(lg_full)
    check_finite("probabilities", p_full)
    tv_clean_full = tv(p_clean, p_full)

    diag = {"target_norm": _per_recipient(target, owner, n),
            **{k: np.full((n, len(CONDITIONS)), np.nan) for k in ("actual_norm", "scale", "cos_delta")},
            "tv_clean_full": tv_clean_full}
    out = {k: np.zeros((n, len(CONDITIONS))) for k in OUTCOMES}
    sgn = 2.0 * yd - 1.0
    n_disc = np.maximum(disc.sum((1, 2)), 1)
    for i, name in enumerate(CONDITIONS):
        if name == "full_be":
            lg, cap = lg_full, cap_full
        elif name == "full_input":
            lg, cap = call(pd, cr_t)
        else:
            step = steps[name]
            lg, cap = call(pr, cr_t, (both, _patch_values(xr, both, step=step)),
                           (both, (xr[both] + step).astype(np.float32)))
        if name != "full_input":
            moved = (sub(cap, "L2_after").astype(np.float64) - sub(cap, "L2_before").astype(np.float64))[both]
            step = delta if name == "full_be" else steps[name]
            sn = np.linalg.norm(step, axis=1)
            diag["actual_norm"][:, i] = _per_recipient(np.linalg.norm(moved, axis=1), owner, n)
            diag["cos_delta"][:, i] = _per_recipient((step * delta).sum(1) / np.maximum(sn * dn, 1e-30), owner, n)
            if name in scales:
                diag["scale"][:, i] = _per_recipient(scales[name], owner, n)
        p = code_probs(lg)
        check_finite("probabilities", p)
        out["directed"][:, i] = tv(p_clean, p_full) - tv(p, p_full)
        out["undirected"][:, i] = tv(p, p_clean)
        out["argmax_changes"][:, i] = (lg.argmax(-1) != lg_c.argmax(-1)).sum(-1).numpy().astype(float)
        for k, key in (("L4", "4"), ("L8", "8")):
            z = head_logits(sub(cap, k), heads["P" + k[1]])
            check_finite("head_logits", z)
            out["shift" + key][:, i] = (sgn * (z - z_clean[k]) * disc).sum((1, 2)) / n_disc
            out["flip" + key][:, i] = (((z >= 0) == yd) & ~((z_clean[k] >= 0) == yd) & disc).sum((1, 2)) / n_disc
    check_finite("outcomes", *out.values())
    return {**out, "conditions": list(CONDITIONS), "invalid_reasons": reasons, "diagnostics": diag}
