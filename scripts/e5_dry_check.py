"""E5 dry-run pass rule (`e5_protocol_v1.md` §9.4): decides whether the protocol may be locked.

Usage: uv run --locked python scripts/e5_dry_check.py

Reads only; never loads the model; safe to rerun. `experiments/e5/dry/check.json` and its sidecar
`check.sha256` are deleted first and written atomically at the end, so an abort leaves no approval.
Every comparison is exact (float64 bit equality; NaN only where a value is undefined, i.e. a pair
without a discordant bit); there is no tolerance anywhere. Parts (each `{"passed", "reasons", ...}`):

- `a`: `subsets.sha256_ids` of the dry ids (runner `pairs.npz`, raw order) equals
  `experiments/e5/pairs.json` `subsets.probe_val.sha256.ids`; so do the dry results' `sha256_ids_raw`,
  its row order and `runs/e5/pairs/probe_val/ids.json`; every row's `pair_index` is its raw index.
- `b` (claim A): per pair id, `n_disc`, `w_P2`, `w_Z`, `w_pilot_rule_P2`, `w_pilot_rule_Z`, `delta`
  and `elig_a` of the dry rows equal `e5test.pair_scores` / `eligibility` applied to the saved pilot
  predictions `runs/e5/pilot/{P2,z6}__shared__none.npy` (shape (2n, 81, 9), NaN exactly on given
  cells) with `e5test.same_inputs` of the saved PROBE-VAL activations (`e5pilot.load_subset` /
  `representation`); the ordered A1/A2 decision inputs (`e5test.decide`) equal the dry ones.
- `c` (claim B): the dry raw causal batch files `runs/e5/dry/causal/<ab|ba>_batch_<k>.npz` and
  `runs/e5/causal/primary.npz` (`meta[:, 0]` pair index, `meta[:, 1]` order 0 = ab / 1 = ba) are
  both mapped by condition name onto `e5batch.CONDITIONS` (a missing, extra or duplicate name on
  either side fails) with complete (pair index, order) coverage; the `directed` values are
  compared per (pair index, order, condition) (`raw_equal`); then the pair means (ab + ba) / 2,
  derived as the runner does, against the dry rows `Q`, `random_mean`, `hv`, `shuf`, `full_be`
  (`pair_means_equal`), `elig_b`, and the ordered B1-B4 decision inputs (`decision_inputs_equal`).
- `d`: both dry runs finished, with `inputs.mode` equal to the run's mode and `inputs.threads` "4",
  every `invalid_reasons` list empty, neither claim `invalid`, no causal batch `invalid_reasons`
  and no extraction `check_failures`.
- `e`: `dry` is processed in raw order and `dry_perm` in the fixed permutation (19 j + 1) mod n, which moves every pair's
  in-batch position and changes every batch's members (each run's recorded `inputs.order` is the
  hash of its processed id order); per pair id every row value of (b) and (c), every ordered
  decision input and every raw causal value per (pair id, order, condition) of `dry_perm` equal
  `dry`'s.
- `code_state` (ruling R8): `code_state.dirty` is false in both `results.json` and in this check's
  own `code_state()`, and all three `commit` values are equal; a missing key fails.
- `run_records`: both `runs/e5/<mode>/run.json` are `finished`; every recorded stage file hashes to
  its recorded SHA-256; every extract/causal batch file on disk is a recorded stage.

`passed` is true only if every part passes and every file of `hashes` exists (`hash_problems`
empty). `hashes` maps ROOT-relative POSIX paths to the SHA-256 of the file bytes (the format
`e5run.require_lock` re-verifies): the three pilot references, the PROBE-VAL ids and
`experiments/e5/pairs.json`, the head and component indexes and files, both `results.json`, both
`run.json` (which carry every raw stage file hash), `scripts/e5_test.py`, this script and
`src/ncm_sudoku/{e5test,e5batch,e5run,e5stats,e5causal,e5extract,probes,e5pilot}.py`, and the PROBE-VAL
pair and activation files part (b) reads (`PROBE_VAL_FILES`). `ids_sha256` is the
`sha256_ids` of the ordered id list. Reported, not gates: `tie_rule_effect` (pilot pair ids whose
`w` differs from `w_pilot_rule`, per representation) and `prediction_max_abs_diff` (dry vs pilot,
dry_perm vs dry).

Fail-closed: a missing file or key, a shape mismatch or an unexpected NaN fails the affected part
with a reason and the record is still written (exit 1). A file that exists but cannot be parsed
stops the check without a record (exit 2), as does any other unexpected error. Exit 0 only when `passed` is true.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

from ncm_sudoku import e5run, subsets
from ncm_sudoku.e5batch import CONDITIONS
from ncm_sudoku.e5pilot import load_subset, representation
from ncm_sudoku.e5test import decide, eligibility, pair_scores, same_inputs
from ncm_sudoku.g0 import code_state
from ncm_sudoku.model import ROOT
from ncm_sudoku.wp2 import atomic_json, atomic_write, file_sha256

CODE_ROOT = ROOT  # code hashes always come from the repository itself
BATCH = 50  # protocol §4.4
THREADS = 4  # protocol §4.4; scripts/e5_test.py records it as the string "4" in inputs.threads
MODES = ("dry", "dry_perm")
REPS = {"P2": "P2", "z6": "Z"}  # representation -> row-key suffix
A_FIELDS = ("n_disc", "w_P2", "w_Z", "w_pilot_rule_P2", "w_pilot_rule_Z", "delta", "elig_a")
B_FIELDS = ("Q", "random_mean", "hv", "shuf", "full_be", "elig_b")
A_INPUTS, B_INPUTS = ("A1_lower", "A1_upper", "A2"), ("B1", "B2", "B3", "B4")
CODE_FILES = ["scripts/e5_test.py", "scripts/e5_dry_check.py"] + [
    f"src/ncm_sudoku/{m}.py" for m in ("e5test", "e5batch", "e5run", "e5stats", "e5causal", "e5extract", "probes",
                                       "e5pilot")]
# PROBE-VAL pair and activation files that part (b) reads through e5pilot.load_subset / representation
PROBE_VAL_FILES = ["runs/e5/pairs/probe_val/a.npy", "runs/e5/pairs/probe_val/b.npy"] + [
    f"runs/e5/acts/probe_val/{m}/{f}.npy" for m in "ab" for f in ("codes", "solved", "prefix_cells", "z6")]
BATCH_FILE = re.compile(r"^(ab|ba)_batch_(\d+)\.npz$")
MAX_LISTED = 5


def fixed_permutation(n: int) -> np.ndarray:
    """The recorded §9.4(e) order; restates `scripts/e5_test.py` PERMUTATION (pinned by a test)."""
    return (19 * np.arange(n) + 1) % n


class Missing(Exception):
    """An expected input file does not exist (the affected part fails)."""


class Unreadable(Exception):
    """An input file exists but cannot be parsed (the check stops without a record)."""


# --- loading -------------------------------------------------------------------------------------

def _json(path: Path):
    if not path.is_file():
        raise Missing(f"missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 - any parse failure is an unreadable input
        raise Unreadable(f"{path}: {type(e).__name__}: {e}") from e


def _npz(path: Path) -> dict:
    if not path.is_file():
        raise Missing(f"missing: {path}")
    try:
        with np.load(path, allow_pickle=False) as z:
            return {k: z[k] for k in z.files}
    except Exception as e:  # noqa: BLE001
        raise Unreadable(f"{path}: {type(e).__name__}: {e}") from e


def _npy(path: Path) -> np.ndarray:
    if not path.is_file():
        raise Missing(f"missing: {path}")
    try:
        return np.load(path, allow_pickle=False)
    except Exception as e:  # noqa: BLE001
        raise Unreadable(f"{path}: {type(e).__name__}: {e}") from e


class Ctx:
    """Lazy, cached inputs of one check."""

    def __init__(self, root: Path, run_dir: dict, out_dir: dict):
        self.root, self.run_dir, self.out_dir = root, run_dir, out_dir
        self._cache: dict = {}
        self.tie_rule_effect = None
        self.code_state = None

    def get(self, key, fn):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    def ids(self) -> list:
        def f():
            ids = _json(self.root / "runs/e5/pairs/probe_val/ids.json")
            if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
                raise ValueError("runs/e5/pairs/probe_val/ids.json is not a list of distinct ids")
            return ids
        return self.get("ids", f)

    def results(self, mode: str) -> dict:
        return self.get(("results", mode), lambda: _json(self.out_dir[mode] / "results.json"))

    def pairs_npz(self, mode: str) -> dict:
        return self.get(("pairs", mode), lambda: _npz(self.run_dir[mode] / "pairs.npz"))

    def subset(self) -> dict:
        def f():
            d = load_subset(self.root, "probe_val")
            if d["n_pairs"] != len(self.ids()):
                raise ValueError(f"PROBE-VAL arrays have {d['n_pairs']} pairs, ids.json {len(self.ids())}")
            return d
        return self.get("subset", f)

    def causal_files(self, mode: str) -> list[tuple[str, int, Path]]:
        d = self.run_dir[mode] / "causal"
        if not d.is_dir():
            raise Missing(f"missing: {d}")
        out = []
        for p in sorted(d.iterdir()):
            m = BATCH_FILE.match(p.name)
            if m:
                out.append((m.group(1), int(m.group(2)), p))
        if not out:
            raise Missing(f"missing: causal batch files in {d}")
        return out


# --- comparison helpers --------------------------------------------------------------------------

def _f64(values, bools: bool = False) -> np.ndarray:
    """float64 array of per-pair values, None -> NaN. With `bools`, every value must be a bool;
    otherwise every value must be None or a real number (never a bool or a string)."""
    out = []
    for v in values:
        if bools:
            if not isinstance(v, (bool, np.bool_)):
                raise TypeError(f"expected a bool, got {v!r}")
        elif v is not None and (isinstance(v, (bool, np.bool_))
                                or not isinstance(v, (int, float, np.integer, np.floating))):
            raise TypeError(f"expected a number or None, got {v!r}")
        out.append(np.nan if v is None else v)
    return np.array(out, dtype=np.float64)


def _eq(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Elementwise exact equality: identical float64 bit patterns, or NaN on both sides."""
    x, y = np.ascontiguousarray(x, np.float64), np.ascontiguousarray(y, np.float64)
    return (x.view(np.uint64) == y.view(np.uint64)) | (np.isnan(x) & np.isnan(y))


