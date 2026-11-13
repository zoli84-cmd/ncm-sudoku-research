"""WP2 dry-run comparison (plan v3.7 §10, §12.2; D76(2)-(3); WP2 plan spec ambiguities 11, 12, 13, 23, 24).

Usage: uv run --locked python scripts/wp2_dry_check.py

Compares the dry run (E2 and E1 on the first 50 CAL puzzles, E3 with PROBE-VAL in the TEST role,
level-12 equivariance) with the pre-lock records and writes `experiments/wp2/dry/check.json` and
`check.md`. `technical_success: true` in `check.json` is the gate for every TEST run
(`wp2._test_gate`), together with `code.commit` equal to the tag commit and the hashed `snapshot`,
which `wp2.verify_dry_approval` recomputes before every TEST start.

Reads only; never loads the model. Safe to rerun: `check.json` and `check.md` are deleted first and
written atomically at the end, so a refusal (a dry output that differs from its run record's
manifest, a missing run record) leaves no approval behind. Prints only
`status_line(runner="dry_check", complete=True, valid=technical_success)`.

Inputs, each read once and hashed from the bytes that are parsed:
- the five dry run records `experiments/wp2/dry/runs/{e3_extract,e3,equiv,e2,e1}.json`;
- dry outputs, each checked against its run record's `outputs` first: `runs/wp2/dry/e2.json`,
  `runs/wp2/dry/e2/parts.json`, `runs/wp2/dry/e1.json`, `experiments/wp2/dry/e3_fits.json`,
  `e3_budget.json`, `equivariance.json`; the score arrays (`score_manifest` of the extract record)
  and the depth predictions (`e3_fits.json` `files`);
- references: `runs/e2p2/pilot2.json`, `runs/lock/level1_full_batch.json`,
  `experiments/e3prep/probes.json`, `experiments/e3prep/wholelayer.json`,
  `experiments/lock/equivariance_l12.json`;
- the dry evaluation `experiments/wp2/dry/results.json` and `report.md` (`dry_evaluate_part`; both
  join the `compared` snapshot group).

`technical_success` requires every dry record valid at the tag commit (`wp2.valid_record`), the dry
ids equal to the first 50 CAL ids of both E2 references, exact equality with complete key coverage
for E2 (configuration records over `E2_FIELDS`, level 1 including the no-op rows and both weights,
base), E1 (`solve` against the pilot-2 `solve_A`) and the extraction (`matches_e3prep`), equal
configs and allclose `per_puzzle` for every mapped E3 fit (`E3_MAP`), the depth breakdown
(`DEPTH_MAP`) and equivariance, zero solve-based and code-based E2 identity failures in both the
E2 output and the run record (spec ambiguity 23), and PROBE files that still match the dry e3
record's `inputs`, and the dry evaluation (`dry_evaluate`): `results.json` and `report.md` present,
role dry, `code_state` at the tag commit and clean, every recorded input under `runs/wp2/dry/` and
`experiments/wp2/dry/` unchanged, and the five dry outputs read here recorded with their current
SHA-256. A missing dry evaluation is a failed part, not a refusal. `NEW_FITS` have no pre-lock
reference and are only listed. The check itself must run
frozen (`freeze_state()["frozen"]`) on clean code, with `code_state()` and `freeze_state()` unchanged between
its start and end (`check_state`; `code_end` and `freeze_state_end` are recorded next to the start states).
The E2 `level1_noop_mismatch` is recomputed from the level-1 rows (`e2p2.level1_noop_mismatch`); the stored
count must be zero as well.
"""

import argparse
import hashlib
import importlib.util
import io
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch

import ncm_sudoku.e2p2 as e2p2
from ncm_sudoku import wp2
from ncm_sudoku.e2 import POLICIES
from ncm_sudoku.e3metrics import DEPTH_CLASSES, depth_breakdown_seeds
from ncm_sudoku.probes import SEEDS
from ncm_sudoku.wp2e3 import STAGE_FITS

NAME = "dry_check"
ROLE = "dry"
RUNNERS = ("e3_extract", "e3", "equiv", "e2", "e1")
MAX_LISTED = 50
ACCEPTABLE = 0.0116  # spec ambiguity 6
E2_KEYS = ("puzzle_id", "level", "policy", "dose", "seed")
E2_FIELDS = (*E2_KEYS, "eligible", "solve_A", "solve_B", "solve_C", "solve_D", "well_formed_C", "well_formed_D",
             "tv", "tv_empty", "hamming_CA", "hamming_CA_empty", "latent", "codebook_rms", "requant_ratio",
             "downstream_changes_D")
