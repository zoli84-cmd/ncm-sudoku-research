# WP1: Distribution Gate, E1, and E2 Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the terminal distribution gate on the frozen generator, produce E1 (tokenizer vs generator) results on the released boards and on CAL, and run the non-confirmatory E2 pilot (four branches, levels 1/2/6/11, dose grid, two replacement policies) with the summaries the preregistration lock needs.

**Architecture:** Small focused modules in `src/ncm_sudoku/` (`subsets`, `gate`, `e1`, `perturb`, `e2`) on top of WP0 (`generate`, `labels`, `validate`, `runner`, `states`, `intervene`). One script per stage writes committed summaries to `experiments/wp1/` and raw records to `runs/wp1/`.

**Tech Stack:** Python 3.12 (uv, native Windows), torch 2.15 CPU, numpy, pytest.

**Spec:** `research_plan_v3.5.md` §4, §4.1, §6, §7, §11.1–§11.2, §12.1; `DECISIONS.md` D27, D31–D40.

## Global Constraints

- Run order (D32): E1 on released → gate (seed namespace 1, n=1,000) → CAL (seed namespace 2, n=300) → E1 on CAL → E2 pilot.
- Generator is frozen (D33): never edit `generate.py` or `solve.py`; scripts assert their SHA-256 against D33 before generating.
- Seed namespaces (D36): gate 1, CAL 2 (PROBE-TRAIN 3, PROBE-VAL 4, SELECT 5, TEST 6, E4-TEST 7 reserved, not generated). Puzzle ids stay `gen-v1-{seed}-{index}`.
- Gate thresholds (D34, D35) are constants in code, written before the validation batch is drawn; the gate runs once; no retry, enlargement or pooling.
- E2 uses `run_branches`/`continue_generation` from WP0; branches of one configuration share one batch tensor (D20). Own validator (`validate.evaluate`) defines solve.
- Pilot outputs are labelled non-confirmatory; TEST is not generated.
- Levels are 1-indexed in all outputs.

## Review Focus

1. Gate decided on the wrong side of a margin or with the wrong reference (released benchmark is the fixed 86.3%, margin ±5 pp, 90% interval) → `test_model_gate_outcomes` covers equivalent / not equivalent / inconclusive at boundary values (Task 2).
2. Frequency-based replacement returning the original value or drawing from zero-mass codes → `test_frequency_excludes_original` and `test_ineligible_when_no_alternative` (Task 4).
3. Dose grid mismatching D38 → `test_dose_grid` pins {1}, {1,2,4}, {1,4,11,21}, and level 1 → {1} (Task 4).
4. θ₂ / θ_comp averaging in the wrong order (must average seeds within puzzle first, then puzzles; common eligible population) → `test_theta_estimators_on_toy_records` (Task 5).
5. Duplicate or symmetry-equivalent solutions slipping across subsets → `test_signature_invariant_under_symmetries` and `test_screen_flags_duplicates` (Task 1).

---

### Task 1: Subsets, seed namespaces, duplicate screening

**Files:** Create `src/ncm_sudoku/subsets.py`, `tests/test_subsets.py`.

**Interfaces — Produces:**
- `SEEDS: dict[str, int] = {"gate": 1, "cal": 2, "probe_train": 3, "probe_val": 4, "select": 5, "test": 6, "e4_test": 7}`; `DEV_SEED = 20261109`.
- `FROZEN_SHA256: dict[str, str]` with the D33 hashes of `generate.py` and `solve.py`; `assert_generator_frozen() -> None` raises `RuntimeError` on mismatch.
- `generate_subset(name: str, n: int) -> list[GeneratedPuzzle]` = `generate_many(SEEDS[name], n)` after `assert_generator_frozen()`.
- `solution_signature(solution: np.ndarray) -> tuple` — invariant under digit relabeling, row/column permutations within bands/stacks, band/stack permutations, transposition: for every box, each mini-row (and separately each mini-column) is a 3-digit set; count for each set how many other boxes in the same band (stack for mini-columns) contain the same set as a mini-row (mini-column); signature = sorted pair of (sorted multiset of mini-row counts, sorted multiset of mini-column counts).
- `screen(subsets: dict[str, list[GeneratedPuzzle]], released_solutions: np.ndarray) -> dict` with `exact_duplicates` and `signature_collisions` (lists of id pairs across and within subsets, released included).

