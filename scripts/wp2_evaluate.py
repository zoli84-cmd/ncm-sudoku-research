"""WP2 pre-written single-look evaluation (plan v3.7 §6, §7.3-§7.4, §8.2-§8.4, §10, §11, §13; D76-D79;
WP2 plan spec ambiguities 2, 3, 7-10, 18, 19, 22-24).

Usage: uv run --locked python scripts/wp2_evaluate.py --role test|dry

Single look: the TEST role refuses to run (named exit, nothing written) if
`experiments/wp2/test/results.json` or `report.md` already exists; the dry role may rerun.

Reads only raw outputs of the five WP2 runners and never loads the model:
`runs/wp2/<role>/{e1.json, e2.json, e2/diag/*.npz, e3/preds/*.npz, e3data/score/*.npy}`,
`experiments/wp2/<role>/{e3_fits.json, e3_budget.json, equivariance.json}`, the role's puzzles
(`wp2.load_role`, only for the empty/given split of the E2 diagnostics; ids must equal `e2.json`)
and, for the configuration-difference table only, `experiments/e3prep/{probes.json, wholelayer.json}`.

Validity gate, before any statistic: every run record (`e3_extract`, `e3`, `equiv`, `e2`, `e1`) must
exist and pass `wp2.valid_record` at the current tag commit; any reason exits naming the runner and
the reasons. The one exception is an E2 record whose only reason is `identity-failure` (spec
ambiguity 23): the evaluation continues but computes no E2 interval, TOST, AUC or reading; every
E2 entry carries the identity-failure status block instead. The TEST role also requires
`wp2.freeze_state()["frozen"]` now, the score set's ids equal to the TEST ids and the
equivariance ids equal to the first `N_EQUIV` score ids. Every input file is checked against the manifest of the record
that produced it (run record `outputs`, `score_manifest`, `e3_fits.json` `files`, `e2.json`
`diag_files`) before it is read; a mismatch exits naming the file.

Statistics come only from `wp2eval` (`contrast`, `tost`, `h1_block`, `auc_frozen`,
`e2_descriptive`, `select_readings`) and `e2p2` (`puzzle_values`, `dose_nodes`); `summarize2` and
`auc_pair` are never called.

Outputs: `experiments/wp2/<role>/results.json` and `report.md` (UTF-8); the report is rendered
before either file is written, so a failure leaves neither behind. E2 diagnostics (D78) are
descriptive: level-1 rows are weighted by the policy weights over non-no-op rows, configuration
rows are averaged over eligible seeds within puzzle, then over puzzles.
"""

import argparse
import json
import math
import sys
import time
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

import ncm_sudoku.e2p2 as e2p2
import ncm_sudoku.wp2eval as wp2eval
from ncm_sudoku import wp2
from ncm_sudoku.e1 import e1_table
from ncm_sudoku.e2 import POLICIES
from ncm_sudoku.e3controls import unit_digit_labels, unit_metrics
from ncm_sudoku.e3metrics import depth_breakdown_seeds, depth_label_rates, secondary_metrics
from ncm_sudoku.probes import SEEDS, brier_per_puzzle
from ncm_sudoku.wp2e3 import STAGE_FITS, STAGES

NAME = "wp2_evaluate"
RUNNERS = ("e3_extract", "e3", "equiv", "e2", "e1")
N_BOOT = wp2eval.N_BOOT
ALPHA = 0.05  # per side, theta2' and theta_T TOST (§11.4, §8.3)
OUTPUT_FILES = ("results.json", "report.md")
SCORE_FILES = ("ids.json", "puzzles.npy", "mask.npy", "empty.npy", "depth.npy")
N_EQUIV = 200  # wp2_equiv.py: equivariance.json ids are the first N_EQUIV score ids
TEST_NOTE = "WP2 confirmatory evaluation on TEST (plan v3.7); single look, read only after all TEST runs are complete"
DEVIATION_REQUIRED = "a logged deviation (DECISIONS.md) is required before any E2 inference"
CI95_BOUND_LABEL = ("individual-level (0.95) rare-event bound; the 98.33% family interval is the inferential one")
CI95_LABEL = "individual-level 95% interval; the 98.33% family interval is the inferential one"
DISCLOSURE_7_4 = (
    "Plan §7.4 reading (D78): full state tensors are not saved. Cumulative-state distances and intermediate "
    "decodings exist only for the primary configurations (every level-1 value, weighted under the frequency and "
    "the uniform policy; level 11, frequency policy, dose 1, seeds 0-2). Every other configuration has the "
    "cell-level change vectors of C and D against A, the per-later-level D code changes and the replacement "
    "diagnostics only. This follows §7.4's closing sentence (\"We report if only the final sensitivity is "
    "estimable\") and is a reading, not a deviation.")
CLAIM_BOUNDARIES = (
    "Results are stated conditionally on checkpoint and intervention policy. The main risks — distribution shift "
    "after code replacement, teacher/generated conflation, data overlap, readout capacity, format errors, and post "
    "hoc target selection — appear in the final report together with their assigned controls. No single diagnostic "
    "proves in general that a patch is \"in-distribution\".")
EQUIV_BOTH_NOTE = ("Equivalence also held: the 96.67% TOST interval lies inside (-0.01, 0.01); §8.3: both readings "
                   "can hold at once.")