def _compare(what: str, ids: list, x: np.ndarray, y: np.ndarray, reasons: list) -> bool:
    if x.shape != y.shape:
        reasons.append(f"{what}: shape {x.shape} != {y.shape}")
        return False
    eq = _eq(x, y)
    if eq.all():
        return True
    bad = np.flatnonzero(~eq.reshape(len(ids), -1).all(axis=1)) if eq.ndim > 1 else np.flatnonzero(~eq)
    i = bad[0]
    reasons.append(f"{what}: {len(bad)} pair(s) differ, first {ids[i]}: {x[i].tolist()!r} vs {y[i].tolist()!r}")
    return False


def _rows(res: dict, ids: list, fields, reasons: list, label: str) -> dict | None:
    """Row values per field in `ids` order (float64, None -> NaN), or None if a row or key is missing."""
    rows = res.get("pairs")
    if not isinstance(rows, dict):
        reasons.append(f"{label}: no per-pair rows")
        return None
    missing = [i for i in ids if i not in rows]
    if missing:
        reasons.append(f"{label}: {len(missing)} pair id(s) without a row, first {missing[0]}")
        return None
    out = {}
    for f in fields:
        absent = [i for i in ids if f not in rows[i]]
        if absent:
            reasons.append(f"{label}: field {f} missing for {len(absent)} pair(s), first {absent[0]}")
            return None
        try:
            out[f] = _f64([rows[i][f] for i in ids], bools=f.startswith("elig_"))
        except TypeError as e:
            reasons.append(f"{label}: field {f}: {e}")
            return None
    return out