- [ ] Step 1: tests — `test_seed_namespaces` (values above); `test_assert_generator_frozen_passes`; `test_signature_invariant_under_symmetries` (signature of `S` equals signature after digit relabeling, row swap in a band, band swap, column swap in a stack, transposition); `test_signature_differs` (two generated solutions with different signatures for seeds (2,0),(2,1)); `test_screen_flags_duplicates` (a subset containing the same puzzle twice → one exact duplicate; a relabeled copy → one signature collision).
- [ ] Steps 2–4: FAIL → implement → PASS (`uv run pytest -q`).
- [ ] Step 5: commit `feat: subsets, seed namespaces, duplicate screening`.

### Task 2: Distribution gate

**Files:** Create `src/ncm_sudoku/gate.py`, `scripts/wp1_gate.py`, `tests/test_gate.py`; output `experiments/wp1/gate.json`.

**Interfaces — Consumes:** `labels.inference_waves`, `labels.naked_singles`, `labels.hidden_singles`, Task 1, `runner.generate_codes`, `runner.decode_codes`, `validate`.
**Produces:**
- Constants (D34, D35): `TVD_MAX = 0.05`, `STUCK_SHARE_MAX_PP = 5.0`, `INITIAL_SINGLES_MAX = 1.0`, `BENCHMARK_PCT = 86.3`, `MARGIN_PP = 5.0`, `CI_LEVEL = 0.90`, `GATE_N = 1000`.
- `depth_profile(puzzles) -> dict` with `cell_depth_dist` (shares of blank cells in categories `"1","2","3",">=4","stuck"`), `stuck_puzzle_share`, `mean_initial_singles` (union of naked and hidden single cells in the initial state).
- `model_free_gate(fresh: dict, released: dict) -> dict` (`tvd`, differences, booleans per criterion, `passed`).
- `wilson_interval(k: int, n: int, level: float) -> tuple[float, float]` (proportions).
- `model_gate(solves: np.ndarray) -> dict` with `fresh_pct`, `diff_pp`, `ci_pp` (Wilson 90% of fresh minus 86.3), `outcome` in {`"equivalent"`, `"not_equivalent"`, `"inconclusive"`}: equivalent if the interval lies inside (−5, +5); not_equivalent if it lies entirely outside [−5, +5]; else inconclusive.
- `wp1_gate.py`: refuses to run if `experiments/wp1/gate.json` exists (single look); generates the gate batch (seed namespace 1, n=1,000), depth profiles of gate batch and released boards, model-free gate, model generation + own-validator solve, model gate, screen against released; writes `gate.json` with all of it plus timings.

- [ ] Step 1: tests — `test_depth_profile_categories` (on `[P, INKALA]`: shares sum to 1, `stuck_puzzle_share == 0.5`); `test_model_free_gate` (identical profiles pass; tvd 0.06 fails); `test_wilson_interval` (k=50, n=100 at 0.90 equals (0.4188, 0.5812) within 1e-3); `test_model_gate_outcomes` (solve array with 863 of 1,000 true → equivalent; 800/1000 → not_equivalent since interval below 81.3; a borderline count where the interval crosses −5 → inconclusive; compute the borderline count in the test from the Wilson function).
- [ ] Steps 2–4: FAIL → implement → PASS.
- [ ] Step 5: commit `feat: distribution gate` (before running it).
- [ ] Step 5b: pre-run gate review (the gate is a single look, D27): a fresh-context reviewer (most capable model) reads only `src/ncm_sudoku/gate.py`, `scripts/wp1_gate.py`, `tests/test_gate.py` and D34–D36, and checks thresholds, the fixed 86.3% reference, interval direction and outcome logic, seed namespace, and the single-look guard. Any Critical/Important finding is fixed (test RED→GREEN) before Step 6; the review result goes to the ledger.
- [ ] Step 6: after Task 3 Step 6 (E1 released) has run, run `uv run python scripts/wp1_gate.py` (≈ 25 min); record the outcome as D41 in `DECISIONS.md`; commit `data: WP1 distribution gate result`.

