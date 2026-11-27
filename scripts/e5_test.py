"""E5 TEST runner and its PROBE-VAL dry runs (`e5_protocol_v1.md` §4-§6, §8, §9.3-§9.4).

Usage: uv run --locked python scripts/e5_test.py --mode dry|dry_perm|test [--resume]

Modes:
- `dry`: the 250 PROBE-VAL pairs of runs/e5/pairs/probe_val/ (ids and arrays checked against
  experiments/e5/pairs.json), raw order; never imports or calls the TEST pair generation path.
- `dry_perm`: as `dry`, processing pair `PERMUTATION[j]` = (19 j + 1) mod 250 at position j
  (§9.4(e): every pair changes its in-batch position); every output is keyed by pair id.
- `test`: requires the `e5-prereg-v1` lock (`e5run.require_lock`: tag, clean code, manifest,
  approved dry record), then generates the 400 TEST pairs (namespace 10) with `screen_pairs`
  against the external canonical-key index (gate, CAL, PROBE-TRAIN, PROBE-VAL, WP2 TEST, released
  hard set, E5 PROBE pairs) and checks `internal_collisions` (any: both claims invalid, no redraw).

Start (§6): torch threads set to 4 (refuses otherwise); every input hashed into `run.json`
(`e5run.start_run`; `--resume` continues only an interrupted run with identical inputs and
verified partial outputs). Hash checks by §6 category (ruling R5): checkpoint, generator guard,
pair set, screening corpus, P2 head (and in test mode the manifest and dry record) -> the run stops
invalid for both claims; Z<=6 head -> claim A invalid; W, Q, H, R, Pi, P4, P8 -> claim B invalid;
the run continues for the other claim.

Stages under `e5run.RUN_DIR[mode]` (each written atomically and recorded in run.json; a resumed
run skips recorded stages): `pairs.npz` (a, b, solutions and ids in raw order, the processing
`order`, and `meta_json` with the screening log and internal collisions), `extract/<a|b>/batch_<k>.npz` (every `extract_batch` array plus
`check_failures`: shapes of the 9 captured layers, z6 shapes, codes equal to a clean
`generate_codes` call on the same batch in dry modes and the first TEST batch of each member),
`probes.npz` (per-seed and mean predictions and the identical-input flags for P2 and Z<=6),
`causal/<ab|ba>_batch_<k>.npz` (per recipient: `pair_index` (position in the raw-ordered pair
set), `pair_ids`, `order` (0 = ab, 1 = ba), every `evaluate_batch` array, `invalid_reasons`),
`decisions.json`. Batches of 50: extraction a-members then b-members, probe inference over the
same rows, causal recipients order ab then ba (§4.4).

Outputs: `e5run.OUT_DIR[mode]/results.json` (per-pair rows by pair id in raw order, decision
inputs, log K, outcomes, bootstrap intervals, eligibility, screening, invalid reasons, input
hashes, threads, code state; dry modes also the max abs difference to the saved pilot
predictions, information only) and `report.md` (the §8 rows selected by the outcomes, copied
verbatim from the protocol). A non-finite value, a failed extraction check, an internal
collision or a shared hash mismatch stops the run: status `invalid`, both claims invalid.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from ncm_sudoku import e5pairs, e5run, subsets
from ncm_sudoku.e5batch import CONDITIONS, OUTCOMES, evaluate_batch
from ncm_sudoku.e5extract import extract_batch
from ncm_sudoku.e5probes import candidate_targets
from ncm_sudoku.e5test import (
    NonFiniteError,
    bootstrap,
    check_finite,
    decide,
    eligibility,
    external_index,
    head_probs,
    internal_collisions,
    pair_scores,
    same_inputs,
    screen_pairs,
)
from ncm_sudoku.g0 import code_state, environment_record
from ncm_sudoku.gate import GATE_N
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.released import load_released
from ncm_sudoku.runner import generate_codes, puzzle_tensor
from ncm_sudoku.wp2 import CKPT_SHA256, DataIntegrityError, atomic_json, atomic_npz, atomic_write, verify_checkpoints

CODE_ROOT = ROOT  # code and protocol hashes always come from the repository itself
THREADS, BATCH, LEVELS_1_6 = 4, 50, 35
N_TEST, N_DRY = 400, 250
D_MODEL, Z_DIM = 512, 256
PERMUTATION = (19 * np.arange(N_DRY) + 1) % N_DRY
EXISTING = {"gate": GATE_N, "cal": 300, "probe_train": 2000, "probe_val": 500, "test": 600}  # as scripts/e5_pairs.py
CODE_FILES = ["scripts/e5_test.py", "e5_protocol_v1.md"] + [
    f"src/ncm_sudoku/{m}.py" for m in ("e5test", "e5batch", "e5run", "e5stats", "e5causal", "e5extract", "e5pairs",
                                       "e5probes", "probes", "labels", "intervene", "states", "runner", "model",
                                       "symmetry", "subsets", "generate", "solve", "wp2")]
DRY_NOTE = "DRY RUN on the PROBE-VAL pairs (protocol §9.4); not TEST"
STOP_ROW = "Internal collision, shared failure or non-finite stop"


class Stop(Exception):
    """A shared failure (§6): the run stops and both claims are invalid."""


def _paths() -> dict:
    r = ROOT
    return {"pairs_json": r / "experiments/e5/pairs.json", "pairs": r / "runs/e5/pairs",
            "components": r / "experiments/e5/lock/components.json", "heads": r / "experiments/e5/causal/heads.json",
            "ckpt": r / "checkpoints/sudoku/hard", "pilot": r / "runs/e5/pilot",
            "released": r / "data/released/sudoku/hard", "released_json": r / "experiments/provenance/released_data.json",
            "test_set": r / "experiments/lock/test_set.json", "manifest": r / "experiments/e5/lock/manifest.json",
            "dry_record": r / "experiments/e5/dry/check.json"}


def _json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _npz(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def _plain(x):
    """JSON-safe copy: numpy scalars and arrays to Python, NaN to None."""
    if isinstance(x, dict):
        return {k: _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, np.ndarray)):
        return [_plain(v) for v in (x.tolist() if isinstance(x, np.ndarray) else x)]
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, (np.integer, int)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else float(x)
    return x


def _load_pairs(P: dict, subset: str) -> tuple[list, dict, bool]:
    """Ids and arrays of a PROBE pair subset and whether they match experiments/e5/pairs.json."""
    d = P["pairs"] / subset
    ids = _json(d / "ids.json")
    arr = {k: np.load(d / f"{k}.npy", allow_pickle=False) for k in ("a", "b", "solutions")}
    sha = _json(P["pairs_json"])["subsets"][subset]["sha256"]
    ok = subsets.sha256_ids(ids) == sha["ids"] and all(subsets.sha256_array(v) == sha[k] for k, v in arr.items())
    return ids, arr, ok


# --- start: inputs and §6 hash categories --------------------------------------------------------

def _inputs(mode: str, P: dict) -> tuple[dict, dict]:
    """Input hashes for run.json and the expected hashes with their §6 category."""
    comps, heads = _json(P["components"])["files"], _json(P["heads"])["heads"]
    files = {f"checkpoint/{n}": P["ckpt"] / n for n in CKPT_SHA256}
    files |= {f"head/{k}": ROOT / heads[k]["file"] for k in ("P2", "P4", "P8")}
    files |= {f"component/{k}": ROOT / comps[k]["file"] for k in ("z6_head", "W", "Q", "H", "R", "Pi")}
    files |= {f"code/{c}": CODE_ROOT / c for c in CODE_FILES}
    files["pairs_json"] = P["pairs_json"]
    for subset in (("probe_train", "probe_val") if mode == "test" else ("probe_val",)):
        files |= {f"pairs/{subset}/{f}": P["pairs"] / subset / f for f in ("ids.json", "a.npy", "b.npy", "solutions.npy")}
    expected = {f"head/{k}": (heads[k]["sha256"], "shared" if k == "P2" else "B") for k in ("P2", "P4", "P8")}
    expected |= {f"component/{k}": (comps[k]["sha256"], "A" if k == "z6_head" else "B")
                 for k in ("z6_head", "W", "Q", "H", "R", "Pi")}
    if mode == "test":
        rel = _json(P["released_json"])["hard"]["files"]
        for name in ("puzzles.pickle", "solutions.pickle"):
            files[f"corpus/released/{name}"] = P["released"] / name
            expected[f"corpus/released/{name}"] = (rel[f"sudoku/hard/{name}"]["sha256"], "shared")
        files["corpus/test_set.json"] = P["test_set"]
    inputs = e5run.input_hashes(files)
    inputs |= {"mode": mode, "threads": str(THREADS)}
    if mode == "test":
        inputs["order"] = "raw_index (the recorded pairs stage fixes the ids)"
    else:
        ids = _json(P["pairs"] / "probe_val" / "ids.json")
        if len(ids) != N_DRY:
            raise SystemExit(f"PROBE-VAL has {len(ids)} pairs, expected {N_DRY}")
        order = PERMUTATION if mode == "dry_perm" else np.arange(N_DRY)
        inputs["order"] = subsets.sha256_ids([ids[i] for i in order])
    return inputs, expected


def _start_checks(mode: str, P: dict, inputs: dict, expected: dict, lock_problem: str | None) -> dict:
    inv = {"shared": [], "A": [], "B": []}
    if lock_problem:
        inv["shared"].append(lock_problem)
    try:
        verify_checkpoints(P["ckpt"])
    except DataIntegrityError as e:
        inv["shared"].append(f"checkpoint_hash: {e}")
    try:
        subsets.assert_generator_frozen()
    except RuntimeError as e:
        inv["shared"].append(f"generator_guard: {e}")
    for key, (sha, cat) in expected.items():
        if inputs[key] != sha:
            inv[cat].append(f"hash_mismatch: {key}")
    for subset in (("probe_train", "probe_val") if mode == "test" else ("probe_val",)):
        if not _load_pairs(P, subset)[2]:
            inv["shared"].append(f"{'screening_corpus' if mode == 'test' else 'pair_set'}_hash: {subset} pairs")
    return inv


# --- stages --------------------------------------------------------------------------------------

class Runner:
    def __init__(self, mode: str, P: dict, done: set, inv: dict):
        self.mode, self.P, self.done, self.inv = mode, P, done, inv
        self.rd = e5run.RUN_DIR[mode]
        self.info: dict = {}
        self._model = None

    def model(self):
        if self._model is None:
            self._model = load_model(self.P["ckpt"])
        return self._model

    def stage(self, name: str, path: Path, compute, kind: str = "npz"):
        """Loads a recorded stage, or computes, writes atomically and records it."""
        if name in self.done:
            return _npz(path) if kind == "npz" else _json(path)
        obj = compute()
        atomic_npz(path, **obj) if kind == "npz" else atomic_json(path, _plain(obj))
        e5run.record_output(self.mode, name, path)
        return obj

    def pairs(self):
        def compute():
            if self.mode == "test":
                entries, corpus = self._corpus()
                accepted, log = screen_pairs(
                    lambda i: e5pairs.generate_pair(e5pairs.PAIR_SEEDS["pairs_test"], i), external_index(entries), N_TEST)
                arrays = {k: np.stack([getattr(p, f) for p in accepted]).astype(np.uint8)
                          for k, f in (("a", "a"), ("b", "b"), ("solutions", "solution"))}
                ids, order = [p.pair_id for p in accepted], np.arange(N_TEST)
                screen = {"applied": True, "n_candidates": len(log), "n_rejected": sum(not r["accepted"] for r in log),
                          "n_accepted": len(accepted), "corpus": corpus, "log": log}
            else:
                ids, arrays, _ = _load_pairs(self.P, "probe_val")
                order = PERMUTATION if self.mode == "dry_perm" else np.arange(N_DRY)
                screen = {"applied": False, "note": "dry mode: PROBE-VAL pairs, screened at generation (D99)"}
            sols = [SimpleNamespace(pair_id=i, solution=s) for i, s in zip(ids, arrays["solutions"])]
            meta = {"screen": screen, "internal_collisions": internal_collisions(sols)}
            return {**arrays, "ids": np.array(ids), "order": order, "meta_json": np.array(json.dumps(_plain(meta)))}

        arrays = self.stage("pairs", self.rd / "pairs.npz", compute)
        meta = json.loads(str(arrays["meta_json"]))
        self.ids, self.order, self.n = arrays["ids"].tolist(), np.asarray(arrays["order"]), len(arrays["ids"])
        self.info["screening"] = {k: v for k, v in meta["screen"].items() if k != "log"}
        self.info["internal_collisions"] = meta["internal_collisions"]
        if meta["internal_collisions"]:
            self.inv["shared"] += [f"internal_collision: {x} {y}" for x, y in meta["internal_collisions"]]
            raise Stop("internal collision")
        A, B, S = (arrays[k][self.order] for k in ("a", "b", "solutions"))
        self.puzzles, self.solutions = np.concatenate([A, B]), np.concatenate([S, S])
        mask, self.empty = candidate_targets(self.puzzles)
        self.mask = mask > 0.5
        self.elig_a, self.elig_b = eligibility(self.mask, self.empty, self.n)

    def _corpus(self) -> tuple[dict, dict]:
        gen = {name: subsets.generate_subset(name, n) for name, n in EXISTING.items()}
        ts = _json(self.P["test_set"])["sha256"]
        if (subsets.sha256_ids([g.puzzle_id for g in gen["test"]]) != ts["ids"]
                or subsets.sha256_array(np.stack([g.solution for g in gen["test"]])) != ts["solutions"]):
            self.inv["shared"].append("screening_corpus_hash: WP2 TEST differs from experiments/lock/test_set.json")
            raise Stop("screening corpus")
        entries = {name: [(g.puzzle_id, g.solution) for g in v] for name, v in gen.items()}
        _, rel = load_released(self.P["released"])
        entries["released"] = [(f"released-hard-{i}", s) for i, s in enumerate(rel)]
        for subset in ("probe_train", "probe_val"):
            ids, arr, _ = _load_pairs(self.P, subset)
            entries[f"pairs_{subset}"] = list(zip(ids, arr["solutions"]))
        flat = [x for v in entries.values() for x in v]
        return entries, {"counts": {k: len(v) for k, v in entries.items()},
                         "sha256_ids": subsets.sha256_ids([i for i, _ in flat]),
                         "sha256_solutions": subsets.sha256_array(np.stack([s for _, s in flat]))}

    def extract(self):
        feats, codes = {"P2": [], "z6": []}, []
        for mi, member in enumerate("ab"):
            for k, s in enumerate(range(0, self.n, BATCH)):
                rows = slice(mi * self.n + s, mi * self.n + min(s + BATCH, self.n))
                name = f"extract/{member}/batch_{k}"

                def compute(rows=rows, name=name, k=k):
                    pz = self.puzzles[rows]
                    out = extract_batch(self.model(), pz, self.solutions[rows])
                    check_finite(name, *(v for v in out.values() if v.dtype.kind == "f"))
                    fails = self._extract_checks(out, pz, self.mode != "test" or k == 0)
                    return {**out, "check_failures": np.array(fails, dtype=str)}

                out = self.stage(name, self.rd / "extract" / member / f"batch_{k}.npz", compute)
                if out["check_failures"].size:
                    self.inv["shared"] += [f"extraction_check: {name}: {f}" for f in out["check_failures"].tolist()]
                    raise Stop("extraction check")
                feats["P2"].append(out["prefix_cells"][:, 2].astype(np.float32))
                feats["z6"].append(out["z6"].astype(np.float32))
                codes.append(out["codes"])
        self.feats = {k: np.concatenate(v) for k, v in feats.items()}
        self.codes = np.concatenate(codes).astype(np.int64)

    def _extract_checks(self, out: dict, puzzles: np.ndarray, clean: bool) -> list[str]:
        B, fails = len(puzzles), []
        if out["prefix_cells"].shape != (B, 9, 81, D_MODEL):
            fails.append(f"prefix_cells shape {out['prefix_cells'].shape}")
        if out["prefix_bos"].shape != (B, 9, D_MODEL):
            fails.append(f"prefix_bos shape {out['prefix_bos'].shape}")
        for key in ("z6", "z6_teacher"):
            if out[key].shape != (B, 81, Z_DIM):
                fails.append(f"{key} shape {out[key].shape}")
        if clean:
            ref = generate_codes(self.model(), puzzles, batch_size=B).numpy()
            if not np.array_equal(out["codes"].astype(np.int64), ref):
                fails.append("codes differ from a clean generation")
        return fails

    def probes(self):
        heads, comps = _json(self.P["heads"])["heads"], _json(self.P["components"])["files"]
        files = {"P2": ROOT / heads["P2"]["file"], "z6": ROOT / comps["z6_head"]["file"]}

        def compute():
            out = {}
            for rep, f in files.items():
                per_seed, mean = head_probs(torch.load(f, weights_only=True), self.feats[rep], self.empty, batch=BATCH)
                check_finite(f"probes/{rep}", per_seed, mean[self.empty])
                out |= {f"{rep}_per_seed": per_seed, f"{rep}_mean": mean,
                        f"{rep}_same_input": same_inputs(self.feats[rep], self.n)}
            return out

        pr = self.stage("probes", self.rd / "probes.npz", compute)
        self.scores = {rep: pair_scores(pr[f"{rep}_mean"], self.mask, self.empty, pr[f"{rep}_same_input"], self.n)
                       for rep in files}
        if self.mode != "test":
            self.info["pilot_prediction_max_abs_diff"] = {rep: self._pilot_diff(rep, pr[f"{rep}_mean"]) for rep in files}

    def _pilot_diff(self, rep: str, mean: np.ndarray):
        """Information only (not a gate): max |dry - saved pilot| over the evaluable entries."""
        path = self.P["pilot"] / f"{rep}__shared__none.npy"
        if not path.is_file():
            return None
        pilot = np.load(path, allow_pickle=False)[np.concatenate([self.order, self.order + self.n])]
        both = np.isfinite(pilot) & np.isfinite(mean)
        return {"max_abs_diff": float(np.abs(pilot[both] - mean[both]).max()) if both.any() else None,
                "nan_pattern_equal": bool(np.array_equal(np.isnan(pilot), np.isnan(mean)))}

    def causal(self):
        heads, comps = _json(self.P["heads"])["heads"], _json(self.P["components"])["files"]
        loaded = {}
        directed = np.zeros((2, self.n, len(CONDITIONS)))
        n = self.n
        for oi, oname in enumerate(("ab", "ba")):
            for k, s in enumerate(range(0, n, BATCH)):
                idx = np.arange(s, min(s + BATCH, n))
                r, d = (idx, idx + n) if oname == "ab" else (idx + n, idx)

                def compute(idx=idx, r=r, d=d, oi=oi):
                    if not loaded:
                        loaded["comps"] = {k_: np.load(ROOT / comps[k_]["file"], allow_pickle=False)
                                           for k_ in ("W", "Q", "H", "R", "Pi")}
                        loaded["heads"] = {k_: torch.load(ROOT / heads[k_]["file"], weights_only=True)
                                           for k_ in ("P4", "P8")}
                    cr = self.codes[:, :LEVELS_1_6]
                    out = evaluate_batch(self.model(), loaded["comps"], loaded["heads"],
                                         puzzle_tensor(self.puzzles[r]), puzzle_tensor(self.puzzles[d]), cr[r], cr[d],
                                         self.empty[r], self.empty[d], self.mask[r], self.mask[d])
                    return {"pair_index": self.order[idx], "pair_ids": np.array([self.ids[i] for i in self.order[idx]]),
                            "order": np.full(len(idx), oi), "conditions": np.array(CONDITIONS),
                            **{key: np.asarray(out[key]) for key in OUTCOMES},
                            **{f"diag_{key}": np.asarray(v) for key, v in out["diagnostics"].items()},
                            "invalid_reasons": np.array(out["invalid_reasons"], dtype=str)}

                z = self.stage(f"causal/{oname}_batch_{k}", self.rd / "causal" / f"{oname}_batch_{k}.npz", compute)
                directed[oi, idx] = z["directed"]
                for reason in z["invalid_reasons"].tolist():
                    if reason not in self.inv["B"]:
                        self.inv["B"].append(reason)
        self.pair_values = (directed[0] + directed[1]) / 2  # (ab + ba) / 2, processed order

    def decisions(self) -> dict:
        raw = np.empty(self.n, int)
        raw[self.order] = np.arange(self.n)  # raw index -> processed position

        def R(x):
            return np.asarray(x)[raw]

        ci = {c: i for i, c in enumerate(CONDITIONS)}
        pv = R(self.pair_values)
        v = {"Q": pv[:, ci["Q"]], "random_mean": pv[:, [ci[f"rand{j}"] for j in range(20)]].mean(1),
             "hv": pv[:, ci["hv"]], "shuf": pv[:, ci["shuf"]], "full_be": pv[:, ci["full_be"]]}
        w = {rep: {k: R(self.scores[rep][k]) for k in ("n_disc", "w", "w_pilot_rule")} for rep in ("P2", "z6")}
        ea, eb = R(self.elig_a), R(self.elig_b)
        check_finite("per_pair_A", w["P2"]["w"][ea], w["z6"]["w"][ea])
        check_finite("per_pair_B", *v.values())
        delta = w["P2"]["w"] - w["z6"]["w"]

        def compute():
            dec = decide(w["P2"]["w"], w["z6"]["w"], ea, v["Q"], v["random_mean"], v["hv"], v["shuf"], eb,
                         self.inv["A"], self.inv["B"])
            check_finite("decision_inputs", *(np.asarray(x) for x in dec["inputs"].values()))
            est = {"W_P2": w["P2"]["w"][ea], "W_Z": w["z6"]["w"][ea], "Delta": delta[ea], "Q": v["Q"][eb],
                   "Q_minus_random_mean": (v["Q"] - v["random_mean"])[eb], "Q_minus_hv": (v["Q"] - v["hv"])[eb],
                   "Q_minus_shuf": (v["Q"] - v["shuf"])[eb], "full_be": v["full_be"][eb]}
            return {"decision": dec, "bootstrap": {k: bootstrap(x) if x.size else None for k, x in est.items()}}

        dec = self.stage("decisions", self.rd / "decisions.json", compute, "json")
        rows = {}
        for i, pid in enumerate(self.ids):
            rows[pid] = _plain({"pair_index": i, "elig_a": ea[i], "elig_b": eb[i], "n_disc": w["P2"]["n_disc"][i],
                                "w_P2": w["P2"]["w"][i], "w_Z": w["z6"]["w"][i],
                                "w_pilot_rule_P2": w["P2"]["w_pilot_rule"][i], "w_pilot_rule_Z": w["z6"]["w_pilot_rule"][i],
                                "delta": delta[i], **{k: x[i] for k, x in v.items()}})
        excluded = {"A": [p for p, e in zip(self.ids, ea) if not e], "B": [p for p, e in zip(self.ids, eb) if not e]}
        return {"pairs": rows, **dec, "outcomes": dec["decision"]["outcomes"],
                "eligibility": {"n_a": int(ea.sum()), "n_b": int(eb.sum()), "excluded": excluded}}


# --- results and report --------------------------------------------------------------------------

def section8_rows(protocol_text: str) -> dict[str, list[str]]:
    """The §8 table of the protocol: first cell -> the row's three cells, verbatim."""
    sec = protocol_text.split("\n## 8.", 1)[1].split("\n## ", 1)[0]
    lines = [ln.strip() for ln in sec.splitlines() if ln.strip().startswith("| ")]
    return {cells[0]: cells for cells in ([c.strip() for c in ln[1:-1].split("|")] for ln in lines[1:])}