def _inputs(res: dict, keys, reasons: list, label: str) -> dict | None:
    try:
        inp = res["decision"]["inputs"]
        return {k: _f64(inp[k]) for k in keys}
    except (KeyError, TypeError) as e:
        reasons.append(f"{label}: decision inputs missing ({type(e).__name__}: {e})")
        return None


def _compare_inputs(label: str, x: dict, y: dict, reasons: list) -> bool:
    ok = True
    for k in x:
        if x[k].shape != y[k].shape or not _eq(x[k], y[k]).all():
            ok = False
            n_diff = "length differs" if x[k].shape != y[k].shape else f"{int((~_eq(x[k], y[k])).sum())} value(s) differ"
            reasons.append(f"{label} {k}: {n_diff} ({x[k].shape[0]} vs {y[k].shape[0]})")
    return ok


def _nan_where_undefined(label: str, ids: list, vals: dict, n_disc: np.ndarray | None, reasons: list) -> None:
    """W-AUC fields may be NaN exactly where `n_disc` is 0; every other field must be finite."""
    for f in ("w_P2", "w_Z", "w_pilot_rule_P2", "w_pilot_rule_Z", "delta"):
        if f not in vals:
            continue
        bad = np.flatnonzero(np.isnan(vals[f]) != (n_disc == 0))
        if bad.size:
            reasons.append(f"{label} {f}: NaN pattern differs from n_disc == 0 at {len(bad)} pair(s), first {ids[bad[0]]}")
    for f in B_FIELDS + ("n_disc", "elig_a"):
        if f in vals and not np.isfinite(vals[f]).all():
            bad = np.flatnonzero(~np.isfinite(vals[f]))
            reasons.append(f"{label} {f}: non-finite at {len(bad)} pair(s), first {ids[bad[0]]}")