WL_REF, PC_REF = "wl_L06.generated", "pc_L06.linear"
E3_MAIN = (  # (row, group, reference): relative differences only within one construction (spec ambiguity 2)
    ("wl_L06.generated", "whole_layer", None), ("wl_L06.permuted", "whole_layer", WL_REF),
    ("wl_L06_controls.random", "whole_layer", WL_REF), ("wl_L06_controls.label_permuted", "whole_layer", WL_REF),
    ("wl_teacher_L06.teacher", "whole_layer", WL_REF), ("wl_teacher_L12.teacher", "whole_layer", "wl_L12.generated"),
    ("raw_projected.linear", "whole_layer", WL_REF), ("raw_unprojected.linear", "whole_layer", WL_REF),
    ("pc_L06.linear", "per_cell", None), ("pc_L06.mlp", "per_cell", PC_REF),
    ("controls.raw_linear", "per_cell", PC_REF), ("controls.raw_mlp", "per_cell", "pc_L06.mlp"),
    ("controls.peer_counts_linear", "per_cell", PC_REF), ("controls.surface_linear", "per_cell", PC_REF),
    ("controls.permuted_linear", "per_cell", PC_REF), ("controls.random_linear", "per_cell", PC_REF),
    ("controls.label_permuted_linear", "per_cell", PC_REF), ("controls.teacher_L02_linear", "per_cell", "pc_L02.linear"),
    ("controls.teacher_L06_linear", "per_cell", PC_REF), ("controls.teacher_L12_linear", "per_cell", "pc_L12.linear"),
    ("controls.rule", "label_free", None), ("controls.marginal", "label_free", None),
)
THETA1 = {  # (permuted, generated)
    "H1": ("wl_L06.permuted", "wl_L06.generated"),
    "theta1_wl.L02": ("wl_L02.permuted", "wl_L02.generated"),
    "theta1_wl.L12": ("wl_L12.permuted", "wl_L12.generated"),
    "theta1_pc.L02": ("pc_L02.permuted", "pc_L02.linear"),
    "theta1_pc.L06": ("controls.permuted_linear", "pc_L06.linear"),
    "theta1_pc.L12": ("pc_L12.permuted", "pc_L12.linear"),
}
DEPTH_FITS = ("wl_L06.generated", "pc_L06.linear", "raw_unprojected.linear", "raw_projected.linear")
PRIMARY_DIAG = ("level1-frequency", "level1-uniform", "L11-frequency-d1")


# --- inputs -----------------------------------------------------------------------------------

