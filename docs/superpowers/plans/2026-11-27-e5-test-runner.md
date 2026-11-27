# E5 TEST runner, PROBE-VAL dry run and lock manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the frozen E5 TEST runner of `e5_protocol_v1.md` (§4–§6, §9.3), its PROBE-VAL dry run with the exact pass rule (§9.4), the synthetic end-to-end tests (§9.5) and the hash manifest (§9.2, §10), so that the protocol can be locked.

**Architecture:** Pure, model-free logic (pair screening, eligibility, within-pair scoring, decisions, outcomes) lives in `ncm_sudoku.e5test`; the model-dependent causal batch with every §6 check lives in `ncm_sudoku.e5batch`; run-directory, input-hash, lock and resume rules live in `ncm_sudoku.e5run`. One CLI runner `scripts/e5_test.py --mode dry|test` drives the stages; `scripts/e5_dry_check.py` applies the §9.4 pass rule and writes the approved dry-run record; `scripts/e5_manifest.py` writes the §10 manifest. The pilot scripts stay unchanged (they are the reference the dry run must reproduce).

**Tech Stack:** Python 3.12 (uv), numpy, torch (FP32, CPU, eager, deterministic, 4 threads), pytest; existing modules `e5pairs`, `e5extract`, `e5causal`, `e5stats`, `probes`, `labels`, `symmetry`, `subsets`, `wp2` (atomic writes, `file_sha256`).

**Spec:** [e5_protocol_v1.md](../../../e5_protocol_v1.md) (D107); decisions D91–D108 in `DECISIONS.md`.

## Global Constraints

- N = 400 TEST pairs, seed namespace `PAIR_SEEDS["pairs_test"]` = 10, pair ids `e5pair-v1-10-<index>`; `n_plan = 400` in every `e5stats` call, also in dry mode.
- Threads: `torch.set_num_threads(4)` at start; the runner refuses to start if `torch.get_num_threads() != 4` afterwards.
- Batch layout (§4.4): extraction batches of 50 puzzles, all a-members in raw order, then all b-members; probe inference in batches of 50 puzzles (a-members, then b-members, cells in grid order); causal batches of 50 recipients, order "ab" for all pairs, then "ba"; last batch shorter as is.
- Prefix activations stored as fp16 and read back as fp32; Z<=6 states fp32; donors captured online in fp32 (never from saved fp16).
- Claim-A prediction: per seed the float32 `Linear + Sigmoid` output of the shared head (input `probes.build_inputs`), averaged over seeds 0, 1, 2 with `np.mean(np.stack(per_seed), axis=0)` in float32 (as the pilot), compared in float64.
- Directed effect: `tv(p_clean, p_full) - tv(p_cond, p_full)` with `e5causal.tv` (mean over the 18 queries inside `tv`), in that operation order; pair value = (ab + ba) / 2.
- Zero rule threshold `1e-12 * max(s, 1)` (`e5causal.norm_matched`); high-variance invariance `max_d |(W step)_d| <= 1e-8 * ||W||_F * ||step||_2`; shuffled direction cosine `>= 1 - 1e-8`.
- Outcomes per claim: `holds`, `not_shown`, `not_estimable`, `invalid`. Any non-finite value stops the run and makes both claims invalid.
- Frozen inputs: `runs/e5/lock/{z6.pt,W.npy,Q.npy,H.npy,R.npy,Pi.npy}` and `runs/e5/causal/heads/{P2,P4,P8}.pt`, hashes from `experiments/e5/lock/components.json` and `experiments/e5/causal/heads.json`.
- TEST mode starts only at the lock tag `e5-prereg-v1` (HEAD equals the tag commit, code clean, upstream submodule clean at the pinned commit), with a verified manifest and a verified approved dry-run record; dry mode never imports or calls the TEST pair generation path.
- English in every file; no invented numbers; writes only through `wp2.atomic_json`, `wp2.atomic_npy`, `wp2.atomic_write`.

## Review Focus