def _causal_table(label: str, n: int, entries: list, reasons: list) -> np.ndarray | None:
    """(n, 2, len(CONDITIONS)) float64 from (pair_index, order, names, directed) entries, conditions
    mapped by name; None (with reasons) on any name, shape, coverage or finiteness problem."""
    table = np.full((n, 2, len(CONDITIONS)), np.nan)
    seen = np.zeros((n, 2), int)
    ok = True
    for src, pidx, order, names, directed in entries:
        names = [str(x) for x in np.asarray(names).tolist()]
        if len(set(names)) != len(names):
            reasons.append(f"{label} {src}: duplicate condition names")
            return None
        missing, extra = [c for c in CONDITIONS if c not in names], [c for c in names if c not in CONDITIONS]
        if missing or extra:
            reasons.append(f"{label} {src}: missing condition(s) {missing}, unexpected {extra}")
            return None
        pidx, order, directed = np.asarray(pidx), np.asarray(order), np.asarray(directed, np.float64)
        if directed.shape != (len(pidx), len(names)) or order.shape != pidx.shape or pidx.ndim != 1:
            reasons.append(f"{label} {src}: shapes pair_index {pidx.shape}, order {order.shape}, "
                           f"directed {directed.shape}")
            return None
        if pidx.dtype.kind not in "iu" or order.dtype.kind not in "iu":
            reasons.append(f"{label} {src}: pair_index/order are not integer arrays")
            return None
        if ((pidx < 0) | (pidx >= n)).any() or not np.isin(order, (0, 1)).all():
            reasons.append(f"{label} {src}: pair index or order code out of range")
            return None
        col = [names.index(c) for c in CONDITIONS]
        table[pidx, order] = directed[:, col]
        np.add.at(seen, (pidx, order), 1)
    if (seen != 1).any():
        k = np.argwhere(seen != 1)[0]
        reasons.append(f"{label}: (pair index, order) coverage not exactly once: {int((seen != 1).sum())} key(s), "
                       f"first ({int(k[0])}, {'ab' if k[1] == 0 else 'ba'}) seen {int(seen[k[0], k[1]])} time(s)")
        ok = False
    if ok and not np.isfinite(table).all():
        reasons.append(f"{label}: non-finite directed value(s)")
        ok = False
    return table if ok else None


def _run_causal(ctx: Ctx, mode: str, reasons: list) -> np.ndarray | None:
    ids = ctx.ids()
    entries = []
    for oname, _, path in ctx.causal_files(mode):
        z = _npz(path)
        for key in ("pair_index", "pair_ids", "order", "conditions", "directed"):
            if key not in z:
                reasons.append(f"{mode} {path.name}: key {key} missing")
                return None
        pidx = np.asarray(z["pair_index"])
        if pidx.dtype.kind not in "iu" or ((pidx < 0) | (pidx >= len(ids))).any():
            reasons.append(f"{mode} {path.name}: pair_index out of range")
            return None
        if z["pair_ids"].tolist() != [ids[int(i)] for i in pidx]:
            reasons.append(f"{mode} {path.name}: pair_ids differ from ids.json at pair_index")
            return None
        if not (np.asarray(z["order"]) == (0 if oname == "ab" else 1)).all():
            reasons.append(f"{mode} {path.name}: order code differs from the file's order {oname}")
            return None
        entries.append((path.name, pidx, z["order"], z["conditions"], z["directed"]))
    return _causal_table(mode, len(ids), entries, reasons)


def _pair_values(table: np.ndarray) -> dict:
    """Pair means exactly as `scripts/e5_test.py` derives them: (ab + ba) / 2, then per condition."""
    pv = (table[:, 0] + table[:, 1]) / 2
    ci = {c: i for i, c in enumerate(CONDITIONS)}
    return {"Q": pv[:, ci["Q"]], "random_mean": pv[:, [ci[f"rand{j}"] for j in range(20)]].mean(1),
            "hv": pv[:, ci["hv"]], "shuf": pv[:, ci["shuf"]], "full_be": pv[:, ci["full_be"]]}


def _first_raw_diff(ids: list, x: np.ndarray, y: np.ndarray) -> str:
    bad = np.argwhere(~_eq(x, y))
    i, o, c = bad[0]
    return (f"{len(bad)} value(s) differ, first (pair {ids[i]}, {'ab' if o == 0 else 'ba'}, {CONDITIONS[c]}): "
            f"{x[i, o, c]!r} vs {y[i, o, c]!r}")


# --- pilot side ----------------------------------------------------------------------------------

def _pilot_scores(ctx: Ctx, reasons: list) -> dict | None:
    """pair_scores on the saved pilot predictions with same_inputs of the saved activations."""
    d = ctx.subset()
    n, mask, empty = d["n_pairs"], d["mask"] > 0.5, d["empty"]
    out = {}
    for rep in REPS:
        pred = _npy(ctx.root / "runs/e5/pilot" / f"{rep}__shared__none.npy")
        if pred.shape != (2 * n, 81, 9):
            reasons.append(f"pilot {rep}: shape {pred.shape} != {(2 * n, 81, 9)}")
            return None
        pred = pred.astype(np.float64)
        given = np.broadcast_to(~empty[..., None], pred.shape)
        if not (np.isnan(pred) == given).all() or not np.isfinite(pred[~given]).all():
            reasons.append(f"pilot {rep}: predictions are not NaN exactly on given cells and finite elsewhere")
            return None
        feats = representation(d, rep)
        if feats.shape[0] != 2 * n:
            reasons.append(f"pilot {rep}: activations have {feats.shape[0]} rows, expected {2 * n}")
            return None
        out[rep] = pair_scores(pred, mask, empty, same_inputs(feats, n), n)
    return out


def _pilot_eligibility(ctx: Ctx) -> tuple[np.ndarray, np.ndarray]:
    d = ctx.subset()
    return eligibility(d["mask"] > 0.5, d["empty"], d["n_pairs"])