### Task 3: E1 tokenizer vs generator

**Files:** Create `src/ncm_sudoku/e1.py`, `scripts/wp1_e1.py`, `tests/test_e1.py`; outputs `experiments/wp1/e1_released.json`, `experiments/wp1/e1_cal.json`.

**Interfaces — Consumes:** `runner.generate_codes/decode_codes/teacher_codes`, `states.cumulative_states/decode_state`, `validate`, `model.level_slices`.
**Produces:** `e1_summary(m, puzzles, solutions, batch_size=128) -> dict` with:
- `teacher`: reconstruction exact-match share and cell accuracy of decoded teacher codes vs solution tokens;
- `generated`: means of `validate.evaluate` fields (own) for the generated output;
- `per_level`: for ℓ = 1..12, (a) share of positions where generated code equals teacher code within level ℓ, (b) decoding of the generated cumulative state Z≤ℓ: cell accuracy vs reference solution on all and on blank cells, solve share, format-error share;
- `hamming`: mean token Hamming and mean cell Hamming between decoded teacher output and decoded generated output;
- `n`.
`wp1_e1.py --subset released|cal` runs it (CAL read from Task 1 `generate_subset("cal", 300)`).

- [ ] Step 1: slow test `test_e1_summary_small` (4 released puzzles): keys present; `per_level` has 12 entries; level 12 decoding solve share equals `generated["solve"]`; teacher exact share is 1.0.
- [ ] Steps 2–4: FAIL → implement → PASS.
- [ ] Step 5: commit `feat: E1 tokenizer vs generator summary`.
- [ ] Step 6: run `uv run python scripts/wp1_e1.py --subset released` (≈ 45 min); commit the JSON.
- [ ] Step 7 (after the gate, Task 2 Step 6): run `--subset cal`; commit.

### Task 4: Perturbation policies and dose grid

**Files:** Create `src/ncm_sudoku/perturb.py`, `tests/test_perturb.py`.

**Interfaces — Produces:**
- `dose_grid(n_level: int) -> list[int]` = sorted distinct values of {1, ⌈0.05n⌉, ⌈0.15n⌉, ⌈0.30n⌉} within 1..n.
- `code_frequencies(codes: torch.Tensor, levels) -> list[torch.Tensor]` — per level, the share of each of the 16 code values among all positions of that level across the batch.
- `perturb_level(level_codes: torch.Tensor (B, n), dose: int, policy: str, freqs: torch.Tensor (16,), gen: torch.Generator) -> tuple[torch.Tensor, torch.Tensor]` returning `(new_codes, eligible (B,) bool)`. Positions: `dose` positions uniformly without replacement per row. `policy="frequency"`: each chosen position draws from `freqs` with the original value's mass set to 0 and renormalized; a row is ineligible (and left unchanged) if any chosen position has zero remaining mass. `policy="uniform"`: draw uniformly from the 15 other values; always eligible. New value is never the original.

- [ ] Step 1: tests — `test_dose_grid` (`dose_grid(1)==[1]`, `dose_grid(2)==[1]`, `dose_grid(13)==[1,2,4]`, `dose_grid(67)==[1,4,11,21]`); `test_code_frequencies_sum_to_one`; `test_frequency_excludes_original` (1,000 draws, never original, only codes with mass); `test_ineligible_when_no_alternative` (freqs one-hot on the original value → eligible False, codes unchanged); `test_uniform_changes_exactly_dose_positions`; `test_perturb_deterministic_given_seed`.
- [ ] Steps 2–4: FAIL → implement → PASS.
- [ ] Step 5: commit `feat: perturbation policies and dose grid`.

### Task 5: E2 pilot runner, estimators, report