1. A batch-size or position dependence of probe or causal outputs: the dry-run reordering (permutation j -> (19 j + 1) mod 250) must leave every per-pair value bit-identical; pinned in Task 6 and Task 7.
2. A pair excluded for claim A (no discordant bit) still entering a claim-A mean, or its row being dropped from probe inference batches: pinned in Task 2 (`eligibility`, `decide` with `n_A < 400`).
3. An interrupted run resumed with a changed input (thread count, head file, pair list): pinned in Task 4 (`test_resume_refuses_changed_inputs`).
4. A claim-B check failure in one batch being lost when later batches pass: pinned in Task 3 (`invalid_reasons` accumulate per batch) and Task 5.
5. A TEST-mode start without the tag or with an unapproved dry record: pinned in Task 4 (`test_test_mode_requires_lock`).

---

### Task 1: Pair screening, internal collisions and eligibility

**Files:**
- Create: `src/ncm_sudoku/e5test.py`
- Test: `tests/test_e5test.py`

**Interfaces:**
- Consumes: `e5pairs.generate_pair(seed, index) -> Pair` (fields `pair_id`, `a`, `b`, `solution`), `symmetry` canonical form as used by `symmetry.screen_canonical`.
- Produces:
  - `canonical_key(solution: np.ndarray) -> bytes` (the exact canonical form used by `screen_canonical`; reuse its internal function, do not re-implement).
  - `external_index(entries: dict[str, list[tuple[str, np.ndarray]]]) -> dict[bytes, str]` (canonical key -> first external id, built once).
  - `screen_pairs(make_pair: Callable[[int], Pair], index: dict[bytes, str], n: int) -> tuple[list[Pair], list[dict]]`: raw index from 0; a pair whose solution key is in `index` is rejected; log rows `{"index", "pair_id", "accepted", "reason", "colliding_id"}` (`reason` is `"external_collision"` or `None`); stops at the n-th accepted pair; any exception from `make_pair` propagates (a generation error stops the run).
  - `internal_collisions(pairs: list[Pair]) -> list[tuple[str, str]]`: every pair of pair ids with equal solution keys.
  - `eligibility(mask: np.ndarray, empty: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]`: members stacked a then b (`mask` (2n, 81, 9) bool, `empty` (2n, 81) bool); returns `elig_a` (n,) = at least one both-empty cell with a digit that is a candidate in exactly one member; `elig_b` (n,) = at least one both-empty cell.

- [ ] **Step 1: Write the failing tests**

```python
def test_screen_rejects_external_collisions_steps_and_logs(): ...
    # fake make_pair with solutions s0, s1(external), s2, s3; n=3
    # -> accepted ids [0, 2, 3]; log has 4 rows; row 1 has accepted False,
    #    reason "external_collision", colliding_id the external id
def test_screen_propagates_generation_errors(): ...   # make_pair raises at index 1 -> pytest.raises
def test_internal_collisions_lists_both_ids(): ...    # two pairs with a relabelled (same-orbit) solution -> [(id_x, id_y)]
def test_eligibility_from_labels(): ...               # pair with identical clue masks on all both-empty cells' candidates -> elig_a False, elig_b True
```

- [ ] **Step 2: Run** `uv run --locked pytest -q tests/test_e5test.py` — Expected: FAIL (module missing).
- [ ] **Step 3: Implement** the five functions in `src/ncm_sudoku/e5test.py` (module docstring cites protocol §4.1).
- [ ] **Step 4: Run** the same command — Expected: PASS.
- [ ] **Step 5: Commit** `feat(e5): TEST pair screening, collisions and eligibility`.

### Task 2: Within-pair scoring, probe inference, decisions and outcomes

**Files:**
- Modify: `src/ncm_sudoku/e5test.py`
- Test: `tests/test_e5test.py`