# --- parts ---------------------------------------------------------------------------------------

def part_a(ctx: Ctx) -> dict:
    reasons = []
    ref = _json(ctx.root / "experiments/e5/pairs.json")["subsets"]["probe_val"]["sha256"]["ids"]
    ids = ctx.ids()
    dry_ids = [str(x) for x in ctx.pairs_npz("dry")["ids"].tolist()]
    res = ctx.results("dry")
    got = {"pairs.npz ids": subsets.sha256_ids(dry_ids), "ids.json": subsets.sha256_ids(ids),
           "results sha256_ids_raw": res.get("sha256_ids_raw"),
           "results row order": subsets.sha256_ids(list(res.get("pairs") or {}))}
    reasons += [f"{k}: {v} != pairs.json {ref}" for k, v in got.items() if v != ref]
    rows = res.get("pairs") or {}
    bad = [p for i, p in enumerate(ids) if not isinstance(rows.get(p), dict) or rows[p].get("pair_index") != i]
    if bad:
        reasons.append(f"rows: pair_index differs from the raw index for {len(bad)} pair(s), first {bad[0]}")
    return {"passed": not reasons, "reasons": reasons, "sha256_ids": got["pairs.npz ids"], "expected": ref}


def part_b(ctx: Ctx) -> dict:
    reasons = []
    ids = ctx.ids()
    sc = _pilot_scores(ctx, reasons)
    if sc is not None:
        ctx.tie_rule_effect = {rep: [ids[i] for i in np.flatnonzero(~_eq(_f64(s["w"]), _f64(s["w_pilot_rule"])))]
                               for rep, s in sc.items()}
    res = ctx.results("dry")
    dry = _rows(res, ids, A_FIELDS, reasons, "dry rows")
    dry_in = _inputs(res, A_INPUTS, reasons, "dry")
    if sc is None or dry is None or dry_in is None:
        return {"passed": False, "reasons": reasons}
    elig_a, _ = _pilot_eligibility(ctx)
    pil = {"n_disc": _f64(sc["P2"]["n_disc"]), "elig_a": elig_a.astype(np.float64)}
    for rep, suf in REPS.items():
        pil[f"w_{suf}"], pil[f"w_pilot_rule_{suf}"] = _f64(sc[rep]["w"]), _f64(sc[rep]["w_pilot_rule"])
    pil["delta"] = pil["w_P2"] - pil["w_Z"]
    if not np.array_equal(_f64(sc["z6"]["n_disc"]), pil["n_disc"]):
        reasons.append("pilot: n_disc differs between P2 and z6 scoring")
    _nan_where_undefined("pilot", ids, pil, pil["n_disc"], reasons)
    _nan_where_undefined("dry", ids, dry, dry["n_disc"], reasons)
    for f in A_FIELDS:
        _compare(f"per-pair {f} (dry vs pilot)", ids, dry[f], pil[f], reasons)
    n = len(ids)
    zeros = np.zeros(n)
    dec = decide(pil["w_P2"], pil["w_Z"], elig_a, zeros, zeros, zeros, zeros, np.zeros(n, bool), [], [])
    ref_in = {k: _f64(dec["inputs"][k]) for k in A_INPUTS}
    inputs_equal = _compare_inputs("decision input (dry vs pilot)", dry_in, ref_in, reasons)
    return {"passed": not reasons, "reasons": reasons, "decision_inputs_equal": inputs_equal,
            "n_a": int(elig_a.sum())}


def part_c(ctx: Ctx) -> dict:
    reasons = []
    ids, n = ctx.ids(), len(ctx.ids())
    dry_tab = _run_causal(ctx, "dry", reasons)
    p = _npz(ctx.root / "runs/e5/causal/primary.npz")
    pil_tab = None
    if all(k in p for k in ("meta", "conditions", "directed")):
        meta = np.asarray(p["meta"])
        if meta.ndim == 2 and meta.shape[1] == 2:
            pil_tab = _causal_table("primary.npz", n, [("primary.npz", meta[:, 0], meta[:, 1], p["conditions"],
                                                        p["directed"])], reasons)
        else:
            reasons.append(f"primary.npz: meta shape {meta.shape}")
    else:
        reasons.append(f"primary.npz: keys {sorted(p)} lack meta/conditions/directed")
    out = {"raw_equal": False, "pair_means_equal": False, "decision_inputs_equal": False}
    if dry_tab is not None and pil_tab is not None:
        out["raw_equal"] = bool(_eq(dry_tab, pil_tab).all())
        if not out["raw_equal"]:
            reasons.append("raw directed (dry vs primary.npz): " + _first_raw_diff(ids, dry_tab, pil_tab))
    res = ctx.results("dry")
    dry = _rows(res, ids, B_FIELDS, reasons, "dry rows")
    dry_in = _inputs(res, B_INPUTS, reasons, "dry")
    if pil_tab is not None and dry is not None:
        pv = _pair_values(pil_tab)
        _, elig_b = _pilot_eligibility(ctx)
        _nan_where_undefined("dry", ids, dry, None, reasons)
        means_ok = all([_compare(f"pair mean {f} (dry vs primary.npz)", ids, dry[f], pv[f], reasons) for f in pv])
        out["pair_means_equal"] = bool(means_ok)
        _compare("per-pair elig_b (dry vs labels)", ids, dry["elig_b"], elig_b.astype(np.float64), reasons)
        if dry_in is not None:
            zeros = np.zeros(n)
            dec = decide(zeros, zeros, np.zeros(n, bool), pv["Q"], pv["random_mean"], pv["hv"], pv["shuf"], elig_b,
                         [], [])
            ref_in = {k: _f64(dec["inputs"][k]) for k in B_INPUTS}
            out["decision_inputs_equal"] = _compare_inputs("decision input (dry vs primary.npz)", dry_in, ref_in,
                                                           reasons)
    return {"passed": not reasons and all(out.values()), "reasons": reasons, **out}


