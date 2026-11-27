"""E5 TEST pair screening, eligibility, within-pair scoring and claim decisions
(protocol §4.1, §5.1, §5.3, §6).

Candidate pair solutions are screened against a precomputed index of external
canonical keys (gate, CAL, PROBE-TRAIN, PROBE-VAL, WP2 TEST, released hard set,
the E5 PROBE-TRAIN and PROBE-VAL pairs); a colliding candidate is rejected and
the raw index steps to the next candidate until N pairs are accepted. A
generation error propagates and stops the run; it never silently becomes a step
to the next index. After the accepted set is fixed, internal collisions among
its own solution orbits are only logged, never replaced (D99's internal
replacement does not apply to TEST). Eligibility for claims A and B is decided
from candidate-mask labels alone, before any model output is read.

`head_probs` reproduces the pilot's probe-inference path (float32 Linear +
Sigmoid per seed, float32 seed mean, float64 scatter) in puzzle batches.
`pair_scores` scores discordant bits as in `e5pilot.w_auc`, with the protocol
§5.1 identical-input tie rule (a bit-identical probe input at a cell scores 0.5
regardless of the predictions); `w_pilot_rule` keeps the pre-tie-rule score for
the §9.4 dry-run comparison. `decide` reads claims A and B (protocol §5.3) over
the eligible pairs in raw index order with the fixed `n_plan` of 400, and
reports every condition's ordered decision input and log capital alongside the
four-way outcome of §6 (`invalid`, `not_estimable`, `holds`, `not_shown`).
`check_finite` is the shared finiteness gate of §6; `bootstrap` is the
percentile pair-bootstrap of §5.3's estimates (seed 0, 10,000 resamples).
"""

from typing import Callable

import numpy as np
import torch

from ncm_sudoku.e5pairs import Pair
from ncm_sudoku.e5stats import B1_MIN, DELTA_MIN, EPSILON, betting_logk, claim_a, claim_b, to_unit
from ncm_sudoku.probes import build_inputs
from ncm_sudoku.symmetry import canonical_form

N_PLAN = 400  # protocol §5.3: always 400, never inferred from the sample
N_BOOT, BOOT_SEED = 10000, 0


class NonFiniteError(RuntimeError):
    """Raised by `check_finite` when a checked array holds a non-finite element."""


def canonical_key(solution: np.ndarray) -> bytes:
    """Exact canonical form of a solution grid (the key `symmetry.screen_canonical` uses)."""
    return canonical_form(solution)


def external_index(entries: dict[str, list[tuple[str, np.ndarray]]]) -> dict[bytes, str]:
    """Canonical key -> first external id, built once over every named collection."""
    index: dict[bytes, str] = {}
    for items in entries.values():
        for pid, solution in items:
            key = canonical_key(solution)
            if key not in index:
                index[key] = pid
    return index


def screen_pairs(make_pair: Callable[[int], Pair], index: dict[bytes, str], n: int) -> tuple[list[Pair], list[dict]]:
    """Raw index from 0: a pair whose solution's canonical key is in `index` is
    rejected and logged; accepted pairs accumulate until the n-th is reached.
    Any exception `make_pair` raises propagates unchanged."""
    accepted: list[Pair] = []
    log: list[dict] = []
    i = 0
    while len(accepted) < n:
        pair = make_pair(i)
        colliding_id = index.get(canonical_key(pair.solution))
        ok = colliding_id is None
        log.append({"index": i, "pair_id": pair.pair_id, "accepted": ok,
                     "reason": None if ok else "external_collision", "colliding_id": colliding_id})
        if ok:
            accepted.append(pair)
        i += 1
    return accepted, log


def internal_collisions(pairs: list[Pair]) -> list[tuple[str, str]]:
    """Every pair of pair ids whose solutions share a canonical-form orbit."""
    by_key: dict[bytes, list[str]] = {}
    for p in pairs:
        by_key.setdefault(canonical_key(p.solution), []).append(p.pair_id)
    out: list[tuple[str, str]] = []
    for ids in by_key.values():
        if len(ids) >= 2:
            out += [(ids[a], ids[b]) for a in range(len(ids)) for b in range(a + 1, len(ids))]
    return out