def select_rows(out_a: str, out_b: str, stopped: bool) -> list[str]:
    """§8 rows that apply to the two outcomes (first cells); the stop row when none applies."""
    if stopped:
        return [STOP_ROW]
    rows = []
    rows += {"holds": ["Claim A holds"], "not_shown": ["Claim A not shown (any of A1, A2 fails)"]}.get(out_a, [])
    rows += {"holds": ["Claim B holds"], "not_shown": ["Claim B not shown (any of B1–B4 fails)"]}.get(out_b, [])
    joint = {("holds", "holds"): "Claims A and B hold", ("holds", "not_shown"): "Claim A holds, claim B not shown",
             ("not_shown", "holds"): "Claim B holds, claim A not shown"}
    if (out_a, out_b) in joint:
        rows.append(joint[(out_a, out_b)])
    if out_b == "invalid" and out_a != "invalid":
        rows.append("Claim B invalid (§6), claim A valid")
    if out_a in ("invalid", "not_estimable") and out_b != "invalid":
        rows.append("Claim A invalid or not estimable, claim B valid")
    return rows or [STOP_ROW]


def report(mode: str, results: dict) -> str:
    table = section8_rows((CODE_ROOT / "e5_protocol_v1.md").read_text(encoding="utf-8"))
    out = results["outcomes"]
    keys = select_rows(out["A"], out["B"], results["status"] == "invalid")
    lines = [f"# E5 {mode} results", ""]
    if mode != "test":
        lines += [DRY_NOTE, ""]
    lines += [f"- Run status: {results['status']}", f"- Claim A outcome: {out['A']}", f"- Claim B outcome: {out['B']}"]
    dec = results.get("decision")
    if dec:
        lines += [f"- Conditions: {json.dumps({**dec['claim_a'], **dec['claim_b']})}", f"- log K: {json.dumps(dec['log_k'])}"]
    lines += [f"- Invalid reasons: {json.dumps(results['invalid_reasons'])}", "",
              "## Interpretation (protocol §8)", "",
              "Rows selected by the outcomes; text copied verbatim from `e5_protocol_v1.md` §8.", "",
              "| Result | Justified claim | Does not follow |", "|---|---|---|"]
    lines += ["| " + " | ".join(table[k]) + " |" for k in keys]
    return "\n".join(lines) + "\n"