def part_d(ctx: Ctx) -> dict:
    reasons = []
    for mode in MODES:
        try:
            res = ctx.results(mode)
        except Missing as e:
            reasons.append(f"{mode}: {e}")
            continue
        if res.get("mode") != mode:
            reasons.append(f"{mode}: results mode is {res.get('mode')!r}")
        inputs = res.get("inputs") if isinstance(res.get("inputs"), dict) else {}
        if inputs.get("mode") != mode:
            reasons.append(f"{mode}: recorded inputs.mode is {inputs.get('mode')!r}")
        if inputs.get("threads") != str(THREADS):
            reasons.append(f"{mode}: recorded inputs.threads is {inputs.get('threads')!r}, expected {str(THREADS)!r}")
        if res.get("status") != "finished":
            reasons.append(f"{mode}: status {res.get('status')!r}")
        inv = res.get("invalid_reasons")
        if not isinstance(inv, dict) or any(k not in inv for k in ("shared", "A", "B")):
            reasons.append(f"{mode}: invalid_reasons missing or incomplete")
        else:
            reasons += [f"{mode}: invalid_reasons {k}: {v}" for k, v in inv.items() if v]
        outcomes = res.get("outcomes") or {}
        for claim in ("A", "B"):
            if outcomes.get(claim) not in ("holds", "not_shown", "not_estimable"):
                reasons.append(f"{mode}: claim {claim} outcome {outcomes.get(claim)!r}")
        for _, _, path in ctx.causal_files(mode):
            z = _npz(path)
            if "invalid_reasons" not in z:
                reasons.append(f"{mode} {path.name}: invalid_reasons missing")
            elif z["invalid_reasons"].size:
                reasons.append(f"{mode} {path.name}: invalid_reasons {z['invalid_reasons'].tolist()}")
        for member in "ab":
            files = sorted((ctx.run_dir[mode] / "extract" / member).glob("batch_*.npz"))
            if not files:
                reasons.append(f"{mode}: no extraction batches for member {member}")
            for path in files:
                z = _npz(path)
                if "check_failures" not in z:
                    reasons.append(f"{mode} extract/{member}/{path.name}: check_failures missing")
                elif z["check_failures"].size:
                    reasons.append(f"{mode} extract/{member}/{path.name}: {z['check_failures'].tolist()}")
    return {"passed": not reasons, "reasons": reasons}


def part_e(ctx: Ctx) -> dict:
    reasons = []
    ids, n = ctx.ids(), len(ctx.ids())
    orders = {}
    for mode in MODES:
        pz = ctx.pairs_npz(mode)
        if [str(x) for x in pz["ids"].tolist()] != ids:
            reasons.append(f"{mode}: pairs.npz ids differ from ids.json")
        orders[mode] = np.asarray(pz["order"])
        rec_order = (ctx.results(mode).get("inputs") or {}).get("order")
        if (orders[mode].shape != (n,) or sorted(orders[mode].tolist()) != list(range(n))):
            reasons.append(f"{mode}: processing order is not a permutation of the {n} pairs")
        elif rec_order != subsets.sha256_ids([ids[i] for i in orders[mode]]):
            reasons.append(f"{mode}: recorded inputs.order differs from the processing order of pairs.npz")
    if not reasons:
        if not np.array_equal(orders["dry"], np.arange(n)):
            reasons.append("dry: not processed in raw order")
        perm, j = orders["dry_perm"], np.arange(n)
        if not np.array_equal(perm, fixed_permutation(n)):
            reasons.append("dry_perm: processing order is not the fixed permutation (19 j + 1) mod n")
        if (perm % BATCH == j % BATCH).any():
            reasons.append("dry_perm: some pair keeps its in-batch position")
        raw_batches = [set(range(s, min(s + BATCH, n))) for s in range(0, n, BATCH)]
        if any(set(perm[s:s + BATCH].tolist()) in raw_batches for s in range(0, n, BATCH)):
            reasons.append("dry_perm: some batch keeps its raw members")
    fields = A_FIELDS + B_FIELDS
    rows = {mode: _rows(ctx.results(mode), ids, fields, reasons, f"{mode} rows") for mode in MODES}
    if all(r is not None for r in rows.values()):
        for f in fields:
            _compare(f"per-pair {f} (dry_perm vs dry)", ids, rows["dry_perm"][f], rows["dry"][f], reasons)
    ins = {mode: _inputs(ctx.results(mode), A_INPUTS + B_INPUTS, reasons, mode) for mode in MODES}
    if all(x is not None for x in ins.values()):
        _compare_inputs("decision input (dry_perm vs dry)", ins["dry_perm"], ins["dry"], reasons)
    tabs = {mode: _run_causal(ctx, mode, reasons) for mode in MODES}
    if all(t is not None for t in tabs.values()) and not _eq(tabs["dry_perm"], tabs["dry"]).all():
        reasons.append("raw directed (dry_perm vs dry): " + _first_raw_diff(ids, tabs["dry_perm"], tabs["dry"]))
    elif any(t is None for t in tabs.values()):
        reasons.append("raw directed: a causal table could not be built")
    return {"passed": not reasons, "reasons": reasons}