L1_KEYS = ("puzzle_id", "value")
L1_FIELDS = ("noop", "w_frequency", "w_uniform", "solve_C", "solve_D", "well_formed_C", "well_formed_D", "tv",
             "tv_empty", "hamming_CA", "hamming_CA_empty", "latent", "codebook_rms", "requant_ratio",
             "downstream_changes_D")
BASE_FIELDS = ("solve_A", "solve_B1")
CONFIG_DOSES = {2: (1, 2), 6: (1, 2, 4, 8, 13), 11: (1, 4, 11, 21, 41, 67)}  # DOSE_FRACTIONS_V36 (§12.2)
E2_LEVEL_KEYS = frozenset(str(lv) for lv in CONFIG_DOSES)
N_CONFIG_SEEDS = 78  # per puzzle: 13 level-dose nodes x 2 policies x 3 seeds
N_LEVEL1_VALUES = 16
REFERENCES = {
    "pilot2": "runs/e2p2/pilot2.json",
    "level1_full_batch": "runs/lock/level1_full_batch.json",
    "probes.json": "experiments/e3prep/probes.json",
    "wholelayer.json": "experiments/e3prep/wholelayer.json",
    "equivariance_l12": "experiments/lock/equivariance_l12.json",
}
EQUIV_CONFIG = ("level", "n", "k", "seed", "n_predictors", "ids")
EQUIV_ARRAYS = ("deviation", "seed_noise", "brier", "brier_original")


def _e3_map() -> dict[str, tuple[str, tuple[str, ...]]]:
    """Dry `stage.fit` -> (reference file, key path), D64 (`probes.json`) and D67 (`wholelayer.json`)."""
    m = {}
    for lv in ("L06", "L12"):
        for fit in STAGE_FITS[f"wl_{lv}"]:
            m[f"wl_{lv}.{fit}"] = ("wholelayer.json", ("stages", lv, f"{fit}_linear"))
    m["wl_teacher_L12.teacher"] = ("wholelayer.json", ("stages", "teacher_L12", "teacher_linear"))
    for stage in ("raw_projected", "raw_unprojected"):
        m[f"{stage}.linear"] = ("wholelayer.json", ("stages", stage, "linear"))
    for lv in ("L02", "L06", "L12"):
        for fit in STAGE_FITS[f"pc_{lv}"]:
            m[f"pc_{lv}.{fit}"] = ("probes.json", ("stages", f"{lv}_permuted_linear" if fit == "permuted"
                                                   else f"{lv}_{fit}"))
    for stage in ("controls", "unit_digit"):
        for fit in STAGE_FITS[stage]:
            m[f"{stage}.{fit}"] = ("probes.json", ("stages", stage, fit))
    for fit in STAGE_FITS["training_size"]:
        m[f"training_size.{fit}"] = ("probes.json", ("stages", "training_size", fit[1:]))
    return m


if sum(map(len, CONFIG_DOSES.values())) * len(POLICIES) * len(e2p2.SEEDS_P2) != N_CONFIG_SEEDS:
    raise RuntimeError("the E2 configuration grid differs from the locked 78 configuration-seed keys")
E3_MAP = _e3_map()
NEW_FITS = frozenset(f"{s}.{f}" for s in ("wl_L02", "wl_L06_controls", "wl_teacher_L06", "wl_training_size")
                     for f in STAGE_FITS[s])
DEPTH_MAP = {"generated_linear": "pc_L06.linear", "raw_linear": "controls.raw_linear"}  # -> probes.json depth_L06