def _read(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _rel(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(Path(wp2.ROOT).resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


class Inputs:
    """SHA-256 of every file read, each checked against its producer's manifest first."""

    def __init__(self):
        self.sha: dict[str, str] = {}

    def check(self, path: Path, expected: str | None, producer: str) -> Path:
        rel = _rel(path)
        if expected is None:
            sys.exit(f"{NAME}: {rel} is not listed in the {producer} manifest")
        if not Path(path).is_file():
            sys.exit(f"{NAME}: {rel} is missing ({producer})")
        sha = wp2.file_sha256(path)
        if sha != expected:
            sys.exit(f"{NAME}: {rel} differs from the SHA-256 recorded by {producer}")
        self.sha[rel] = sha
        return Path(path)

    def unrecorded(self, path: Path) -> Path:
        if not Path(path).is_file():
            sys.exit(f"{NAME}: {_rel(path)} is missing")
        self.sha[_rel(path)] = wp2.file_sha256(path)
        return Path(path)

    def json(self, path: Path, expected: str | None, producer: str):
        return _read(self.check(path, expected, producer))

    def npz(self, path: Path, expected: str | None, producer: str) -> dict:
        with np.load(self.check(path, expected, producer), allow_pickle=False) as z:
            return {k: z[k] for k in z.files}

    def npy(self, path: Path, expected: str | None, producer: str) -> np.ndarray:
        return np.load(self.check(path, expected, producer), allow_pickle=False)


def gate(role: str, freeze: dict) -> tuple[dict, dict, bool]:
    """Run records of the role; exits unless every one is valid at the tag commit (E2 identity
    failure excepted). Returns (records, reasons per runner, E2 identity failure)."""
    if role == "test" and not freeze.get("frozen"):
        sys.exit(f"{NAME}: the TEST role requires the code freeze (frozen) now; state: {freeze}")
    rec_dir = wp2.paths(role)[0] / "runs"
    records, reasons, identity = {}, {}, False
    for runner in RUNNERS:
        p = rec_dir / f"{runner}.json"
        if not p.is_file():
            sys.exit(f"{NAME}: no {runner} run record at {p}")
        rec = _read(p)
        if rec.get("runner") != runner or rec.get("role") != role:
            sys.exit(f"{NAME}: {p} is not the {role} {runner} run record")
        ok, why = wp2.valid_record(rec, freeze.get("tag_commit"))
        if not ok:
            if runner == "e2" and why == ["identity-failure"]:
                identity = True
            else:
                sys.exit(f"{NAME}: the {runner} run record is not valid: {why}")
        records[runner], reasons[runner] = rec, why
    return records, reasons, identity


def single_look(role: str, exp: Path) -> None:
    """TEST role: refuses to run if a results.json or report.md already exists (single look); dry may rerun."""
    if role != "test":
        return
    for name in OUTPUT_FILES:
        if (exp / name).exists():
            sys.exit(f"{NAME}: the TEST evaluation is single-look and {_rel(exp / name)} already exists; "
                     "nothing was written")


def _outputs(rec: dict, name: str) -> str | None:
    return (rec.get("outputs") or {}).get(name)


# --- helpers ----------------------------------------------------------------------------------

def _plain(x):
    """JSON-ready: numpy scalars and arrays to Python, tuples to lists, NaN/inf to None."""
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if isinstance(x, np.ndarray):
        return _plain(x.tolist())
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return float(x) if math.isfinite(float(x)) else None
    return x


def _mean(v) -> float | None:
    v = np.asarray(v, dtype=float)
    v = v[~np.isnan(v)]
    return float(v.mean()) if v.size else None


class E3:
    """Accessors for the E3 fits on the score set; predictions are verified against `e3_fits.json` files."""

    def __init__(self, fits: dict, out: Path, score: dict, inputs: Inputs):
        self.fits, self.out, self.score, self.inputs = fits, out, score, inputs
        self.ids = score["ids"]
        self.n = len(self.ids)
        self.empty = np.asarray(score["empty"], bool)
        self.pz = np.nonzero(self.empty)[0]
        self.y = np.asarray(score["mask"])[self.empty].astype(np.float64)
        self._preds: dict[str, dict] = {}

    def summary(self, name: str) -> dict:
        stage, fit = name.split(".")
        try:
            return self.fits["stages"][stage][fit]
        except KeyError:
            sys.exit(f"{NAME}: e3_fits.json has no {name} fit")

    def per_puzzle(self, name: str) -> np.ndarray:
        return np.asarray(self.summary(name)["per_puzzle"], dtype=float)

    def brier(self, name: str) -> float | None:
        return _mean(self.per_puzzle(name))

    def preds(self, name: str) -> dict:
        stage, fit = name.split(".")
        files = ((self.fits.get("files") or {}).get(stage) or {}).get(fit) or {}
        keys = [k for k in files if k.startswith("preds/")]
        if len(keys) != 1:
            sys.exit(f"{NAME}: e3_fits.json files of {name} list {len(keys)} prediction files")
        if keys[0] not in self._preds:
            self._preds[keys[0]] = self.inputs.npz(self.out / keys[0], files[keys[0]], "e3_fits.json files")
        return self._preds[keys[0]]

    def seed_preds(self, name: str) -> list[np.ndarray]:
        p = self.preds(name)
        return [p[f"seed{s}"] for s in SEEDS]

    def seed_briers(self, name: str) -> list[np.ndarray]:
        return [brier_per_puzzle(p, self.y, self.pz, self.n) for p in self.seed_preds(name)]

    def diff(self, a: str, b: str) -> dict[str, float]:
        return wp2eval.paired_diff(self.per_puzzle(a), self.per_puzzle(b), self.ids)


# --- statistics -------------------------------------------------------------------------------

def _label_primary(x: dict) -> dict:
    x["ci95_label"] = CI95_BOUND_LABEL if x["ci95"]["method"] == "bound" else CI95_LABEL
    return x


def _sec(e3: E3, a: str, b: str) -> dict:
    return {"a": a, "b": b, "quantity": f"{a} minus {b}",
            **wp2eval.contrast(e3.diff(a, b), False, n_boot=N_BOOT)}


def identity_block(e2: dict) -> dict:
    return {"status": "identity-failure", "deviation_required": DEVIATION_REQUIRED,
            "sham_mismatch": e2p2.sham_mismatch_counts(e2), "level1_noop_mismatch": e2.get("level1_noop_mismatch"),
            "code_mismatch": e2.get("code_mismatch")}


def statistics(e2: dict, e3: E3, identity: bool) -> tuple[dict, dict, dict]:
    """(primary, secondary, auc)."""
    perm, gen = THETA1["H1"]
    h1 = wp2eval.h1_block(e3.per_puzzle(perm), e3.per_puzzle(gen), e3.ids, e3.seed_briers(perm),
                          e3.seed_briers(gen), n_boot=N_BOOT)
    primary = {"H1": _label_primary({"quantity": f"theta1 = {perm} minus {gen} (level 6, whole-layer)", **h1})}
    d_t = e3.diff("wl_teacher_L12.teacher", "wl_L12.generated")
    secondary = {
        "theta_T": {"quantity": "wl_teacher_L12.teacher minus wl_L12.generated",
                    **wp2eval.contrast(d_t, False, n_boot=N_BOOT),
                    "tost": wp2eval.tost(d_t, wp2eval.THETA_T_MARGIN, ALPHA, n_boot=N_BOOT)},
        "theta1_wl": {lv: _sec(e3, *THETA1[f"theta1_wl.{lv}"]) for lv in ("L02", "L12")},
        "theta1_pc": {lv: _sec(e3, *THETA1[f"theta1_pc.{lv}"]) for lv in ("L02", "L06", "L12")},
        "raw_minus_generated": {"projected": _sec(e3, "raw_projected.linear", WL_REF),
                                "unprojected": _sec(e3, "raw_unprojected.linear", WL_REF)},
    }
    if identity:
        block = identity_block(e2)
        primary["H2"], primary["H3"] = dict(block), dict(block)
        for key in ("theta2_prime", "uniform", "correct_baseline"):
            secondary[key] = dict(block)
        auc = {k: {**block, "auc_a": None, "auc_b": None} for k in wp2eval.AUC_RANGES}
        return primary, secondary, auc

    def e2c(name, policy="frequency", primary_=False, keep=None):
        v = e2p2.puzzle_values(e2, name, policy)
        if keep is not None:
            v = {k: x for k, x in v.items() if k in keep}
        return {"policy": policy, **wp2eval.contrast(v, primary_, n_boot=N_BOOT)}, v

    primary["H2"] = _label_primary(e2c("theta2", primary_=True)[0])
    primary["H3"] = _label_primary(e2c("theta_comp", primary_=True)[0])
    t2p, v = e2c("theta2_prime")
    secondary["theta2_prime"] = {**t2p, "tost": wp2eval.tost(v, wp2eval.THETA2P_MARGIN, ALPHA, n_boot=N_BOOT)}
    secondary["uniform"] = {c: e2c(c, "uniform")[0] for c in ("theta2", "theta_comp", "theta2_prime")}
    correct = {b["puzzle_id"] for b in e2["base"] if b["solve_A"] == 1}
    secondary["correct_baseline"] = {c: e2c(c, keep=correct)[0] for c in ("theta2", "theta_comp")}
    auc = {"6-11": {"levels": [6, 11], **wp2eval.auc_frozen(e2p2.dose_nodes(e2, 6), e2p2.dose_nodes(e2, 11),
                                                            wp2eval.AUC_RANGES["6-11"])},
           "2-11": {"levels": [2, 11], **wp2eval.auc_frozen(e2p2.dose_nodes(e2, 2), e2p2.dose_nodes(e2, 11),
                                                            wp2eval.AUC_RANGES["2-11"])}}
    return primary, secondary, auc


def rare_event(primary: dict, secondary: dict) -> dict:
    flat = dict(primary)
    for key, val in secondary.items():
        if "status" in val or "ci95" in val:
            flat[key] = val
        else:
            flat.update({f"{key}.{k}": v for k, v in val.items()})
    out = {}
    for name, x in flat.items():
        if "ci95" not in x:
            continue
        out[name] = {"ci95_method": x["ci95"]["method"], "n_nonzero": x["n_nonzero"], "n": x["n"],
                     "family_method": (x.get("family") or {}).get("method"),
                     "tost_method": (x.get("tost") or {}).get("method")}
    return out


# --- E2 diagnostics (D78) ---------------------------------------------------------------------

def _diag_groups(e2: dict) -> dict[str, tuple[int, list[tuple[str, np.ndarray]]]]:
    """label -> (intervention level, [(stage key, per-row weight)])."""
    ids = e2["ids"]
    groups: dict = {}
    by_value = defaultdict(list)
    for r in e2["level1"]:
        by_value[r["value"]].append(r)
    for policy in POLICIES:
        items = []
        for v in sorted(by_value):
            rows = by_value[v]
            if [r["puzzle_id"] for r in rows] != ids:
                sys.exit(f"{NAME}: e2.json level-1 value {v} rows are not in id order")
            items.append((f"level1/v{v:02d}", np.array([0.0 if r.get("noop") else float(r[f"w_{policy}"])
                                                        for r in rows])))
        groups[f"level1-{policy}"] = (1, items)
    stages = defaultdict(list)
    for r in e2["records"]:
        stages[(r["level"], r["policy"], r["dose"], r["seed"])].append(r)
    configs = defaultdict(list)
    for (level, policy, dose, seed), rows in sorted(stages.items()):
        if [r["puzzle_id"] for r in rows] != ids:
            sys.exit(f"{NAME}: e2.json records of L{level} {policy} d{dose} s{seed} are not in id order")
        configs[(level, policy, dose)].append((f"L{level:02d}/{policy}/d{dose:02d}/s{seed}",
                                               np.array([1.0 if r["eligible"] else 0.0 for r in rows])))
    for (level, policy, dose), items in sorted(configs.items()):
        groups[f"L{level:02d}-{policy}-d{dose}"] = (level, items)
    return groups


def _per_puzzle(items, get) -> np.ndarray:
    """Per puzzle: sum_s w x / sum_s w over the group's stages (rows with weight 0 ignored)."""
    num = den = None
    for key, w in items:
        x = np.asarray(get(key), dtype=np.float64)
        wx = w.reshape(-1, *([1] * (x.ndim - 1)))
        c = np.where(wx > 0, x, 0.0) * wx
        num, den = (c, w.copy()) if num is None else (num + c, den + w)
    keep = den > 0
    return num[keep] / den[keep].reshape(-1, *([1] * (num.ndim - 1)))


def _over_puzzles(per: np.ndarray):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmean(per, axis=0)


def _row_means(arr: np.ndarray, cells: np.ndarray) -> np.ndarray:
    """Per row (and level) the share of `cells` that changed; arr [n, ..., 81], cells [n, 81] bool."""
    c = cells.reshape(len(cells), *([1] * (arr.ndim - 2)), 81)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (arr * c).sum(-1) / c.sum(-1)


def _map_summary(cells81: np.ndarray) -> dict:
    g = np.asarray(cells81).reshape(9, 9)
    return {"cells": cells81, "rows": g.mean(axis=1), "columns": g.mean(axis=0),
            "boxes": g.reshape(3, 3, 3, 3).mean(axis=(1, 3)).reshape(9)}


def _quantiles(per: np.ndarray):
    v = per[~np.isnan(per)]
    return np.quantile(v, e2p2.QUANTILES).tolist() if v.size else None


def e2_diagnostics(e2: dict, diag_dir: Path, empty: np.ndarray, inputs: Inputs) -> dict:
    files = e2.get("diag_files") or {}
    cache: dict = {}

    def arrays(key):
        if key not in cache:
            entry = files.get(key) or {}
            cache[key] = inputs.npz(diag_dir / (entry.get("file") or f"{key.replace('/', '__')}.npz"),
                                    entry.get("sha256"), "e2.json diag_files")
        return cache[key]

    def get(name, f=None):
        return lambda key: (f or (lambda a: a))(arrays(key)[name].astype(np.float64))

    given = ~empty
    out = {"cell_change_map": {}, "later_level_changes": {}, "replacement": {}, "propagation": {}}
    for label, (level, items) in _diag_groups(e2).items():
        cmap = {}
        for b in "CD":
            cells = _over_puzzles(_per_puzzle(items, get(f"changed_{b}")))
            eg = {"empty": _over_puzzles(_per_puzzle(items, get(f"changed_{b}", lambda a: _row_means(a, empty)))),
                  "given": _over_puzzles(_per_puzzle(items, get(f"changed_{b}", lambda a: _row_means(a, given))))}
            cmap[b] = {**_map_summary(cells), "empty_given": eg}
        out["cell_change_map"][label] = cmap
        later = _over_puzzles(_per_puzzle(items, get("later_changes_D")))
        out["later_level_changes"][label] = {str(k + 1): later[k] for k in range(level, len(later))}

        def pos_mean(a):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                return np.nanmean(a, axis=1)

        out["replacement"][label] = {
            **{q: _quantiles(_per_puzzle(items, get(q, pos_mean))) for q in ("p_new", "p_orig", "freq_new")},
            "replacement_norm": _quantiles(_per_puzzle(items, get("replacement_norm"))), "quantiles": e2p2.QUANTILES}
        if label in PRIMARY_DIAG:
            missing = [k for k, _ in items if "state_dist_C" not in arrays(k)]
            if missing:
                sys.exit(f"{NAME}: primary diagnostic stage {missing[0]} has no full (state) diagnostics")
            prop = {}
            for b in "CD":
                prop[f"state_dist_{b}"] = _over_puzzles(_per_puzzle(items, get(f"state_dist_{b}")))
                prop[f"level_changed_{b}"] = {
                    "map": _over_puzzles(_per_puzzle(items, get(f"level_changed_{b}"))),
                    "empty": _over_puzzles(_per_puzzle(items, get(f"level_changed_{b}",
                                                                  lambda a: _row_means(a, empty)))),
                    "given": _over_puzzles(_per_puzzle(items, get(f"level_changed_{b}",
                                                                  lambda a: _row_means(a, given))))}
            out["propagation"][label] = prop
    out["weighting"] = ("level-1 rows weighted by the policy weights over non-no-op rows; other configurations "
                        "averaged over eligible seeds within puzzle, then over puzzles")
    return out


# --- E3 tables --------------------------------------------------------------------------------

def _n_params(s: dict):
    return (s.get("budget") or {}).get("n_params")


def e3_main(e3: E3) -> list[dict]:
    rows = []
    for name, group, ref in E3_MAIN:
        s = e3.summary(name)
        b = e3.brier(name)
        b_ref = e3.brier(ref) if ref is not None else None
        rel = (b - b_ref) / b_ref if ref is not None and b is not None and b_ref else None
        rows.append({"row": name, "group": group, "construction": s.get("construction"), "brier": b,
                     "reference": ref, "brier_reference": b_ref, "relative_difference": rel,
                     "config": s.get("config"), "n_params": _n_params(s)})
    return rows


def _fit_names():
    for stage, _ in STAGES:
        for fit in STAGE_FITS[stage]:
            yield f"{stage}.{fit}"


def _prelock_ref(stage: str, fit: str) -> tuple[str, list[str]] | None:
    if stage in ("pc_L02", "pc_L06", "pc_L12"):
        lv = stage[3:]
        return "probes.json", ["stages", f"{lv}_permuted_linear" if fit == "permuted" else f"{lv}_{fit}"]
    if stage in ("controls", "unit_digit"):
        return "probes.json", ["stages", stage, fit]
    if stage == "training_size":
        return "probes.json", ["stages", stage, fit[1:]]
    if stage in ("wl_L06", "wl_L12"):
        return "wholelayer.json", ["stages", stage[3:], f"{fit}_linear"]
    if stage == "wl_teacher_L12":
        return "wholelayer.json", ["stages", "teacher_L12", "teacher_linear"]
    if stage in ("raw_projected", "raw_unprojected"):
        return "wholelayer.json", ["stages", stage, fit]
    return None


def config_vs_prelock(e3: E3, prelock: dict) -> dict:
    out = {}
    for name in _fit_names():
        s = e3.summary(name)
        if s.get("config") is None:
            continue
        ref = _prelock_ref(*name.split("."))
        cfg, source = None, None
        if ref is not None:
            node = prelock[ref[0]]
            for k in ref[1]:
                node = node.get(k) if isinstance(node, dict) else None
            cfg = node.get("config") if isinstance(node, dict) else None
            source = f"experiments/e3prep/{ref[0]} " + ".".join(ref[1]) + (" (D64)" if ref[0] == "probes.json"
                                                                             else " (D67)")
        out[name] = {"selected": s["config"], "prelock": cfg, "source": source,
                     "differs": None if cfg is None else [float(x) for x in s["config"]] != [float(x) for x in cfg]}
    return out


def e3_tables(e3: E3, budget: dict, prelock: dict, h1: dict) -> dict:
    B = e3.brier
    levels, mlp = {}, {}
    for lv in ("L02", "L06", "L12"):
        pc_perm = "controls.permuted_linear" if lv == "L06" else f"pc_{lv}.permuted"
        levels[lv] = {"whole_layer": {"generated": B(f"wl_{lv}.generated"), "permuted": B(f"wl_{lv}.permuted")},
                      "per_cell": {"linear": B(f"pc_{lv}.linear"), "mlp": B(f"pc_{lv}.mlp"), "permuted": B(pc_perm)}}
        lin, ml = e3.summary(f"pc_{lv}.linear"), e3.summary(f"pc_{lv}.mlp")
        mlp[lv] = {"linear": B(f"pc_{lv}.linear"), "mlp": B(f"pc_{lv}.mlp"),
                   "mlp_minus_linear": (B(f"pc_{lv}.mlp") - B(f"pc_{lv}.linear")
                                        if None not in (B(f"pc_{lv}.mlp"), B(f"pc_{lv}.linear")) else None),
                   "config_linear": lin.get("config"), "config_mlp": ml.get("config"),
                   "n_params_linear": _n_params(lin), "n_params_mlp": _n_params(ml)}
    n, puzzles = e3.n, np.asarray(e3.score["puzzles"])
    y_unit = unit_digit_labels(puzzles).reshape(-1, 9).astype(np.float64)
    pz_unit = np.repeat(np.arange(n), 27)
    unit = {}
    for fit in STAGE_FITS["unit_digit"]:
        name = f"unit_digit.{fit}"
        s = e3.summary(name)
        unit[fit] = {"brier": B(name), "config": s.get("config"), "n_params": _n_params(s),
                     **unit_metrics(e3.preds(name)["mean"], y_unit, pz_unit, n)}
    training = {}
    for key, stage in (("whole_layer", "wl_training_size"), ("per_cell", "training_size")):
        training[key] = {fit: {"n_puzzles": e3.summary(f"{stage}.{fit}").get("n_puzzles"), "brier": B(f"{stage}.{fit}"),
                               "config": e3.summary(f"{stage}.{fit}").get("config"),
                               "reused_from": e3.summary(f"{stage}.{fit}").get("reused_from")}
                         for fit in STAGE_FITS[stage]}
    training["note"] = ("whole_layer is the primary probe's curve and the basis for any data-requirement statement; "
                        "per_cell is secondary (spec ambiguity 3)")
    mask, empty, depth = e3.score["mask"], e3.empty, e3.score["depth"]
    rates = depth_label_rates(mask, empty, depth)
    depth_tab = {name: {"brier": depth_breakdown_seeds(e3.seed_preds(name), mask, empty, depth), "label_rates": rates}
                 for name in DEPTH_FITS}
    sec = {}
    for name in _fit_names():
        s = e3.summary(name)
        if s.get("rows") == "reused":
            sec[name] = {"reused_from": s.get("reused_from")}
        elif s.get("rows") == "cell":
            sec[name] = secondary_metrics(e3.preds(name)["mean"], e3.y, e3.pz, n, empty, puzzles)
    bud = {}
    for stage, _ in STAGES:
        for fit, entries in (budget.get(stage) or {}).items():
            bud[f"{stage}.{fit}"] = {"entries": entries, "n_params": _n_params(e3.summary(f"{stage}.{fit}")),
                                     "any_hit_cap": any(bool(e.get("hit_cap")) for e in entries)}
    seeds = {}
    for name, (a, b) in THETA1.items():
        ba, bb = e3.seed_briers(a), e3.seed_briers(b)
        seeds[name] = {"permuted": a, "generated": b,
                       "per_seed": [_mean(x - y) for x, y in zip(ba, bb)],
                       "brier_permuted_per_seed": [_mean(x) for x in ba],
                       "brier_generated_per_seed": [_mean(y) for y in bb]}
    seeds["H1"]["h1_block_per_seed"] = h1.get("per_seed")
    return {"e3_main": e3_main(e3), "e3_levels": levels, "mlp": mlp, "unit_digit": unit, "training_size": training,
            "depth": depth_tab, "secondary_metrics": sec, "budget": bud,
            "config_vs_prelock": config_vs_prelock(e3, prelock), "seed_stability": seeds}


def equivariance_table(eq: dict) -> dict:
    kinds = list(eq.get("mean_deviation") or {})
    return {"categories": {k: {"mean_deviation": eq["mean_deviation"][k], "share_within": eq["share_within"][k],
                               "brier_transformed": eq["mean_brier"][k],
                               "brier_original": eq["mean_brier_original"]} for k in kinds},
            "n": eq.get("n"), "acceptable": eq.get("acceptable"), "acceptable_source": eq.get("acceptable_source"),
            "seed_noise_p95": eq.get("seed_noise_p95"), "equivariance_reading": wp2eval.EQUIV_READING}


# --- report -----------------------------------------------------------------------------------

def _f(x, nd=6) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    if isinstance(x, float):
        return f"{x:.{nd}g}"
    if isinstance(x, (list, tuple)):
        return "[" + ", ".join(_f(v, nd) for v in x) + "]"
    return str(x)


def _ci(block) -> str:
    return "n/a" if not block or block.get("ci") is None else f"[{_f(block['ci'][0])}, {_f(block['ci'][1])}]"


def _tost_label(tost: dict) -> str:
    """The interval the TOST verdict actually used: two-sided 1 - 2 alpha (bootstrap) or, on the
    rare-event path, the one-sided 1 - alpha bound (`wp2eval.tost`)."""
    if tost.get("method") == "bound":
        return f"one-sided {round(100 * (1 + tost['level']) / 2, 2):g}% rare-event bound"
    return f"{round(100 * tost['level'], 2):g}% interval ({tost.get('method')})"


def _table(header: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(_f(c) if not isinstance(c, str) else c for c in r) + " |" for r in rows]
    return out + [""]


def report(res: dict) -> str:
    L = [f"# WP2 evaluation ({res['role']} role)", ""]
    if res["role"] == "dry":
        L += [f"**{wp2.DRY_NOTE}**", ""]
    else:
        L += [f"**{TEST_NOTE}**", ""]
    L += [f"- Date: {res['date']}", f"- Tag commit: {res['freeze_state'].get('tag_commit')}",
          f"- Frozen now: {res['freeze_state'].get('frozen')}", ""]
    L += _table(["Runner", "Status", "Valid", "Commit", "Seconds", "Reasons"],
                [[k, str(v["status"]), v["valid"], str(v["commit"]), v["seconds"], ", ".join(v["reasons"]) or "-"]
                 for k, v in res["records"].items()])

    L += ["## Primary contrasts (§11.1)", ""]
    rows, notes = [], []
    for name, x in res["primary"].items():
        if "status" in x:
            continue
        tost = x.get("tost") or {}
        rows.append([name, x["estimate"], _ci(x["family"]), _ci(x["ci95"]), x["ci95"]["method"], x["n"],
                     x["n_nonzero"], f"{_ci(tost)}, {_tost_label(tost)}" if tost else "-",
                     ("equivalent" if tost.get("equivalent") else "not equivalent") if tost else "-"])
        notes.append(f"- {name}: the 95% interval is the {x['ci95_label']}.")
    L += _table(["Contrast", "Estimate", "98.33% interval", "95% interval", "Method", "n", "n nonzero",
                 "H1 TOST interval (level, method)", "TOST verdict"], rows) + notes + [""]
    if any("status" in x for x in res["primary"].values()):
        blk = res["primary"]["H2"]
        L += ["**E2 identity failure (spec ambiguity 23).** No E2 interval, TOST, AUC or reading is computed: "
              f"{blk['deviation_required']}. sham_mismatch = {json.dumps(blk['sham_mismatch'])}, "
              f"level1_noop_mismatch = {blk['level1_noop_mismatch']}, code_mismatch = "
              f"{json.dumps(blk['code_mismatch'])}.", ""]

    L += ["## §13 readings", ""]
    h1_equiv = bool((res["primary"]["H1"].get("tost") or {}).get("equivalent"))
    for r in res["readings"]:
        if r["row"] is None:
            L += [f"- **{r['hypothesis']}**: {r['note']}. Inputs: `{json.dumps(r['inputs'])}`"]
            continue
        L += [f"- **{r['hypothesis']}** — {r['result']}", f"  - Justified claim: {r['claim']}",
              f"  - Does not follow: {r['does_not_follow']}"]
        if r["row"] == "h1_negative" and h1_equiv:
            L += [f"  - {EQUIV_BOTH_NOTE}"]
    L += [""]

    L += ["## Secondary contrasts", ""]
    rows = []
    for key, val in res["secondary"].items():
        items = [(key, val)] if ("status" in val or "ci95" in val) else [(f"{key}.{k}", v) for k, v in val.items()]
        for name, x in items:
            if "status" in x:
                rows.append([name, "identity-failure", "-", "-", "-", "-", "-"])
                continue
            tost = x.get("tost")
            rows.append([name, x["estimate"], _ci(x["ci95"]), x["ci95"]["method"], x["n"],
                         f"{_ci(tost)}, {_tost_label(tost)}" if tost else "-",
                         ("equivalent" if tost["equivalent"] else "not equivalent") if tost else "-"])
    L += _table(["Contrast", "Estimate", "95% interval", "Method", "n", "TOST interval (level, method)", "TOST verdict"], rows)

    L += ["## AUC over the frozen range (§7.3, §12.2)", ""]
    for k, a in res["auc"].items():
        if "status" in a:
            L += [f"- {k}: not computed (E2 identity failure)."]
        else:
            L += [f"- {k}: auc_a = {_f(a['auc_a'])}, auc_b = {_f(a['auc_b'])}, range = {_f(a['range'])}, "
                  f"TEST coverage = {_f(a['coverage'])}, reason = {a['reason'] or '-'}"]
    L += [""]

    t = res["tables"]
    e1 = t["e1"]
    L += ["## E1 (§6)", "", f"- n = {e1['n']}, official exact share = {_f(e1['official_exact_share'])}, "
          f"generated solve = {_f(e1['generated']['solve'])}, teacher exact share = {_f(e1['teacher']['exact_share'])}",
          f"- Hamming: token mean = {_f(e1['hamming']['token_mean'])}, cell mean = {_f(e1['hamming']['cell_mean'])}, "
          f"cell empty mean = {_f(e1['hamming']['cell_empty_mean'])}, n = {e1['hamming']['n_cell_hamming']}", ""]

    e2t = t["e2"]
    L += ["## E2 descriptive tables (no statistics)", "",
          f"- sham_mismatch = {json.dumps(e2t['sham_mismatch'])}, level1_noop_mismatch = "
          f"{e2t['level1_noop_mismatch']}, code_mismatch = {json.dumps(e2t['code_mismatch'])}", ""]
    L += _table(["Level", "Policy", "Dose", "Records", "Excluded", "Solve A", "Solve C", "Solve D"],
                [[c["level"], c["policy"], c["dose"], c["n_records"], c["excluded_share"], c["solve_mean"]["A"],
                  c["solve_mean"]["C"], c["solve_mean"]["D"]] for c in e2t["configurations"]])
    diag = t["e2_diagnostics"]
    L += ["### E2 propagation diagnostics (D78)", "", f"- Weighting: {diag['weighting']}. Full maps are in results.json.",
          ""]
    L += _table(["Configuration", "Mean later-level D code changes"],
                [[k, ", ".join(f"L{lv}: {_f(v, 4)}" for lv, v in d.items())]
                 for k, d in diag["later_level_changes"].items()])
    L += _table(["Primary configuration", "state_dist_C per level", "state_dist_D per level"],
                [[k, _f(p["state_dist_C"], 4), _f(p["state_dist_D"], 4)] for k, p in diag["propagation"].items()])

    L += ["## E3 main table (§8.2, §12.2)", "",
          "Brier = seed-mean per-puzzle Brier on the score set; relative difference = (Brier - reference) / "
          "reference, only within one construction.", ""]
    L += _table(["Row", "Group", "Construction", "Brier", "Reference", "Relative difference", "Config", "n_params"],
                [[r["row"], r["group"], str(r["construction"]), r["brier"], str(r["reference"] or "-"),
                  r["relative_difference"], r["config"], r["n_params"]] for r in t["e3_main"]])
    L += _table(["Level", "WL generated", "WL permuted", "PC linear", "PC MLP", "PC permuted"],
                [[lv, x["whole_layer"]["generated"], x["whole_layer"]["permuted"], x["per_cell"]["linear"],
                  x["per_cell"]["mlp"], x["per_cell"]["permuted"]] for lv, x in t["e3_levels"].items()])
    L += _table(["Unit-digit fit", "Brier", "Exact match", "ROC-AUC", "Brier (ensemble)"],
                [[k, v["brier"], v["exact_match"], v["roc_auc"], v["brier_ensemble"]] for k, v in t["unit_digit"].items()])
    L += [f"Training size: {t['training_size']['note']}.", ""]
    L += _table(["Curve", "Fit", "n puzzles", "Brier", "Reused from"],
                [[c, f, v["n_puzzles"], v["brier"], str(v["reused_from"] or "-")]
                 for c in ("whole_layer", "per_cell") for f, v in t["training_size"][c].items()])
    L += ["Depth breakdown (descriptive; label rates and sample sizes differ by depth, §5.2, §8.3):", ""]
    rates = t["depth"][DEPTH_FITS[0]]["label_rates"]
    L += _table(["Depth", "n cells", "n puzzles", "Positive rate", *DEPTH_FITS],
                [[c, rates[c]["n_cells"], rates[c]["n_puzzles"], rates[c]["positive_rate"],
                  *[t["depth"][f]["brier"][c]["brier"] for f in DEPTH_FITS]] for c in rates])
    L += _table(["θ₁ pair", "Per-seed θ₁ means (no intervals, spec ambiguity 18)"],
                [[k, _f(v["per_seed"])] for k, v in t["seed_stability"].items()])
    diffs = [k for k, v in t["config_vs_prelock"].items() if v["differs"]]
    L += [f"Selected configurations that differ from the pre-lock D64/D67 selection: {', '.join(diffs) or 'none'}.", ""]

    eq = t["equivariance"]
    L += ["## Exploratory level-12 equivariance (§8.4)", "",
          f"Reading: {eq['equivariance_reading']}; tolerance {_f(eq['acceptable'])} ({eq['acceptable_source']}), "
          f"TEST seed-noise P95 = {_f(eq['seed_noise_p95'])}.", ""]
    L += _table(["Category", "Mean deviation", "Share within", "Brier transformed", "Brier original"],
                [[k, v["mean_deviation"], v["share_within"], v["brier_transformed"], v["brier_original"]]
                 for k, v in eq["categories"].items()])

    L += ["## §7.4 disclosure", "", res["disclosure_7_4"], "", "## Claim boundaries (§13)", "", CLAIM_BOUNDARIES, ""]
    return "\n".join(L)


# --- main -------------------------------------------------------------------------------------

def run(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", choices=wp2.ROLES, required=True)
    role = ap.parse_args(sys.argv[1:] if argv is None else argv).role
    exp, raw = wp2.paths(role)
    single_look(role, exp)
    freeze = wp2.freeze_state()
    records, reasons, identity = gate(role, freeze)
    inputs = Inputs()

    e1 = inputs.json(raw / "e1.json", _outputs(records["e1"], "e1.json"), "e1 run record")
    e2 = inputs.json(raw / "e2.json", _outputs(records["e2"], "e2.json"), "e2 run record")
    fits = inputs.json(exp / "e3_fits.json", _outputs(records["e3"], "e3_fits.json"), "e3 run record")
    budget = inputs.json(exp / "e3_budget.json", _outputs(records["e3"], "e3_budget.json"), "e3 run record")
    equiv = inputs.json(exp / "equivariance.json", _outputs(records["equiv"], "equivariance.json"), "equiv run record")
    manifest = records["e3_extract"].get("score_manifest") or {}
    score_dir = raw / "e3data" / "score"
    score = {"ids": inputs.json(score_dir / "ids.json", manifest.get("ids.json"), "e3_extract score_manifest")}
    for name in SCORE_FILES[1:]:
        score[name[:-4]] = inputs.npy(score_dir / name, manifest.get(name), "e3_extract score_manifest")
    if fits.get("score_ids") != score["ids"]:
        sys.exit(f"{NAME}: e3_fits.json score_ids differ from the score set's ids.json")
    if e1.get("ids") != e2.get("ids"):
        sys.exit(f"{NAME}: e1.json ids differ from e2.json ids")
    role_data = wp2.load_role(role)
    if list(role_data.ids) != e2["ids"]:
        sys.exit(f"{NAME}: the role's puzzle ids differ from e2.json ids")
    if role == "test":  # defence in depth: the runners check these at the source
        if score["ids"] != list(role_data.ids):
            sys.exit(f"{NAME}: the score set's ids differ from the TEST ids")
        if equiv.get("ids") != score["ids"][:N_EQUIV]:
            sys.exit(f"{NAME}: equivariance.json ids differ from the first {N_EQUIV} score ids")
    prelock = {name: _read(inputs.unrecorded(wp2.ROOT / "experiments" / "e3prep" / name))
               for name in ("probes.json", "wholelayer.json")}

    e3 = E3(fits, raw / "e3", score, inputs)
    primary, secondary, auc = statistics(e2, e3, identity)
    eq_table = equivariance_table(equiv)
    readings = wp2eval.select_readings({"H1": primary["H1"], "H2": primary["H2"], "H3": primary["H3"],
                                        "theta2_prime": secondary["theta2_prime"],
                                        "theta1_L12_wl": secondary["theta1_wl"]["L12"],
                                        "theta_T": secondary["theta_T"], "equivariance": eq_table})
    tables = {"e1": e1_table(e1["records"]), "e2": wp2eval.e2_descriptive(e2),
              "e2_diagnostics": e2_diagnostics(e2, raw / "e2" / "diag", np.asarray(role_data.puzzles) == 0, inputs),
              **e3_tables(e3, budget, prelock, primary["H1"]), "equivariance": eq_table}

    torch.use_deterministic_algorithms(True)  # before every environment_record()
    res = {
        "role": role, "note": wp2.DRY_NOTE if role == "dry" else TEST_NOTE, "date": time.strftime("%Y-%m-%d"),
        "code_state": wp2.code_state(), "freeze_state": freeze, "environment": wp2.environment_record(),
        "records": {k: {"status": r.get("status"), "valid": r.get("valid"), "commit": (r.get("code") or {}).get("commit"),
                        "seconds": r.get("seconds"), "reasons": reasons[k]} for k, r in records.items()},
        "inputs": inputs.sha,
        "role_data": {"source": role_data.source, "n": len(role_data.ids)},
        "e2_identity_failure": identity,
        "primary": primary, "secondary": secondary, "rare_event": rare_event(primary, secondary),
        "readings": readings, "auc": auc, "disclosure_7_4": DISCLOSURE_7_4, "tables": tables,
    }
    res = _plain(res)
    text = report(res)  # rendered before either write: a report failure leaves the single look unused
    wp2.atomic_json(exp / "results.json", res)
    wp2.atomic_write(exp / "report.md", text)
    return 0


def main(argv: list[str] | None = None) -> None:
    try:
        code = run(argv)
    except wp2.DataIntegrityError as e:
        sys.exit(f"{NAME}: {e}")
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