def part_run_records(ctx: Ctx) -> dict:
    reasons = []
    for mode in MODES:
        rd = ctx.run_dir[mode]
        rec = _json(rd / "run.json")
        if rec.get("status") != "finished":
            reasons.append(f"{mode}: run.json status {rec.get('status')!r}")
        stages = rec.get("stages")
        if not isinstance(stages, dict):
            reasons.append(f"{mode}: run.json has no stages")
            continue
        for required in ("pairs", "probes", "decisions"):
            if required not in stages:
                reasons.append(f"{mode}: stage {required} not recorded")
        for prefix in ("extract/a/", "extract/b/", "causal/ab_", "causal/ba_"):
            if not any(s.startswith(prefix) for s in stages):
                reasons.append(f"{mode}: no recorded stage {prefix}*")
        for stage, info in stages.items():
            path = rd / (stage + (".json" if stage == "decisions" else ".npz"))
            if not path.is_file():
                reasons.append(f"{mode}: stage {stage}: {path} missing")
            elif not isinstance(info, dict) or file_sha256(path) != info.get("sha256"):
                reasons.append(f"{mode}: stage {stage}: file differs from its recorded SHA-256")
        on_disk = [p for p in rd.glob("extract/*/*.npz")] + [p for p in rd.glob("causal/*.npz")]
        for p in on_disk:
            stage = p.relative_to(rd).with_suffix("").as_posix()
            if stage not in stages:
                reasons.append(f"{mode}: {p.relative_to(rd).as_posix()} is not a recorded stage")
    return {"passed": not reasons, "reasons": reasons}


def part_code_state(ctx: Ctx) -> dict:
    """Ruling R8: both dry runs and this check ran on clean code at one and the same commit."""
    reasons = []
    states = {mode: ctx.results(mode).get("code_state") for mode in MODES}
    states["check"] = ctx.code_state
    for who, st in states.items():
        if not isinstance(st, dict) or "dirty" not in st or "commit" not in st:
            reasons.append(f"{who}: code_state missing or without dirty/commit")
        elif st["dirty"] is not False:
            reasons.append(f"{who}: code_state dirty is {st['dirty']!r}")
    commits = {who: st.get("commit") for who, st in states.items() if isinstance(st, dict)}
    if len(set(commits.values())) != 1 or None in commits.values():
        reasons.append(f"commits differ or are missing: {commits}")
    return {"passed": not reasons, "reasons": reasons, "commits": commits}


PARTS = {"code_state": part_code_state, "a": part_a, "b": part_b, "c": part_c, "d": part_d, "e": part_e, "run_records": part_run_records}


def _run_part(fn, ctx: Ctx) -> dict:
    try:
        return fn(ctx)
    except Missing as e:
        return {"passed": False, "reasons": [str(e)]}
    except (FileNotFoundError, KeyError, IndexError, ValueError, TypeError, AttributeError) as e:
        return {"passed": False, "reasons": [f"{type(e).__name__}: {e}"]}


# --- information and hashes ----------------------------------------------------------------------

def _pred_rows(pr: dict, ids: list) -> np.ndarray:
    """Raw pilot-layout row (a: i, b: n + i) of every probes.npz row."""
    pos, n = {p: i for i, p in enumerate(ids)}, len(ids)
    return np.array([pos[str(p)] + (0 if m == "a" else n) for p, m in zip(pr["pair_ids"].tolist(), pr["member"].tolist())])


def _diff(x: np.ndarray, y: np.ndarray) -> dict:
    both = np.isfinite(x) & np.isfinite(y)
    return {"max_abs_diff": float(np.abs(x[both] - y[both]).max()) if both.any() else None,
            "nan_pattern_equal": bool(np.array_equal(np.isnan(x), np.isnan(y)))}