**Files:** Create `src/ncm_sudoku/e2.py`, `scripts/wp1_pilot.py`, `tests/test_e2.py`; outputs `runs/wp1/pilot_records.jsonl`, `experiments/wp1/pilot_summary.json`, `experiments/wp1/pilot_report.md`.

**Interfaces — Consumes:** Tasks 1, 4; `intervene.continue_generation`, `runner`, `validate`, `model.level_slices`.
**Produces:**
- `PILOT_LEVELS = (1, 2, 6, 11)`, `POLICIES = ("frequency", "uniform")`, `N_SEEDS = 3`.
- `run_pilot(m, puzzles, solutions, chunk: int = 50) -> list[dict]` — A once per puzzle; B once per (puzzle, level); per (level, policy, dose from `dose_grid`, seed 0..2): perturb level ℓ for all puzzles with `torch.Generator().manual_seed(1000*level + 100*dose + 10*seed + (0 if policy=="frequency" else 1))`, C and D via `continue_generation` on the same chunk tensor. Record per puzzle: `puzzle_id, level, policy, dose, seed, eligible, solve_A, solve_B, solve_C, solve_D, well_formed_C, well_formed_D, hamming_CA` (cell Hamming of decoded C vs decoded A; null if C is not well-formed), `downstream_changes_D` (codes after level ℓ differing from A). Frequencies from `code_frequencies` of the A codes of these puzzles (D38).
- `theta2(records) -> float`, `theta_comp(records, level=2) -> float` — frequency policy, dose 1; average over seeds within puzzle first, then over puzzles; θ₂ on puzzles eligible at both levels 2 and 11 in all seeds (§7.2).
- `cluster_bootstrap(records, estimator, n_boot: int = 2000, seed: int = 0) -> tuple[float, float]` — resample puzzles with replacement; 95% percentile interval.
- `summarize(records) -> dict` — θ₂, θ_comp (level 2) with intervals; per (level, policy, dose): solve means for A–D, discordance counts b (A=1, D=0) and c (A=0, D=1) per seed, exclusion share, format-error shares, `hamming_CA` quantiles (0, .25, .5, .75, 1); dose-overlap diagnostic: per level the range of median `hamming_CA` across doses and whether ranges overlap between levels 2 and 11.
- `wp1_pilot.py`: CAL from Task 1; writes records, summary, and a markdown report headed "Non-confirmatory pilot (plan §12.1)".

- [ ] Step 1: tests — `test_theta_estimators_on_toy_records` (hand-built records for 2 puzzles × 3 seeds with known values: θ₂ and θ_comp equal the hand-computed seed-then-puzzle averages; an ineligible puzzle at level 11 is excluded from θ₂); `test_cluster_bootstrap_degenerate` (all-identical records → zero-width interval at the point value); slow `test_run_pilot_small` (2 released puzzles, monkeypatch `PILOT_LEVELS=(11,)` and doses `[1]`: records have the expected count 2 policies × 1 dose × 3 seeds × 2 puzzles; `solve_B == solve_A` for all).
- [ ] Steps 2–4: FAIL → implement → PASS.
- [ ] Step 5: commit `feat: E2 pilot runner, estimators, report`.
- [ ] Step 6: after Task 3 Step 7, run `uv run python scripts/wp1_pilot.py` in the background (≈ 3 h on CPU: 54 D configurations × 300 puzzles); read the summary; record D42 (pilot headline numbers, explicitly non-confirmatory); commit outputs.

### Task 6: Documentation pass

**Files:** Modify `ROADMAP.md` (WP1 status, measured run times, next step: lock inputs), `AGENTS.md` (index new modules, scripts, `experiments/wp1/`), `DECISIONS.md` (D41, D42 already added in Tasks 2/5).

- [ ] Step 1: edits; `uv run pytest -q` → PASS.
- [ ] Step 2: commit `docs: WP1 status and DOX update`.

## Out of scope

Contiguous/scattered position experiments (backlog), sample-size simulation and the lock (next WP), PROBE/SELECT/TEST generation, E3/E4.