def _script(name: str):
    spec = importlib.util.spec_from_file_location(f"_{NAME}_{name}", Path(__file__).resolve().parent / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXTRACT_ARRAYS = tuple(_script("wp2_e3_extract").ARRAY_NAMES)  # the arrays `compare_dirs` checks
PROBE_INPUT_FILES = tuple(_script("wp2_e3").INPUT_FILES)  # per PROBE subset in the e3 `inputs` manifest


# --- reading -------------------------------------------------------------------------------------

def _rel(path: Path) -> str:
    return Path(path).resolve().relative_to(Path(wp2.ROOT).resolve()).as_posix()


class Reader:
    """Reads each file once; the SHA-256 is taken from the parsed bytes and, when a producer
    manifest is given, checked against it first."""

    def __init__(self):
        self.sha: dict[str, str] = {}

    def bytes(self, path: Path, expected: str | None = None, producer: str | None = None) -> bytes:
        rel = _rel(path)
        if producer is not None and expected is None:
            raise wp2.DataIntegrityError(f"{rel} is not listed in the {producer} manifest")
        if not Path(path).is_file():
            raise wp2.DataIntegrityError(f"{rel} is missing")
        data = Path(path).read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        if producer is not None and sha != expected:
            raise wp2.DataIntegrityError(f"{rel} differs from the SHA-256 recorded by {producer}")
        self.sha[rel] = sha
        return data

    def json(self, path: Path, expected: str | None = None, producer: str | None = None):
        return json.loads(self.bytes(path, expected, producer).decode("utf-8"))

    def npy(self, path: Path, expected: str | None, producer: str) -> np.ndarray:
        return np.load(io.BytesIO(self.bytes(path, expected, producer)), allow_pickle=False)

    def npz(self, path: Path, expected: str | None, producer: str) -> dict:
        with np.load(io.BytesIO(self.bytes(path, expected, producer)), allow_pickle=False) as z:
            return {k: z[k] for k in z.files}


# --- comparisons -----------------------------------------------------------------------------------

def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x)