**Interfaces:**
- Consumes: `e5stats.claim_a`, `e5stats.claim_b`, `e5stats.to_unit`; `probes.build_inputs`; head files as lists of three state dicts (keys `0.weight`, `0.bias`).
- Produces:
  - `check_finite(name: str, *arrays) -> None`: raises `NonFiniteError(name)` (subclass of `RuntimeError`) on any non-finite element.
  - `head_probs(state_dicts: list[dict], features: np.ndarray, empty: np.ndarray, batch: int = 50) -> tuple[np.ndarray, np.ndarray]`: per-seed float32 probabilities (3, n_rows, 9) and their float32 seed mean scattered to (n_puzzles, 81, 9) float64 with NaN on given cells; inputs built per batch of `batch` puzzles in the given row order.
  - `pair_scores(pred: np.ndarray, mask: np.ndarray, empty: np.ndarray, same_input: np.ndarray, n: int) -> dict`: per pair `n_disc` (int), `w` (float, NaN if `n_disc == 0`); score 1 / 0 / 0.5 as in `e5pilot.w_auc`, and 0.5 wherever `same_input[i, cell]` (bit-identical probe input vectors of the two members at that cell) regardless of predictions; also `w_pilot_rule` without the identical-input rule (for the §9.4 report).
  - `same_inputs(features: np.ndarray, n: int) -> np.ndarray`: (n, 81) bool, `np.array_equal` of the members' feature rows per cell.
  - `decide(w_p2, w_z, elig_a, q, rand, hv, shuf, elig_b, invalid_a: list[str], invalid_b: list[str]) -> dict`: claim inputs in raw index order over eligible pairs; `n_plan=400`; outcome per claim `invalid` if its invalid list is non-empty, else `not_estimable` if no eligible pair, else `holds` / `not_shown`; also the ordered decision input vectors (A1 lower, A1 upper, A2 on the `to_unit` scale, B1–B4) and every condition's log K.
  - `bootstrap(x: np.ndarray) -> dict` (95% percentile, 10,000 resamples, seed 0, `degenerate` flag; same as `scripts/e5_causal.py`).

- [ ] **Step 1: Write the failing tests**

```python
def test_pair_scores_identical_inputs_score_half_even_with_1ulp_prediction_gap(): ...
def test_pair_scores_match_pilot_w_auc_without_identical_inputs(): ...  # vs e5pilot.w_auc per_pair on random data
def test_head_probs_seed_mean_is_float32_like_pilot(): ...             # equals np.mean(np.stack(per_seed), 0) bit for bit
def test_head_probs_independent_of_batch_size(): ...                   # batch 50 vs batch 7 on a small fake head: equal arrays
def test_decide_hand_computed_case(): ...
    # 3 eligible pairs with n_disc 1, 4, 9 and w_p2 [1, 1, 0.75], w_z [0.5, 0.5, 0.5]:
    # equal pair weight -> mean Delta = (0.5 + 0.5 + 0.25) / 3; decision inputs equal to_unit(w_p2 - w_z) in order
def test_decide_n_a_below_400_uses_only_eligible_pairs_and_n_plan_400(): ...
def test_decide_outcomes_invalid_and_not_estimable(): ...              # invalid_b non-empty -> B "invalid"; no eligible A pair -> A "not_estimable"
def test_check_finite_raises_on_nan_and_inf(): ...
```

- [ ] **Step 2: Run** `uv run --locked pytest -q tests/test_e5test.py` — Expected: the new tests FAIL.
- [ ] **Step 3: Implement** the functions; `decide` calls `e5stats.claim_a(..., n_plan=400)` and `claim_b(..., n_plan=400)` on the eligible rows and reads log K through `e5stats.betting_logk` with the §5.3 boundaries.
- [ ] **Step 4: Run** — Expected: PASS.
- [ ] **Step 5: Commit** `feat(e5): within-pair scoring, probe inference and claim decisions`.

### Task 3: Causal batch with every §6 check

**Files:**
- Create: `src/ncm_sudoku/e5batch.py`
- Test: `tests/test_e5batch.py`