def eligibility(mask: np.ndarray, empty: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Members stacked a then b. `elig_a` = at least one cell empty in both
    members with a digit that is a candidate in exactly one of them (a
    discordant bit); `elig_b` = at least one cell empty in both members."""
    ma, mb, ea, eb = mask[:n], mask[n:], empty[:n], empty[n:]
    both = ea & eb
    disc = both[..., None] & (ma != mb)
    return disc.any(axis=(1, 2)), both.any(axis=1)


def check_finite(name: str, *arrays) -> None:
    """Raises `NonFiniteError(name)` if any element of any given array is not finite
    (protocol §6: activations, logits, probe predictions on evaluable bits and every
    per-pair quantity are checked before any argmax, quantization or aggregation)."""
    for arr in arrays:
        if not np.all(np.isfinite(np.asarray(arr))):
            raise NonFiniteError(name)


def _head_module(state_dict: dict) -> torch.nn.Module:
    """Builds the probe linear-sigmoid head the way `probes._make_model("linear", ...)`
    does, loads the given seed's state dict (keys `0.weight`, `0.bias`) into it."""
    in_dim = state_dict["0.weight"].shape[1]
    model = torch.nn.Sequential(torch.nn.Linear(in_dim, 9), torch.nn.Sigmoid())
    model.load_state_dict(state_dict)
    model.eval()
    return model


def _scatter(rows: np.ndarray, empty: np.ndarray) -> np.ndarray:
    """Row predictions (row-major over np.nonzero(empty)) -> (n, 81, 9) float64, NaN
    on given cells (equivalent to `e5pilot.scatter`)."""
    out = np.full((*empty.shape, 9), np.nan, dtype=np.float64)
    out[empty] = rows
    return out


def head_probs(
    state_dicts: list[dict], features: np.ndarray, empty: np.ndarray, batch: int = 50
) -> tuple[np.ndarray, np.ndarray]:
    """Protocol §5.1 probe inference: per-seed float32 probabilities (3, n_rows, 9)
    and their float32 seed mean scattered to (n_puzzles, 81, 9) float64 with NaN on
    given cells. Inputs are built per batch of `batch` puzzles, in the given row
    order, through `probes.build_inputs`; concatenating the per-batch rows gives the
    same row order as building every row at once, since batches are contiguous
    puzzle blocks and `build_inputs` orders rows row-major over (puzzle, position).
    Enables deterministic algorithms first (`probes.train_probe`'s own rule). The
    Linear step is exactly batch-size invariant; the CPU vectorized Sigmoid kernel's
    grain-size splitting can still round a tail lane up to 1 float32 ulp differently
    between a chunked and an unchunked call over the same rows (a non-associativity
    of the vectorized kernel, not of this function)."""
    torch.use_deterministic_algorithms(True)
    models = [_head_module(sd) for sd in state_dicts]
    n_puzzles = features.shape[0]
    chunks: list[list[np.ndarray]] = [[] for _ in models]
    for start in range(0, n_puzzles, batch):
        stop = min(start + batch, n_puzzles)
        X, _, _ = build_inputs(features[start:stop], empty[start:stop])
        with torch.no_grad():
            for i, model in enumerate(models):
                chunks[i].append(model(X).numpy())
    per_seed = np.stack([np.concatenate(c, axis=0) for c in chunks], axis=0)
    mean = np.mean(per_seed, axis=0)
    return per_seed, _scatter(mean, empty)


def same_inputs(features: np.ndarray, n: int) -> np.ndarray:
    """(n, 81) bool: exact (bit-identical) equality of the two members' feature rows
    at each cell -- the protocol §5.1 identical-input tie rule. Members stacked a
    then b, as everywhere else in this module."""
    a, b = features[:n], features[n:]
    return np.all(a == b, axis=-1)


def pair_scores(
    pred: np.ndarray, mask: np.ndarray, empty: np.ndarray, same_input: np.ndarray, n: int
) -> dict:
    """Protocol §5.1 within-pair AUC per pair. Members stacked a then b. Over the
    discordant bits of a pair (both members empty at the cell, the digit a
    candidate in exactly one member): score 1 if the candidate member's
    probability is higher, 0 if lower, 0.5 if equal, as in `e5pilot.w_auc`; a cell
    flagged in `same_input` (bit-identical probe inputs between the members)
    scores 0.5 at every discordant bit there regardless of the predictions.
    `n_disc` is the discordant-bit count; `w` is the mean score over those bits
    (NaN if `n_disc` is 0); `w_pilot_rule` is the same mean without the
    identical-input override (kept for the protocol §9.4 dry-run report)."""
    pa, pb = pred[:n], pred[n:]
    ya, yb = mask[:n] > 0.5, mask[n:] > 0.5
    both = empty[:n] & empty[n:]
    disc = both[..., None] & (ya != yb)
    p_cand = np.where(ya, pa, pb)
    p_non = np.where(ya, pb, pa)
    score = np.where(p_cand > p_non, 1.0, np.where(p_cand == p_non, 0.5, 0.0))
    tied = np.where(same_input[..., None], 0.5, score)
    n_disc = disc.sum(axis=(1, 2))
    with np.errstate(invalid="ignore"):
        w = (tied * disc).sum(axis=(1, 2)) / n_disc
        w_pilot_rule = (score * disc).sum(axis=(1, 2)) / n_disc
    w = np.where(n_disc == 0, np.nan, w)
    w_pilot_rule = np.where(n_disc == 0, np.nan, w_pilot_rule)
    return {"n_disc": n_disc.astype(int).tolist(), "w": w.tolist(), "w_pilot_rule": w_pilot_rule.tolist()}


def bootstrap(x: np.ndarray) -> dict:
    """95% percentile pair-bootstrap (10,000 resamples, seed 0), same as
    `scripts/e5_causal.py`'s `bootstrap`; non-finite values are dropped first."""
    x = np.asarray(x, np.float64)
    x = x[np.isfinite(x)]
    rng = np.random.default_rng(BOOT_SEED)
    means = rng.choice(x, size=(N_BOOT, len(x)), replace=True).mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return {"mean": float(x.mean()), "ci95": [float(lo), float(hi)], "n": int(len(x)),
            "degenerate": bool(hi - lo == 0)}


def decide(
    w_p2: np.ndarray, w_z: np.ndarray, elig_a: np.ndarray,
    q: np.ndarray, rand: np.ndarray, hv: np.ndarray, shuf: np.ndarray, elig_b: np.ndarray,
    invalid_a: list[str], invalid_b: list[str],
) -> dict:
    """Protocol §5.3 claim decisions. Builds the ordered decision inputs over the
    eligible pairs (raw index order, `elig_a`/`elig_b` boolean masks) and reads
    `claim_a`/`claim_b` and every condition's log capital at the fixed `N_PLAN`
    (400, never the realized eligible count). Outcome per claim (§6): `invalid` if
    its invalid-reason list is non-empty, else `not_estimable` if no pair is
    eligible, else `holds` or `not_shown` from the claim's intersection flag."""
    w_p2, w_z = np.asarray(w_p2, np.float64), np.asarray(w_z, np.float64)
    elig_a = np.asarray(elig_a, bool)
    q, rand, hv, shuf = (np.asarray(a, np.float64) for a in (q, rand, hv, shuf))
    elig_b = np.asarray(elig_b, bool)

    w_p2_e, w_z_e = w_p2[elig_a], w_z[elig_a]
    q_e, rand_e, hv_e, shuf_e = q[elig_b], rand[elig_b], hv[elig_b], shuf[elig_b]
    n_a, n_b = int(elig_a.sum()), int(elig_b.sum())

    inputs = {
        "A1_lower": w_z_e,
        "A1_upper": 1.0 - w_z_e,
        "A2": to_unit(w_p2_e - w_z_e),
        "B1": to_unit(q_e),
        "B2": to_unit(q_e - rand_e),
        "B3": to_unit(q_e - hv_e),
        "B4": to_unit(q_e - shuf_e),
    }
    m0 = {
        "A1_lower": 0.5 - EPSILON, "A1_upper": 0.5 - EPSILON,
        "A2": to_unit(DELTA_MIN), "B1": to_unit(B1_MIN),
        "B2": 0.5, "B3": 0.5, "B4": 0.5,
    }
    log_k = {name: (float(betting_logk(x, m0[name], n_plan=N_PLAN)) if x.size else float("nan"))
             for name, x in inputs.items()}

    claim_a_res = (claim_a(w_p2_e, w_z_e, n_plan=N_PLAN) if n_a
                   else {"A1_lower": False, "A1_upper": False, "A2": False, "A": False})
    claim_b_res = (claim_b(q_e, rand_e, hv_e, shuf_e, n_plan=N_PLAN) if n_b
                   else {"B1": False, "B2": False, "B3": False, "B4": False, "B": False})

    def outcome(invalid_list, n, holds):
        if invalid_list:
            return "invalid"
        if n == 0:
            return "not_estimable"
        return "holds" if holds else "not_shown"

    return {
        "n_a": n_a, "n_b": n_b,
        "inputs": {name: x.tolist() for name, x in inputs.items()},
        "m0": m0,
        "log_k": log_k,
        "claim_a": {k: bool(v) for k, v in claim_a_res.items()},
        "claim_b": {k: bool(v) for k, v in claim_b_res.items()},
        "outcomes": {
            "A": outcome(invalid_a, n_a, bool(claim_a_res["A"])),
            "B": outcome(invalid_b, n_b, bool(claim_b_res["B"])),
        },
    }