def _same(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    return a == b


def compare_keyed(new: list[dict], old: list[dict], keys: tuple[str, ...], fields: tuple[str, ...],
                  expected_keys: set | None = None) -> dict:
    """Records matched on `keys`: per field `n_diff` and `max_abs_diff` (over pairs of finite
    numbers; None if there are none), `n_matched`, `n_missing_new` (old keys without a new record),
    `n_missing_old` (new keys without an old record), `complete_coverage` and up to `MAX_LISTED`
    differing keys. With `expected_keys`, `old` is filtered to them and coverage is complete only if
    the new key set and the filtered old key set both equal `expected_keys`; without, only if no key
    is missing on either side. Duplicate keys make coverage incomplete. None equals only None;
    bools compare as values."""
    key = lambda r: tuple(r.get(k) for k in keys)  # noqa: E731
    new_keys, old_keys = [key(r) for r in new], [key(r) for r in old]
    new_by = dict(zip(new_keys, new))
    old_by = {k: r for k, r in zip(old_keys, old) if expected_keys is None or k in expected_keys}
    n_dup = (len(new_keys) - len(new_by)) + (len([k for k in old_keys if k in old_by]) - len(old_by))
    matched = [k for k in new_by if k in old_by]  # old_by is already filtered to expected_keys
    out: dict = {}
    differing = []
    for f in fields:
        diff = [k for k in matched if not _same(new_by[k].get(f), old_by[k].get(f))]
        nums = [abs(new_by[k][f] - old_by[k][f]) for k in matched
                if _is_num(new_by[k].get(f)) and _is_num(old_by[k].get(f))]
        out[f] = {"n_diff": len(diff), "max_abs_diff": float(max(nums)) if nums else None}
    for k in matched:
        changed = [f for f in fields if not _same(new_by[k].get(f), old_by[k].get(f))]
        if changed and len(differing) < MAX_LISTED:
            differing.append({"key": list(k), "fields": changed})
    n_missing_new = sum(k not in new_by for k in old_by)
    n_missing_old = sum(k not in old_by for k in new_by)
    if expected_keys is None:
        complete = n_missing_new == 0 and n_missing_old == 0
    else:
        complete = set(new_by) == set(expected_keys) and set(old_by) == set(expected_keys)
    out.update(n_matched=len(matched), n_missing_new=n_missing_new, n_missing_old=n_missing_old,
               n_duplicate_keys=n_dup, complete_coverage=bool(complete and n_dup == 0), differing=differing,
               differing_listed_max=MAX_LISTED)
    return out


def _exact(cmp: dict, fields: tuple[str, ...]) -> bool:
    return cmp["complete_coverage"] and all(cmp[f]["n_diff"] == 0 for f in fields)


def _nan(x):
    if isinstance(x, (list, tuple)):
        return [_nan(v) for v in x]
    return np.nan if x is None else x


def _close(a, b) -> tuple[bool, float | None]:
    """(allclose with equal NaN positions, max abs diff over pairs of finite values)."""
    if a is None or b is None:
        return False, None
    try:
        x, y = np.asarray(_nan(a), dtype=float), np.asarray(_nan(b), dtype=float)
    except (TypeError, ValueError):
        return False, None
    if x.shape != y.shape:
        return False, None
    both = np.isfinite(x) & np.isfinite(y)
    mad = float(np.abs(x - y)[both].max()) if both.any() else None
    return bool(np.allclose(x, y, equal_nan=True)), mad


def _config(c):
    return None if c is None else [float(v) for v in c]


def _get(tree, path: tuple):
    for k in path:
        tree = tree.get(k) if isinstance(tree, dict) else None
    return tree


def _zero(x) -> bool:
    if isinstance(x, bool):
        return False
    if isinstance(x, int):
        return x == 0
    if isinstance(x, dict):
        return bool(x) and all(_zero(v) for v in x.values())
    return False


def _identity_ok(block: dict) -> bool:
    """Spec ambiguity 23: every solve-based and code-based count present and zero."""
    sham, code = block.get("sham_mismatch"), block.get("code_mismatch")
    if not isinstance(sham, dict) or not isinstance(code, dict):
        return False
    shape = (set(sham) == {"level1_B1", "levels_B"} and set(code) == {"level1_B1", "levels_B", "level1_noop_D"}
             and isinstance(sham["levels_B"], dict) and isinstance(code["levels_B"], dict)
             and set(sham["levels_B"]) == E2_LEVEL_KEYS and set(code["levels_B"]) == E2_LEVEL_KEYS)
    stored_ok = "level1_noop_mismatch_stored" not in block or _zero(block["level1_noop_mismatch_stored"])
    return shape and stored_ok and _zero(block.get("level1_noop_mismatch")) and _zero(sham) and _zero(code)


# --- parts -----------------------------------------------------------------------------------------

def records_part(rd: Reader, tag_commit: str | None) -> tuple[dict, dict]:
    rec_dir = wp2.paths(ROLE)[0] / "runs"
    records, statuses = {}, {}
    for runner in RUNNERS:
        rec = rd.json(rec_dir / f"{runner}.json")
        ok, reasons = wp2.valid_record(rec, tag_commit)
        if rec.get("runner") != runner or rec.get("role") != ROLE:
            reasons.append("not_the_dry_record_of_this_runner")
        if rec.get("valid") is not True:
            reasons.append("record_not_valid")
        reasons = list(dict.fromkeys(reasons))
        records[runner] = rec
        statuses[runner] = {"status": rec.get("status"), "valid": not reasons, "reasons": reasons,
                            "commit": (rec.get("code") or {}).get("commit")}
    return records, statuses


def e2_parts(e2: dict, e2_rec: dict, pilot2: dict, full: dict, ids: list[str]) -> dict:
    exp_records = {(pid, lv, pol, dose, seed) for pid in ids for lv, doses in CONFIG_DOSES.items()
                   for pol in POLICIES for dose in doses for seed in e2p2.SEEDS_P2}
    fields = tuple(f for f in E2_FIELDS if f not in E2_KEYS)
    rec_cmp = compare_keyed(e2.get("records", []), pilot2.get("records", []), E2_KEYS, fields, exp_records)
    exp_l1 = {(pid, v) for pid in ids for v in range(N_LEVEL1_VALUES)}
    l1_cmp = compare_keyed(e2.get("level1", []), full.get("level1", []), L1_KEYS, L1_FIELDS, exp_l1)
    exp_base = {(pid,) for pid in ids}
    base = {name: compare_keyed(e2.get("base", []), ref.get("base", []), ("puzzle_id",), BASE_FIELDS, exp_base)
            for name, ref in (("pilot2", pilot2), ("level1_full_batch", full))}
    out_block = {"level1_noop_mismatch": e2p2.level1_noop_mismatch(e2.get("level1", []), e2.get("base", [])),
                 "level1_noop_mismatch_stored": e2.get("level1_noop_mismatch"),
                 "sham_mismatch": e2p2.sham_mismatch_counts(e2), "code_mismatch": e2.get("code_mismatch")}
    rec_block = {k: e2_rec.get(k) for k in ("level1_noop_mismatch", "sham_mismatch", "code_mismatch")}
    return {
        "e2_records": {**rec_cmp, "ok": _exact(rec_cmp, fields)},
        "e2_level1": {**l1_cmp, "ok": _exact(l1_cmp, L1_FIELDS)},
        "e2_base": {**base, "ok": all(_exact(c, BASE_FIELDS) for c in base.values())},
        "e2_identity": {"output": out_block, "record": rec_block,
                        "ok": _identity_ok(out_block) and _identity_ok(rec_block)},
    }


def e1_part(e1: dict, pilot2: dict, ids: list[str]) -> dict:
    new = [{"puzzle_id": r.get("puzzle_id"), "solve": r.get("solve")} for r in e1.get("records", [])]
    old = [{"puzzle_id": b.get("puzzle_id"), "solve": b.get("solve_A")} for b in pilot2.get("base", [])]
    cmp = compare_keyed(new, old, ("puzzle_id",), ("solve",), {(pid,) for pid in ids})
    ids_match = e1.get("ids") == ids
    return {**cmp, "ids_match_e2": ids_match, "ok": ids_match and _exact(cmp, ("solve",))}


def _fit_cmp(new: dict | None, old: dict | None, reference: str) -> dict:
    if new is None or old is None:
        return {"reference": reference, "missing": "dry" if new is None else "reference", "ok": False}
    close, mad = _close(new.get("per_puzzle"), old.get("per_puzzle"))
    cfg_equal = _config(new.get("config")) == _config(old.get("config"))
    return {"reference": reference, "config": new.get("config"), "config_reference": old.get("config"),
            "config_equal": cfg_equal, "per_puzzle_allclose": close, "max_abs_diff": mad,
            "ok": cfg_equal and close}


def _depth_cmp(new: dict, old) -> dict:
    out, ok = {}, isinstance(old, dict)
    for c in DEPTH_CLASSES:
        n, o = new[c], (old or {}).get(c) or {}
        b_close, b_mad = _close([n["brier"]], [o.get("brier")]) if "brier" in o else (False, None)
        s_close, s_mad = _close(n["brier_per_seed"], o.get("brier_per_seed"))
        sizes = n["n_cells"] == o.get("n_cells") and n["n_puzzles"] == o.get("n_puzzles")
        out[c] = {"sizes_equal": sizes, "brier_allclose": b_close, "brier_per_seed_allclose": s_close,
                  "max_abs_diff": max((d for d in (b_mad, s_mad) if d is not None), default=None),
                  "ok": sizes and b_close and s_close}
        ok = ok and out[c]["ok"]
    return {**out, "ok": ok}


def e3_part(rd: Reader, fits: dict, refs: dict, score: dict, out_dir: Path) -> dict:
    fit_rows = {}
    for name, (ref_file, path) in E3_MAP.items():
        stage, fit = name.split(".")
        fit_rows[name] = _fit_cmp(_get(fits, ("stages", stage, fit)), _get(refs[ref_file], path),
                                  f"{REFERENCES[ref_file]} " + ".".join(path))
    depth_ref = _get(refs["probes.json"], ("stages", "depth_L06")) or {}
    depth = {}
    for key, name in DEPTH_MAP.items():
        stage, fit = name.split(".")
        files = _get(fits, ("files", stage, fit)) or {}
        pred_keys = [k for k in files if k.startswith("preds/")]
        if len(pred_keys) != 1:
            raise wp2.DataIntegrityError(f"e3_fits.json files of {name} list {len(pred_keys)} prediction files")
        preds = rd.npz(out_dir / pred_keys[0], files[pred_keys[0]], "e3_fits.json files")
        new = depth_breakdown_seeds([preds[f"seed{s}"] for s in SEEDS], score["mask"], score["empty"], score["depth"])
        depth[key] = {"fit": name, **_depth_cmp(new, depth_ref.get(key))}
    depth["ok"] = all(depth[k]["ok"] for k in DEPTH_MAP)
    score_ids_ok = (fits.get("score_ids") == score["ids"] == refs["probes.json"].get("val_ids")
                    == refs["wholelayer.json"].get("val_ids"))
    differing = sorted(n for n, r in fit_rows.items() if not r["ok"])
    return {"fits": fit_rows, "depth": depth, "new_fits": sorted(NEW_FITS), "score_ids_equal_val_ids": score_ids_ok,
            "differing": differing, "ok": score_ids_ok and not differing and depth["ok"]}


def equivariance_part(eq: dict, lock: dict) -> dict:
    config = {k: eq.get(k) == lock.get(k) for k in EQUIV_CONFIG}
    config["probe_config"] = _config(_get(eq, ("probe", "config"))) == _config(_get(lock, ("probe", "config")))
    arrays = {}
    for field in EQUIV_ARRAYS:
        a, b = eq.get(field), lock.get(field)
        if isinstance(a, dict) or isinstance(b, dict):
            if not (isinstance(a, dict) and isinstance(b, dict) and set(a) == set(b)):
                arrays[field] = {"allclose": False, "max_abs_diff": None, "kinds_equal": False}
                continue
            per = {k: _close(a[k], b[k]) for k in sorted(a)}
            mads = [m for _, m in per.values() if m is not None]
            arrays[field] = {"allclose": all(c for c, _ in per.values()), "max_abs_diff": max(mads, default=None),
                             "per_kind": {k: {"allclose": c, "max_abs_diff": m} for k, (c, m) in per.items()}}
        else:
            close, mad = _close(a, b)
            arrays[field] = {"allclose": close, "max_abs_diff": mad}
    lock_acc = lock.get("acceptable")
    dev = eq.get("deviation") if isinstance(eq.get("deviation"), dict) else {}
    share = {"at_0.0116": eq.get("share_within"),
             "at_lock_value": ({k: float(np.mean(np.asarray(_nan(v), float) <= lock_acc)) for k, v in dev.items()}
                               if _is_num(lock_acc) else None),
             "lock_value": lock_acc, "lock_share_within": lock.get("share_within")}
    acceptable_ok = eq.get("acceptable") == ACCEPTABLE
    return {"config_equal": config, "acceptable_fixed": acceptable_ok, "arrays": arrays, "share_within": share,
            "ok": all(config.values()) and acceptable_ok and all(v["allclose"] for v in arrays.values())}


def extraction_part(extract_rec: dict) -> dict:
    m = extract_rec.get("matches_e3prep")
    expected = {Path(n).stem for n in EXTRACT_ARRAYS}
    ok = (isinstance(m, dict) and set(m) == expected
          and all(isinstance(v, dict) and v.get("equal") is True for v in m.values()))
    return {"matches_e3prep": m, "ok": ok}


def dry_evaluate_part(rd: Reader, exp: Path, raw: Path, tag_commit: str | None, outputs: list[str]) -> dict:
    """The dry `wp2_evaluate.py` run (runbook: it must exit 0 before this check): `results.json` and
    `report.md` exist, `results.json` has role dry and `code_state` at the tag commit and clean, every
    recorded input under the dry directories still has its recorded SHA-256 (`changed`), and every
    dry output this check reads (`outputs`, ROOT-relative, already hashed by `rd`) is recorded with
    that hash (`not_recorded`)."""
    files = [exp / "results.json", exp / "report.md"]
    missing = [_rel(f) for f in files if not f.is_file()]
    if missing:
        return {"missing": missing, "ok": False}
    res = rd.json(files[0])
    rd.bytes(files[1])
    code = res.get("code_state") if isinstance(res.get("code_state"), dict) else {}
    inputs = res.get("inputs") if isinstance(res.get("inputs"), dict) else {}
    dry_dirs = tuple(f"{_rel(d)}/" for d in (exp, raw))
    changed = sorted(rel for rel, sha in inputs.items() if rel.startswith(dry_dirs)
                     and (not (wp2.ROOT / rel).is_file() or wp2.file_sha256(wp2.ROOT / rel) != sha))
    not_recorded = sorted(rel for rel in outputs if inputs.get(rel) != rd.sha[rel])
    state = {"role_dry": res.get("role") == ROLE,
             "tag_commit": tag_commit is not None and code.get("commit") == tag_commit,
             "clean": code.get("dirty") is False}
    return {"missing": [], "code_state": code, **state, "n_inputs_checked": sum(r.startswith(dry_dirs) for r in inputs),
            "changed": changed, "not_recorded": not_recorded,
            "ok": all(state.values()) and not changed and not not_recorded}


def probe_inputs_part(e3_rec: dict) -> tuple[dict, dict]:
    """The PROBE entries of the dry e3 record's `inputs`, as ROOT-relative paths with SHA-256 only."""
    files = _get(e3_rec, ("inputs", "files")) or {}
    base = (wp2.ROOT / "runs" / "e3prep").relative_to(wp2.ROOT).as_posix()
    expected = [f"{s}/{n}" for s in ("probe_train", "probe_val") for n in PROBE_INPUT_FILES]
    snapshot = {f"{base}/{k}": files[k] for k in expected if k in files}
    missing = [f"{base}/{k}" for k in expected if k not in files]
    changed = [rel for rel, sha in snapshot.items()
               if not (wp2.ROOT / rel).is_file() or wp2.file_sha256(wp2.ROOT / rel) != sha]
    return {"n": len(snapshot), "missing": missing, "changed": changed, "ok": not missing and not changed}, snapshot


# --- report ----------------------------------------------------------------------------------------

def report(c: dict) -> str:
    cmp = c["comparisons"]
    L = ["# WP2 dry-run check", "", wp2.DRY_NOTE, "",
         f"- date: {c['date']}", f"- code commit: {c['code'].get('commit')} (dirty: {c['code'].get('dirty')})",
         f"- tag commit: {c['freeze_state'].get('tag_commit')}; frozen: {c['freeze_state'].get('frozen')}",
         f"- check state (frozen, clean, unchanged during the check): {c['check_state']['ok']}",
         f"- technical_success: **{str(c['technical_success']).lower()}**", "",
         "## Run records", "", "| runner | status | valid | reasons |", "|---|---|---|---|"]
    L += [f"| {r} | {s['status']} | {s['valid']} | {', '.join(s['reasons']) or '-'} |" for r, s in c["records"].items()]
    L += ["", "## Comparisons", "", "| part | ok | detail |", "|---|---|---|"]

    def keyed(x, fields):
        n_diff = sum(x[f]["n_diff"] for f in fields)
        return f"matched {x['n_matched']}, differing values {n_diff}, complete coverage {x['complete_coverage']}"

    details = {
        "dry_ids": f"{cmp['dry_ids']['n']} ids, first CAL ids in both E2 references",
        "e2_records": keyed(cmp["e2_records"], tuple(f for f in E2_FIELDS if f not in E2_KEYS)),
        "e2_level1": keyed(cmp["e2_level1"], L1_FIELDS),
        "e2_base": "; ".join(f"{k}: {keyed(cmp['e2_base'][k], BASE_FIELDS)}" for k in ("pilot2", "level1_full_batch")),
        "e2_identity": "solve-based and code-based counts in e2.json and the run record",
        "e3": f"{len(E3_MAP)} mapped fits, differing: {', '.join(cmp['e3']['differing']) or 'none'}; "
              f"depth ok {cmp['e3']['depth']['ok']}",
        "equivariance": "deviation, seed_noise, brier, brier_original against experiments/lock/equivariance_l12.json",
        "e1": keyed(cmp["e1"], ("solve",)),
        "extraction": "matches_e3prep of the e3_extract record",
        "probe_inputs": f"{cmp['probe_inputs']['n']} PROBE files; changed: "
                        f"{', '.join(cmp['probe_inputs']['changed']) or 'none'}",
        "dry_evaluate": ("missing: " + ", ".join(cmp["dry_evaluate"]["missing"]) if cmp["dry_evaluate"]["missing"]
                         else f"results.json at the tag commit {cmp['dry_evaluate']['tag_commit']}, clean "
                              f"{cmp['dry_evaluate']['clean']}, role dry {cmp['dry_evaluate']['role_dry']}; changed "
                              f"inputs: {', '.join(cmp['dry_evaluate']['changed']) or 'none'}; unrecorded outputs: "
                              f"{', '.join(cmp['dry_evaluate']['not_recorded']) or 'none'}"),
    }
    L += [f"| {k} | {cmp[k]['ok']} | {details[k]} |" for k in cmp]
    L += ["", f"New fits without a pre-lock reference: {', '.join(cmp['e3']['new_fits'])}.", ""]
    return "\n".join(L)


# --- run -------------------------------------------------------------------------------------------

def run(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="WP2 dry-run comparison").parse_args(sys.argv[1:] if argv is None else argv)
    check_md = wp2.DRY_CHECK.with_name("check.md")
    wp2.DRY_CHECK.unlink(missing_ok=True)  # no stale approval survives a refusal
    check_md.unlink(missing_ok=True)
    torch.use_deterministic_algorithms(True)  # before every environment_record()
    freeze, code, environment = wp2.freeze_state(), wp2.code_state(), wp2.environment_record()
    exp, raw = wp2.paths(ROLE)
    rd = Reader()

    records, statuses = records_part(rd, freeze.get("tag_commit"))
    dry_records = dict(rd.sha)
    outs = lambda runner, name: (records[runner].get("outputs") or {}).get(name)  # noqa: E731
    e2 = rd.json(raw / "e2.json", outs("e2", "e2.json"), "e2 run record")
    rd.bytes(raw / "e2" / "parts.json", outs("e2", "parts.json"), "e2 run record")
    e1 = rd.json(raw / "e1.json", outs("e1", "e1.json"), "e1 run record")
    fits = rd.json(exp / "e3_fits.json", outs("e3", "e3_fits.json"), "e3 run record")
    rd.bytes(exp / "e3_budget.json", outs("e3", "e3_budget.json"), "e3 run record")
    equiv = rd.json(exp / "equivariance.json", outs("equiv", "equivariance.json"), "equiv run record")
    refs = {name: rd.json(wp2.ROOT / rel) for name, rel in REFERENCES.items()}
    eval_outputs = [_rel(p) for p in (raw / "e1.json", raw / "e2.json", exp / "e3_fits.json", exp / "e3_budget.json",
                                      exp / "equivariance.json")]
    dry_eval = dry_evaluate_part(rd, exp, raw, freeze.get("tag_commit"), eval_outputs)
    compared = {_rel(p): rd.sha[_rel(p)] for p in (
        raw / "e2.json", raw / "e1.json", raw / "e2" / "parts.json", exp / "e3_fits.json", exp / "e3_budget.json",
        exp / "equivariance.json", *(wp2.ROOT / rel for rel in REFERENCES.values()))}
    compared.update({rel: rd.sha[rel] for rel in (_rel(exp / "results.json"), _rel(exp / "report.md"))
                     if rel in rd.sha})

    manifest = records["e3_extract"].get("score_manifest") or {}
    score_dir = raw / "e3data" / "score"
    score = {"ids": rd.json(score_dir / "ids.json", manifest.get("ids.json"), "e3_extract score_manifest")}
    for name in ("mask", "empty", "depth"):
        score[name] = rd.npy(score_dir / f"{name}.npy", manifest.get(f"{name}.npy"), "e3_extract score_manifest")

    pilot2, full = refs["pilot2"], refs["level1_full_batch"]
    ids = e2.get("ids") or []
    ids_ok = (len(ids) == wp2.N_DRY and len(set(ids)) == wp2.N_DRY and ids == (full.get("ids") or [])[: wp2.N_DRY]
              and ids == [b.get("puzzle_id") for b in pilot2.get("base", [])][: wp2.N_DRY])
    probe, probe_snapshot = probe_inputs_part(records["e3"])
    comparisons = {
        "dry_ids": {"n": len(ids), "ok": ids_ok},
        **e2_parts(e2, records["e2"], pilot2, full, ids),
        "e3": e3_part(rd, fits, refs, score, raw / "e3"),
        "equivariance": equivariance_part(equiv, refs["equivariance_l12"]),
        "e1": e1_part(e1, pilot2, ids),
        "extraction": extraction_part(records["e3_extract"]),
        "probe_inputs": probe,
        "dry_evaluate": dry_eval,
    }
    torch.use_deterministic_algorithms(True)
    freeze_end, code_end = wp2.freeze_state(), wp2.code_state()
    state = {"frozen": freeze.get("frozen") is True and freeze_end.get("frozen") is True,
             "clean": code.get("dirty") is False and code_end.get("dirty") is False,
             "unchanged": code_end == code and freeze_end == freeze}
    state["ok"] = all(state.values())
    success = (state["ok"] and all(s["valid"] for s in statuses.values())
               and all(p["ok"] for p in comparisons.values()))
    check = {
        "note": wp2.DRY_NOTE, "date": time.strftime("%Y-%m-%d"), "code": code, "freeze_state": freeze,
        "code_end": code_end, "freeze_state_end": freeze_end, "check_state": state, "environment": environment, "records": statuses, "comparisons": comparisons,
        "technical_success": bool(success),
        "snapshot": {"dry_records": dry_records, "compared": compared, "probe_inputs": probe_snapshot},
    }
    check = json.loads(json.dumps(check))
    wp2.atomic_json(wp2.DRY_CHECK, check)
    wp2.atomic_write(check_md, report(check))
    wp2.status_line(runner=NAME, complete=True, valid=bool(success))
    return 0 if success else 1


def main(argv: list[str] | None = None) -> None:
    try:
        code = run(argv)
    except wp2.DataIntegrityError as e:
        sys.exit(f"{NAME}: {e}")
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