**Interfaces:**
- Consumes: `e5causal.{Level7Hooks, isolation_check, project_step, norm_matched, shuffled_raw, code_probs, tv, head_logits}`, `intervene.level_logits`, `e5extract.PREFIX_CELLS`, components dict `{"W", "Q", "H", "R" (20, 512, 9), "Pi"}`, heads dict `{"P4", "P8"}`.
- Produces: `evaluate_batch(m, comps: dict, heads: dict, pr, pd, cr, cd, empty_r, empty_d, mask_r, mask_d) -> dict` with
  - `directed` (B, 25) float64 in the column order `["Q", "rand0".."rand19", "hv", "shuf", "full_be", "full_input"]` (`CONDITIONS`, a module constant), plus `undirected`, `argmax_changes`, `shift4`, `shift8`, `flip4`, `flip8` as in `scripts/e5_causal.py`;
  - `invalid_reasons: list[str]` (empty when every check passed), with these reason strings: `hook_count`, `capture_only_identity`, `self_donor_cells`, `self_donor_prefix91`, `written_rows`, `untouched_rows`, `zero_rule`, `hv_invariance`, `shuffled_direction`;
  - `diagnostics`: target norms, actual norms `||x_after - x_before||`, scale factors, step–Delta cosines.
- Order of calls per batch (fixed): plain clean `level_logits` (no hook, count 0); capture call on recipient (hook count 1, logits must equal plain); capture call on donor with its own codes `cd` (count 1); self-donor at both-empty cells; self-donor at all 91 prefix positions (a `Level7Hooks(m.net, np.arange(91))` patch with the recipient's own rows); full swap; each condition in `CONDITIONS` order; `full_input` = `level_logits(m, pd, cr, 7)` under a capture-only hook. Values written: `(x_r64 + step).astype(np.float32)` at both-empty cells, `x_d` for the full swap; `ValueError` from `norm_matched` is caught and recorded as `zero_rule` (the batch continues with a zero step for that row so that the pair is not dropped).

- [ ] **Step 1: Write the failing tests** (slow, real model, 4 released puzzles as recipients and their row-reversed order as donors, as in `tests/test_e5causal.py`)

```python
@pytest.mark.slow
def test_evaluate_batch_passes_all_checks_on_real_pairs(model, released): ...   # invalid_reasons == []
@pytest.mark.slow
def test_evaluate_batch_reports_injected_failures(model, released, monkeypatch): ...
    # monkeypatch e5batch.project_step for "hv" to add a W-row component -> "hv_invariance";
    # monkeypatch norm_matched to raise -> "zero_rule"; tamper the written value by 1 ulp -> "written_rows"
def test_conditions_constant(): ...  # 25 names in the pilot order
```

- [ ] **Step 2: Run** `uv run --locked pytest -q -m slow tests/test_e5batch.py` — Expected: FAIL (module missing).
- [ ] **Step 3: Implement** `evaluate_batch` in `src/ncm_sudoku/e5batch.py`; every logits, probability, step and outcome array goes through `e5test.check_finite`.
- [ ] **Step 4: Run** — Expected: PASS.
- [ ] **Step 5: Commit** `feat(e5): causal batch evaluation with protocol §6 checks`.

### Task 4: Run directory, input hashes, lock gate and resume

**Files:**
- Create: `src/ncm_sudoku/e5run.py`
- Test: `tests/test_e5run.py`

**Interfaces:**
- Consumes: `wp2.atomic_json`, `wp2.file_sha256`, `wp2.freeze_state`-style git queries (reuse `wp2._git` pattern; do not import WP2 role logic).
- Produces:
  - `LOCK_TAG = "e5-prereg-v1"`; `RUN_DIR = {"dry": runs/e5/dry, "dry_perm": runs/e5/dry_perm, "test": runs/e5/test}`; `OUT_DIR` likewise under `experiments/e5/`.
  - `input_hashes(paths: dict[str, Path]) -> dict[str, str]`.
  - `start_run(mode: str, inputs: dict[str, str], resume: bool) -> dict`: creates `RUN_DIR[mode]/run.json` (`status` "running", inputs, threads, start time, `stages` {}); a single-writer lock file `RUN_DIR[mode]/.lock` (exclusive create; refuse if present); refuses if a `run.json` with `status` "finished" or "invalid" exists; with `resume`, requires `status` "running" and identical `inputs` and threads, and re-hashes every partial output listed in `stages`.
  - `record_output(mode, stage: str, path: Path) -> None`: atomic write already done by the caller; stores the file hash in `run.json`.
  - `finish_run(mode, status: str, summary: dict) -> None` (`status` "finished" or "invalid"; removes the lock).
  - `lock_state() -> dict` and `require_lock(manifest: Path, dry_record: Path) -> None` for TEST mode: tag exists, HEAD equals the tag commit, `git status --porcelain` clean, `third_party/ncm` at the pinned commit and clean, every manifest hash recomputed equal, every hash listed in the dry record recomputed equal and `passed` true.

- [ ] **Step 1: Write the failing tests** (`tmp_path` and monkeypatched `RUN_DIR`)

```python
def test_finished_run_is_never_rerun(): ...
def test_resume_refuses_changed_inputs(): ...        # changed head hash or threads -> raises
def test_resume_refuses_changed_partial_output(): ... # tampered stage file -> raises
def test_single_writer_lock(): ...                   # second start while .lock exists -> raises
def test_test_mode_requires_lock(monkeypatch): ...   # no tag / dirty tree / manifest mismatch / dry record not passed -> raises
```

- [ ] **Step 2: Run** `uv run --locked pytest -q tests/test_e5run.py` — Expected: FAIL.
- [ ] **Step 3: Implement** `src/ncm_sudoku/e5run.py`.
- [ ] **Step 4: Run** — Expected: PASS.
- [ ] **Step 5: Commit** `feat(e5): run records, lock gate and resume rules for the TEST runner`.

### Task 5: Runner script

**Files:**
- Create: `scripts/e5_test.py`
- Test: `tests/test_e5_test_script.py`

**Interfaces:**
- Consumes: Tasks 1–4; `e5extract.extract_batch`; `e5pairs.generate_pair`; `e5pilot.load_subset` (dry mode only); `labels.candidate_mask` via `e5probes.candidate_targets`.
- Produces: `uv run --locked python scripts/e5_test.py --mode dry|dry_perm|test [--resume]`.
  - `dry`: pairs from `runs/e5/pairs/probe_val/` checked against `experiments/e5/pairs.json` (`sha256_ids` of the ids and `sha256_array` of `a`, `b`, `solutions`); raw order.
  - `dry_perm`: as `dry`, with the pair order j -> pair `(19 * j + 1) % 250` (`PERMUTATION`, a module constant; every pair changes its in-batch position, and no new batch shares more than 11 of 50 members with an old batch); outputs are written per pair id.
  - `test`: `require_lock`, then `screen_pairs` on namespace 10 against the external index built from every earlier dataset (gate, CAL, PROBE-TRAIN, PROBE-VAL, WP2 TEST, released hard set, E5 PROBE pairs), `internal_collisions` (any -> both claims invalid, both ids logged, no redraw).
  - Stages, each written atomically under `RUN_DIR[mode]` and recorded: `pairs` (ids, arrays, screening log), `extract/<member>/batch_<k>.npz` (every array `extract_batch` returns: codes, solved, prefix cells of layers 0–8 and closing BOS fp16, level-7 query activations fp16, z6 and z6_teacher fp32; the §7 secondary analyses need them), `probes` (per-seed and mean predictions for P2 and Z<=6), `causal/<order>_batch_<k>.npz` (per recipient: pair index, order, `directed` etc., invalid reasons), `decisions`.
  - Output `OUT_DIR[mode]/results.json`: per-pair rows by pair id (n_disc, W(P2), W(Z), `w_pilot_rule` for both, Delta, the five causal per-pair values Q, random mean, hv, shuf, full_be), ordered decision inputs, log K per condition, outcomes, bootstrap intervals, eligibility counts and excluded ids, screening counts, invalid reasons, hashes of every input, threads, code state; and `report.md` with the §8 interpretation row selected by the outcomes (text copied from protocol §8, no new claims).
  - Extraction checks (§6): per batch, 9 captured layers of shape (B, 9, 81, d), codes equal to a clean `generate_codes` call on the same batch (dry mode and the first TEST batch of each member), z6 shape (B, 81, 256); any failure -> both claims invalid.

- [ ] **Step 1: Write the failing tests** (model-free, with `monkeypatch` replacing `extract_batch` and `evaluate_batch` by deterministic fakes that return fixed arrays)

```python
def test_dry_mode_never_touches_test_generation(monkeypatch): ...  # generate_pair patched to raise -> dry run completes
def test_stage_outputs_are_keyed_by_pair_id_under_permutation(monkeypatch): ...
def test_non_finite_extraction_stops_with_both_claims_invalid(monkeypatch): ...
def test_claim_b_failure_in_one_batch_survives_later_batches(monkeypatch): ...
def test_permutation_property(): ...  # every in-batch position changes; max overlap with an old batch <= 11
```

- [ ] **Step 2: Run** `uv run --locked pytest -q tests/test_e5_test_script.py` — Expected: FAIL.
- [ ] **Step 3: Implement** `scripts/e5_test.py` (docstring with usage, stages and outputs, as the other scripts).
- [ ] **Step 4: Run** — Expected: PASS; then `uv run --locked pytest -q` — Expected: all pass.
- [ ] **Step 5: Commit** `feat(e5): TEST runner with dry and permuted dry modes`.

### Task 6: Dry run and the §9.4 pass rule

**Files:**
- Create: `scripts/e5_dry_check.py`
- Test: `tests/test_e5_dry_check_script.py`

**Interfaces:**
- Consumes: `experiments/e5/dry/results.json`, `experiments/e5/dry_perm/results.json`, `runs/e5/pilot/{P2,z6}__shared__none.npy`, `runs/e5/causal/primary.npz`, PROBE-VAL activations (for `same_inputs`).
- Produces: `experiments/e5/dry/check.json` with `passed` and the parts:
  - (a) `ids_hash`: `sha256_ids` of the dry ids equals `pairs.json` `subsets.probe_val.sha256.ids`;
  - (b) claim A: per pair id, `n_disc`, W(P2), W(Z), Delta of the dry run equal `pair_scores` applied to the saved pilot predictions (exact), and the ordered A decision inputs equal;
  - (c) claim B: per (pair index, order, condition) the dry `directed` values equal `primary.npz` (`meta[:, 0]` pair index, `meta[:, 1]` order 0 = ab), then the pair means and the ordered B inputs;
  - (d) the dry run's `invalid_reasons` are empty for both claims;
  - (e) per pair id, every value of (b) and (c) in `dry_perm` equals `dry`;
  - `tie_rule_effect`: pair ids where `w` differs from `w_pilot_rule` (reported, not a gate);
  - `hashes`: SHA-256 of the three reference files, the ordered id list (`sha256_ids`), the heads and components, `scripts/e5_test.py`, `src/ncm_sudoku/{e5test,e5batch,e5run,e5stats,e5causal,e5extract,probes}.py`, and both results files; the record's own hash is written to `experiments/e5/dry/check.sha256`.

- [ ] **Step 1: Write the failing tests** with small synthetic results and reference files in `tmp_path`: all equal -> `passed`; one per-pair value off by 1 ulp -> part (b) fails; ab and ba swapped for one pair -> part (c) fails though pair means agree.
- [ ] **Step 2: Run** `uv run --locked pytest -q tests/test_e5_dry_check_script.py` — Expected: FAIL.
- [ ] **Step 3: Implement** `scripts/e5_dry_check.py`.
- [ ] **Step 4: Run** — Expected: PASS.
- [ ] **Step 5: Run the real dry runs** (commit the code first so the record names a clean commit): `uv run --locked python scripts/e5_test.py --mode dry`, then `--mode dry_perm`, then `uv run --locked python scripts/e5_dry_check.py`. Expected: `passed: true`. If any part fails: stop, report the part and the first differing pair to the user; do not change a tolerance.
- [ ] **Step 6: If `tie_rule_effect` is non-empty** (a pilot primary value changed): add `--rows <results.json>` to `scripts/e5_power.py` (load the per-pair rows by pair id from the dry results instead of the pilot JSON files, record their hash), re-run it to `experiments/e5/power_final.json`, and check power >= 0.9 for both claims at N = 400 in the grid point and its re-check. Below 0.9: stop, no lock (protocol §9.4).
- [ ] **Step 7: Commit** code, `experiments/e5/dry*/results.json`, `report.md`, `check.json`, `check.sha256`; log D109 in `DECISIONS.md` with the dry-run outcome.

### Task 7: Secondary components and the hash manifest

**Files:**
- Create: `scripts/e5_manifest.py`
- Test: `tests/test_e5_manifest_script.py`

**Interfaces:**
- Consumes: `experiments/e5/lock/components.json`, `experiments/e5/causal/heads.json`, `experiments/e5/dry/check.json`, `experiments/provenance/checkpoints.json`, `subsets.FROZEN_SHA256`, `experiments/e5/pairs.json`.
- Produces: `experiments/e5/lock/manifest.json`: entries `{name, path, format, sha256, retrieval}` with `format` one of `file`, `sha256_ids`, `sha256_array`; covers protocol §10: the protocol file, checkpoint files, generator guard files, screening corpus (ids by `sha256_ids`, solution arrays by `sha256_array`, with the script and seed that reconstruct each), PROBE pair arrays, primary heads, P4/P8 heads, Q, H, R, Pi, W, the secondary components as the file SHA-256 of `scripts/e5_pilot.py` and `scripts/e5_pilot_ref.py` (they refit them deterministically on PROBE data; protocol §4.3 allows this), the runner and every `src/ncm_sudoku/*.py`, `uv.lock`, the dry-run record and its hash. `--verify` recomputes every entry and exits non-zero on the first mismatch.

- [ ] **Step 1: Write the failing tests**: `--verify` passes on a fresh manifest in `tmp_path`; a one-byte change of a listed file fails naming that entry; an id list is hashed with `sha256_ids`, never `sha256_array`.
- [ ] **Step 2: Run** `uv run --locked pytest -q tests/test_e5_manifest_script.py` — Expected: FAIL.
- [ ] **Step 3: Implement** `scripts/e5_manifest.py`.
- [ ] **Step 4: Run** — Expected: PASS; then `uv run --locked python scripts/e5_manifest.py` and `--verify` — Expected: exit 0.
- [ ] **Step 5: DOX pass and commit**: `scripts/AGENTS.md` (the three new scripts), `src/ncm_sudoku/AGENTS.md` (`e5test`, `e5batch`, `e5run`), root `AGENTS.md` (`experiments/e5/` index: `dry/`, `dry_perm/`, `lock/manifest.json`; `runs/e5/{dry,dry_perm,test}/`), `ROADMAP.md`; commit `feat(e5): lock manifest`.

### Afterwards (user steps, not code)

- Restoration check from a clean clone (protocol §10): clone, `uv sync --locked`, fetch checkpoints, regenerate the git-ignored artifacts by the recipes, `scripts/e5_manifest.py --verify`.
- The §7 secondary and exploratory analyses are computed after TEST by a separate script from the saved raw outputs, reported as non-confirmatory; they are not part of this plan.
- Tag `e5-prereg-v1` on the commit that contains the manifest, OSF registration with the protocol, the manifest and the §2 summary; only then `scripts/e5_test.py --mode test`.