def _finish(mode: str, rn: Runner | None, inputs: dict, inv: dict, status: str, body: dict, t0: float) -> str:
    outcomes = body.get("outcomes") or {"A": "invalid", "B": "invalid"}
    results = _plain({"note": DRY_NOTE if mode != "test" else "E5 TEST (protocol e5_protocol_v1.md)", "mode": mode,
                      "status": status, "n_pairs": rn.n if rn and hasattr(rn, "n") else None,
                      "sha256_ids_raw": subsets.sha256_ids(rn.ids) if rn and hasattr(rn, "ids") else None,
                      **body, "outcomes": outcomes, "invalid_reasons": inv, **(rn.info if rn else {}),
                      "inputs": inputs, "threads": torch.get_num_threads(), "batch": BATCH,
                      "code_state": code_state(), "environment": environment_record(),
                      "seconds": round(time.perf_counter() - t0, 1)})
    out = e5run.OUT_DIR[mode]
    atomic_json(out / "results.json", results)
    atomic_write(out / "report.md", report(mode, results))
    e5run.finish_run(mode, status, {"outcomes": outcomes, "invalid_reasons": inv})
    return status


def run(mode: str, resume: bool) -> str:
    t0 = time.perf_counter()
    torch.set_num_threads(THREADS)
    if torch.get_num_threads() != THREADS:
        raise SystemExit(f"torch.get_num_threads() = {torch.get_num_threads()} != {THREADS}; refusing to start")
    torch.use_deterministic_algorithms(True)
    P = _paths()
    lock_problem = None
    if mode == "test":
        try:
            e5run.require_lock(P["manifest"], P["dry_record"])  # LockError (not at the tag) refuses to start
        except e5run.DataIntegrityError as e:
            lock_problem = f"manifest_or_dry_record: {e}"
    inputs, expected = _inputs(mode, P)
    rec = e5run.start_run(mode, inputs, resume)
    inv = _start_checks(mode, P, inputs, expected, lock_problem)
    rn = Runner(mode, P, set(rec.get("stages") or {}), inv)
    try:
        if inv["shared"]:
            raise Stop("start hash checks")
        rn.pairs()
        rn.extract()
        rn.probes()
        rn.causal()
        body = rn.decisions()
    except NonFiniteError as e:
        inv["shared"].append(f"non_finite: {e}")
        return _finish(mode, rn, inputs, inv, "invalid", {}, t0)
    except Stop:
        return _finish(mode, rn, inputs, inv, "invalid", {}, t0)
    return _finish(mode, rn, inputs, inv, "finished", body, t0)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=tuple(e5run.RUN_DIR))
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args(argv)
    status = run(args.mode, args.resume)
    print(json.dumps(_json(e5run.OUT_DIR[args.mode] / "results.json")["outcomes"]), status, flush=True)
    sys.exit(0 if status == "finished" else 1)


if __name__ == "__main__":
    main()