def prediction_info(ctx: Ctx) -> dict:
    """Information only (not a gate): max |difference| of the mean predictions."""
    out = {"dry_vs_pilot": {}, "dry_perm_vs_dry": {}}
    try:
        ids = ctx.ids()
        raw = {}
        for mode in MODES:
            pr = _npz(ctx.run_dir[mode] / "probes.npz")
            rows = _pred_rows(pr, ids)
            raw[mode] = {}
            for rep in REPS:
                arr = np.full((2 * len(ids), 81, 9), np.nan)
                arr[rows] = pr[f"{rep}_mean"]
                raw[mode][rep] = arr
        for rep in REPS:
            pilot = _npy(ctx.root / "runs/e5/pilot" / f"{rep}__shared__none.npy").astype(np.float64)
            out["dry_vs_pilot"][rep] = _diff(raw["dry"][rep], pilot)
            out["dry_perm_vs_dry"][rep] = _diff(raw["dry_perm"][rep], raw["dry"][rep])
    except (Missing, KeyError, IndexError, ValueError, TypeError) as e:
        out["error"] = f"{type(e).__name__}: {e}"
    return out


def _hash_files(ctx: Ctx, problems: list) -> dict:
    r = ctx.root
    data = [r / "runs/e5/pilot/P2__shared__none.npy", r / "runs/e5/pilot/z6__shared__none.npy",
            r / "runs/e5/causal/primary.npz", r / "runs/e5/pairs/probe_val/ids.json", r / "experiments/e5/pairs.json",
            r / "experiments/e5/causal/heads.json", r / "experiments/e5/lock/components.json"]
    data += [r / f for f in PROBE_VAL_FILES]
    for name, key, keys in (("experiments/e5/causal/heads.json", "heads", ("P2", "P4", "P8")),
                            ("experiments/e5/lock/components.json", "files",
                             ("z6_head", "W", "Q", "H", "R", "Pi"))):
        try:
            index = _json(r / name)[key]
            data += [r / index[k]["file"] for k in keys]
        except (Missing, KeyError, TypeError) as e:
            problems.append(f"{name}: cannot list files ({type(e).__name__}: {e})")
    for mode in MODES:
        data += [ctx.out_dir[mode] / "results.json", ctx.run_dir[mode] / "run.json"]
    files = [(p, r) for p in data] + [(CODE_ROOT / c, CODE_ROOT) for c in CODE_FILES]
    hashes = {}
    for p, base in files:
        try:
            rel = Path(p).resolve().relative_to(Path(base).resolve()).as_posix()
        except ValueError:
            problems.append(f"not under the root: {p}")
            continue
        if not Path(p).is_file():
            problems.append(f"missing: {rel}")
            continue
        hashes[rel] = file_sha256(p)
    return hashes


def run_check(root: Path, run_dir: dict, out_dir: dict) -> dict:
    """The §9.4 record; raises `Unreadable` if an existing input cannot be parsed."""
    ctx = Ctx(root, run_dir, out_dir)
    ctx.code_state = code_state()
    parts = {name: _run_part(fn, ctx) for name, fn in PARTS.items()}
    problems: list = []
    hashes = _hash_files(ctx, problems)
    try:
        ids_sha = subsets.sha256_ids(ctx.ids())
    except (Missing, ValueError) as e:
        ids_sha = None
        problems.append(f"ids: {e}")
    passed = all(p["passed"] for p in parts.values()) and not problems
    return {"note": "E5 dry-run pass rule (e5_protocol_v1.md §9.4); exact comparisons, no tolerance",
            "date": time.strftime("%Y-%m-%d"), "passed": bool(passed), "parts": parts,
            "tie_rule_effect": ctx.tie_rule_effect, "prediction_max_abs_diff": prediction_info(ctx),
            "ids_sha256": ids_sha, "hashes": hashes, "hash_problems": problems, "code_state": ctx.code_state}


def main(argv: list[str] | None = None) -> None:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    out = e5run.OUT_DIR["dry"]
    check, sidecar = out / "check.json", out / "check.sha256"
    check.unlink(missing_ok=True)
    sidecar.unlink(missing_ok=True)
    try:
        record = run_check(ROOT, e5run.RUN_DIR, e5run.OUT_DIR)
    except Unreadable as e:
        print(f"e5_dry_check: unreadable input, no record written: {e}", file=sys.stderr, flush=True)
        sys.exit(2)
    except Exception as e:  # noqa: BLE001 - any other failure: no record, nonzero exit
        print(f"e5_dry_check: {type(e).__name__}: {e}; no record written", file=sys.stderr, flush=True)
        sys.exit(2)
    atomic_json(check, record)
    atomic_write(sidecar, file_sha256(check) + "\n")
    print(json.dumps({"passed": record["passed"], **{k: v["passed"] for k, v in record["parts"].items()}}),
          flush=True)
    sys.exit(0 if record["passed"] else 1)


if __name__ == "__main__":
    main()
