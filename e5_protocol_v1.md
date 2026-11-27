# E5 protocol v1 (draft): is the weak level-6 candidate-mask readout a property of the cumulative state or of the generator?

Status: draft, revised after review rounds R1, R2 and Final (`.reviews/e5-protocol-v1/decisions.md`), not locked. Compiled 2026-11-27 from decisions D91–D106 (`DECISIONS.md`). Locking follows the project rule: a git tag plus an OSF registration citing the tag name, the tagged commit and the hash manifest of §10; the TEST pairs are generated only after the lock.

This is a separate study. It does not change the submitted manuscript (TMLR submission 14707, D90) or the locked plan v3.7 (tag `prereg-v3.7`).

## 1. Question and claims

The v3.7 study found the nine-bit candidate mask of a Sudoku puzzle only weakly linearly readable from the generated full-length cumulative latent state after level 6 (Z<=6) of the released NCM Sudoku-hard checkpoint. Its discussion states that candidate reasoning could take place inside the generator's activations without leaving a readable trace in Z<=6, and that its design does not test this. E5 tests it with counterfactual pairs: two puzzles with the same solution and different clue masks. A prediction computed from the solution alone cannot separate the two members of a pair; a within-pair readout therefore measures clue-dependent information.

Two confirmatory claims, each at alpha = 0.025 (family-wise 0.05; D105):

- Claim A (state reading): with the frozen own-position linear probe, the within-pair candidate-mask readout from the generator's prefix layer `k*` exceeds that from the generated Z<=6 by more than 0.25 (A2), and the probe's within-pair readout of Z<=6 is practically equivalent to non-discrimination, within 0.5 ± 0.03 (A1).
- Claim B (causal reading): under an interchange intervention on the candidate subspace of the prefix at layer 2, with the recipient's levels 1–6 fixed, the T = 1 code distribution of level 7 moves towards the both-empty full-swap reference by more than 0.01 TV on average (B1) and by more than under norm-matched random subspaces (B2), a high-variance control (B3) and a shuffled-digit control (B4).

## 2. Existing data and what has been observed

All of the following were seen before this protocol was written; none is confirmatory, and none of the TEST pairs exists yet.

- Positive control (D94–D96, D98): the project's label, probe-training and metric code recovers the published mid-layer per-cell candidate readout of the Kniazev & Fijalkow Sudoku transformer (exact match 0.9994 / 1.0000 / 0.9978 after blocks 4–6 in bfloat16, gate >= 0.99; float32 gives the same gate decision). Scope: it validates labels, training loop and metrics with an untied 729-output head on that model, not the shared own-position head or the NCM hooks used here.
- Pairs (D97, D99): PROBE-TRAIN 1,000 and PROBE-VAL 250 pairs from the project's frozen generator (seed namespaces 8 and 9), no canonical-form overlap with any earlier set.
- Pilot probes (D100, D101; PROBE-VAL, fit on PROBE-TRAIN): mean per-pair within-pair AUC (W-AUC) of the shared own-position head: prefix P2 and P3 1.000 in all 250 pairs (P0 0.500, P8 0.957), generated Z<=6 0.5036 (SD 0.0445; 96 values exactly 0.5, including all 88 pairs with identical level 1–6 codes), teacher Z<=6 0.500; converged L-BFGS references and online MDL agree (Z<=6 MDL compression 1.029, below the position-only P0 1.049; P2 195.6); not every L-BFGS reference reached convergence (P8 hit the iteration cap). E3 permuted and label controls shifted W-AUC systematically (for example 0.432 and 0.581) and are diagnostics, not a calibrated null.
- Causal pilot (D102–D104; PROBE-VAL, 250 pairs, both orders): directed TV movement towards the both-empty full swap: Q 0.052, random subspaces 0.001–0.006 (20 draws), high-variance control 0.022, shuffled-digit control −0.079, both-empty full swap 0.061; mean step alignment with the full difference: Q 0.541, high-variance 0.471, random 0.115–0.142, shuffled −0.002.
- Design simulation (D105, D106; planning model, not a TEST calibration): see §5.4.

## 3. Model, code and environment

- Checkpoint: released NCM Sudoku-hard, `hazyresearch/ncm-checkpoints` revision d342ce8aaea58830eef3b8ad473664673e41f692; SHA-256 generator.pt 9e0bfe44abc1ca3930b7a63cd56cd0b9564b95e29edfe12dd0903207b89df8b8, tokenizer.pt 3bc6aecad8e15820f9d9bb09750e3c59bdf91ca953f1f11dbd109aaed1d80c0b, config.yaml 8d58c49e6fe52e60191e06df4061937d5bb84f97c5ffbcd93ed9830c32f8df2f; upstream HazyResearch/ncm at c70274273f489abc73832b2b98584a8483b6b203 (unmodified submodule); loaded only through `ncm_sudoku.model.load_model` (weights_only).
- Generator guard for the pairs: numpy 2.5.4; `generate.py` SHA-256 57a8bfe55767c3e0be450307d5a09a390e13fa5aabe884ed826e200276d2a2ec, `solve.py` 9f3e6df5ca6e0c91c448c459cb164c398ada77c462308d9bc2e07043948c0e5e (`subsets.assert_generator_frozen`).
- Numerics: FP32 model computation, eager, deterministic algorithms, CPU on native Windows (plan v3.7 §2.2, D30), greedy decoding (temperature 0). Bit-determinism is promised only for a fixed batch layout (D20); the layout is fixed in §4.4. The thread count is recorded with the run.
- Code: this repository at the locking tag; the TEST runner and every frozen artifact are listed with SHA-256 in the manifest (§10).

## 4. Data, representations and frozen components

### 4.1 TEST pairs

- Construction (D97, D99, `ncm_sudoku.e5pairs`): one solution from `generate.random_solution` and two clue masks from the frozen removal procedure (30 clues, unique solution), random streams `[10, index, 0/1/2]`, member B redrawn until its clue mask differs.
- External screening: each candidate is screened (through a precomputed index of the external canonical keys) by the exact canonical form of its solution against the fixed earlier datasets (gate, CAL, PROBE-TRAIN, PROBE-VAL, WP2 TEST, released hard set, the E5 PROBE-TRAIN and PROBE-VAL pairs; their identity hashes are in the manifest); a colliding candidate is rejected. The raw index runs from 0 until the N-th accepted pair; the TEST set is these N = 400 pairs (800 puzzles) in raw index order. A screening log records, per raw index, the pair id, accept or reject, the rejection reason and the colliding external id. A generation error stops the run; it never turns silently into a step to the next index.
- Internal collisions: after the 400 accepted pairs are fixed and before any scoring, they are checked for shared solution orbits; any internal collision blocks both claims; no candidate is replaced or redrawn (for TEST this overrides the internal replacement of D99); both ids of every colliding pair are logged next to the veto. The error guarantee covers this whole procedure, not the collision-free case conditionally.
- Eligibility, decided from labels before any model output is read: claim A uses pairs with at least one discordant bit (a cell empty in both members and a digit that is a candidate in exactly one member); claim B uses pairs with at least one both-empty cell (with 30-clue members at least 21 cells are empty in both, so all pairs are expected eligible for B). The numbers of eligible pairs n_A and n_B are reported; excluded pairs are listed.

### 4.2 Representations

- Extraction (`ncm_sudoku.e5extract`): in the generation pass that produces level 7 (pass index 6, which reads Z<=6), the prefix residual stream at the 81 cell positions (`PREFIX_CELLS`), layers 0–8 (layer 0 = input of blocks[0], layer k = output of blocks[k−1]); generated Z<=6 cell states (`states.cumulative_states`, level 6, `states.cell_states`); generated codes; the solved flag.
- Storage and precision: prefix activations stored as fp16 and read back as fp32 (the probes were fitted on the same path); Z<=6 cell states stored and read as fp32.
- Labels: `labels.candidate_mask` on the initial puzzle.

### 4.3 Frozen components (fitted on PROBE data only, never on TEST)

- Primary probes: the shared own-position linear heads (D55: state concatenated with the cell one-hot, nine sigmoid outputs, seeds 0, 1, 2) for the prefix layer `k*` and for Z<=6, at their selected pilot configurations. `k*` = P2 by the D101(3) rule (highest mean per-pair W-AUC on PROBE-VAL, ties by lower PROBE-VAL Brier, then the lower layer; P2 and P3 both 1.0, P2 Brier 1.95e-6 vs. P3 9.04e-5). The P2 head is saved (bit-identical to the pilot predictions, `experiments/e5/causal/heads.json`); the Z<=6 head is refitted and saved the same way before the lock.
- Causal components: Q = float64 orthonormal basis (SVD, rank check sigma_9 > 1e-8 sigma_1) of the seed-averaged state rows W (9 × 512) of the P2 head; the high-variance basis H = first nine right singular vectors (uncentred SVD) of the PROBE-TRAIN both-empty layer-2 donor−recipient differences (fp16-stored, read as float64) after projecting them off Q, re-orthogonalized against Q; the digit derangement Π: d → d + 1 (mod 9) applied to the nine head-logit coordinates; the 20 random bases R_j, j = 0..19 (float64 QR of i.i.d. standard Gaussian 512 × 9 matrices from `numpy.random.default_rng(1000 + j)`, columns sign-normalized to a positive R diagonal); the P4 and P8 heads for the representational diagnostics.
- Secondary components: the Z<=6 whole-layer (D66) head with its PROBE-TRAIN PCA, the P0–P8 shared heads and the B0–B8 global heads are either saved and hashed before the lock or refitted deterministically on PROBE-TRAIN/PROBE-VAL by the pilot code at the locked commit; they are never fitted or selected on TEST.
- All saved components are listed with SHA-256 in the manifest (§10).

### 4.4 Batch layout

Torch threads: 4 (recorded and checked at start). Extraction: batches of 50 puzzles, all a-members in raw index order, then all b-members. Probe inference: rows in raw index order (a-members, then b-members, cells in grid order), batches of 50 puzzles, the last batch shorter as is; eligibility only selects which rows enter the statistics and never regroups scoring inputs. Causal evaluation: batches of 50 recipients, order "ab" (a recipient, b donor) for all pairs, then "ba"; the last batch of each order may be shorter and is processed as is. Donor activations are captured online in fp32 with `level_logits(m, prefix_d, codes_d, level=7)` (the donor's own clean codes) in the same batch layout as the recipient's; saved fp16 arrays are never used as donors.

## 5. Primary analyses

### 5.1 Within-pair AUC

Probe prediction for a puzzle, cell and digit: for each of seeds 0, 1, 2 the float32 Linear + Sigmoid probability (the `probes` / `e5causal.refit_head` path), averaged over the seeds and compared in float64; per-seed probabilities are kept for §7. (`e5causal.head_logits`, which averages pre-sigmoid logits, is used only for the P4/P8 diagnostics.) For a pair, over its discordant bits: score 1 if the candidate member has the higher probability, 0 if lower, 0.5 if equal; inputs verified bit-identical between the members (the probe input vectors at that cell) are scored 0.5 regardless of the predictions. Per-pair W-AUC = mean score over the pair's discordant bits; W = mean of per-pair W-AUCs over the n_A eligible pairs (equal weight per pair; every statement about W, including the 6-per-100 reading of epsilon, refers to this equal-pair-weighted mean). Bit-pooled values are reported as descriptive.

### 5.2 Causal outcome

For each pair and order (recipient r, donor d), with the recipient's clean level 1–6 codes, `intervene.level_logits(m, prefix_r, codes_r, level=7)` is run with a forward hook on blocks[1] that replaces the recipient's rows at the both-empty cell positions; clue positions and positions empty in one member only are never changed. With Delta_c = x_d − x_r per both-empty cell (float64; x captured at the output of blocks[1] in the same layout) and the target norm s_c = ‖Delta_c Q Qᵀ‖:

| Condition | Written value at a both-empty cell |
|---|---|
| Q | x_r + Delta Q Qᵀ |
| random R_j | x_r + (Delta R_j R_jᵀ) · s / ‖Delta R_j R_jᵀ‖ |
| high-variance H | x_r + (Delta H Hᵀ) · s / ‖Delta H Hᵀ‖ |
| shuffled-digit | x_r + u · s / ‖u‖, u = W⁺ Π(W Delta) |
| both-empty full swap (reference) | x_d |
| full donor input (descriptive reference) | `level_logits(m, prefix_d, codes_r, level=7)` without a patch (a capture-only hook, bit-identical to no hook) |

Steps are computed in float64 and written back as float32. Zero rule (one threshold in text and code, `e5causal.norm_matched`): a zero target norm gives an exactly zero step; a positive target norm s with a raw control step of norm <= 1e-12 · max(s, 1) makes claim B not confirmable (§6), and the pair is not dropped. Outcome: P = T = 1 softmax over the 16 codes at each of the 18 level-7 queries (float64); directed effect of a condition = mean over queries of TV(P_clean, P_full) minus mean over queries of TV(P_cond, P_full), with P_full the both-empty full swap, computed in this operation order (`e5causal.tv`, as in the pilot); each pair's value is the mean of its two orders; the random-subspace value is the mean over the 20 bases.

### 5.3 Decision statistic and conditions

One function, `ncm_sudoku.e5stats.betting_logk`, implements a one-sided betting test of a bounded mean (Waudby-Smith & Ramdas 2024): values X in [0, 1] (quantities on [−1, 1] rescaled by (x + 1)/2), processed over the eligible pairs in raw index order; capital K = prod_i (1 + lambda_i (X_i − m0)); bets lambda_{i+1} = min( sqrt(2 log 40 / (N_plan v_i)), 0.75 / m0 ) with N_plan = 400 always (passed explicitly), mu_i = (0.5 + sum_{j<=i} X_j)/(i + 1), v_i = (0.25 + sum_{j<=i} (X_j − mu_j)^2)/(i + 1), v_0 = 0.25; the condition holds when log K after the last eligible pair > log 40 (terminal decision). If the number of eligible pairs for a claim is 0, the claim is not estimable and not made.

| Condition | X | m0 |
|---|---|---|
| A1 lower | per-pair W-AUC of Z<=6 | 0.47 |
| A1 upper | 1 − per-pair W-AUC of Z<=6 | 0.47 |
| A2 | per-pair Delta = W-AUC(P2) − W-AUC(Z<=6), rescaled | 0.625 (Delta > 0.25) |
| B1 | per-pair Q directed effect, rescaled | 0.505 (> 0.01) |
| B2 | per-pair Q − random-subspace mean, rescaled | 0.5 |
| B3 | per-pair Q − high-variance, rescaled | 0.5 |
| B4 | per-pair Q − shuffled-digit, rescaled | 0.5 |

The A2 margin is set independently of the pilot: a difference of 0.25 is a large effect on the W-AUC scale and, with W(Z<=6) inside the equivalence band, requires a tie-credited prefix W-AUC of about 0.72–0.78 (D105). Claim A holds if A1 lower, A1 upper and A2 all hold; claim B holds if B1–B4 all hold (intersection-union; no further alpha split; D105). Conditions are reported as descriptive outcomes, never as separate confirmatory results. Estimates: percentile pair-bootstrap intervals (95%, 10,000 resamples, seed 0) for every quantity, for estimation only.

### 5.4 Sample size (D105(4)–(6), D106)

N = 400 is the smallest grid point (250..1,000, step 50; 2,000 replications per point) with power >= 0.9 for both claims under the planning model (causal effects halved, W(P2) 0.85, W(Z<=6) 0.515), confirmed by a re-check with another seed (A 0.997, B 0.998). Grid powers (A / B): 250 0.869 / 0.000; 300 0.956 / 0.084; 350 0.989 / 0.746; 400 0.996 / 0.995. At N = 400 (10,000 replications): pilot model 1.000 / 1.000; a same-mean heterogeneous case B 0.9005 (no margin above the target); null-boundary false-positive rates 0.0014 (A1 lower), 0.0013 (A1 upper) and 0 events for A2 and B1–B4. Seeds 2026112701 (grid), 2026112702 (re-check), 2026112703 onwards (checks); `scripts/e5_power.py`, `experiments/e5/power.json`. The simulation resamples the PROBE-VAL pilot, on which the heads were selected; it is a planning model, not a calibration of the fresh TEST.

## 6. Validity, stopping and deviations

Each claim ends in one of four outcomes: holds, not shown, not estimable (no eligible pair), invalid.

- Finiteness: activations before every greedy decision, values before and after fp16 storage, logits, probe predictions on evaluable bits and every per-pair quantity are checked for finiteness before any argmax, quantization or aggregation; a non-finite value stops the run, and both claims are invalid.
- Shared failures, blocking both claims: a hash mismatch of the checkpoint, the generator guard, the pair set, the screening corpus, the labels code, the extraction code, the P2 head (P2 defines Q), the decision code `ncm_sudoku.e5stats`, the runner, or any entry of the approved dry-run record (§9.4); a failed extraction check; an internal orbit collision (§4.1). Extraction checks, run in the dry run and on TEST: the number and shapes of the captured layers (layers 0–8, 81 cell positions, pass index 6) match the specification; the generated codes of the capture pass equal those of a clean generation without capture; the Z<=6 states have the expected shape.
- Claim A failures (claim A invalid, claim B unaffected): a hash mismatch of the Z<=6 head or of the claim-A scoring code.
- Claim B checks, run on every call; any failure makes claim B invalid, and the failing pair is not dropped:
  - hash match of Q, H, Π, R_0..R_19, W and the P4/P8 heads;
  - the hook is registered on blocks[1] of the level-7 call (absolute level checked); hook applications per call by role: clean reference 0, capture-only 1, patch 1; one hooked forward per model instance at a time;
  - written rows: for every condition and every targeted cell, the row after the hook equals the independently computed expected row (x_r + step in float64, rounded to float32; x_d for the full swap) bit for bit;
  - untouched rows: within the same call, every non-targeted row of the hooked output (the query rows, the BOS and separator rows, the clue cells and the cells empty in one member only) is bit-identical before and after the hook;
  - capture-only check: a call with a capture-only hook gives logits bit-identical to `level_logits` without any hook;
  - self-donor: with d := r through the full donor-capture and indexing path, at the both-empty cells and at all 91 prefix positions, the logits are bit-identical to the clean run;
  - zero rule (§5.2): a positive target with a numerically zero control step is a failure;
  - high-variance invariance (float64, on the scaled step): for every cell c, max over the nine digits of |(W step_hv,c)_d| <= 1e-8 ‖W‖_F ‖step_hv,c‖_2 (cells with a zero step skipped);
  - shuffled direction (float64): for every cell with Π(W Delta_c) ≠ 0, the cosine between W step_shuf,c and Π(W Delta_c) >= 1 − 1e-8.
  Target norms, actual norms ‖x_after − x_before‖, scale factors and the alignment of each condition's step with Delta are logged (diagnostics, not tests).
- No optional stopping: N is fixed at 400 and is not changed after any TEST outcome; the TEST is run and analysed once.
- Restartability: the runner checks every input hash and the thread setting before starting, has a single writer and an atomic final write, and may only resume the same interrupted run with identical inputs, order and verified partial outputs; a finished or invalid run is never rerun.
- Deviations: any departure from this protocol is logged in `DECISIONS.md` before outcomes are read where possible and reported; a method change after TEST outcomes have been seen makes the affected claim exploratory; any methodological change after the lock requires a new protocol version, whether or not outcomes were seen, and TEST data already seen are not reused for confirmation.

## 7. Secondary and descriptive analyses (no confirmatory claims)

- Per-seed W-AUC of the primary heads; bit-pooled W for Z<=6 and P2; empty strata reported as null with their denominator; degenerate bootstrap intervals flagged, never read as a proven zero. The E3 permuted and label controls are pilot diagnostics and are not refitted on TEST.
- W(Z<=6) and W(P2) on the stratum of pairs whose generated level 1–6 codes differ; the code-identical stratum as a negative control for Z<=6.
- The share of discordant bits whose local Z<=6 cell state is identical in both members, and W(Z<=6) restricted to the other bits.
- The Z<=6 whole-layer (D66) readout (comparison with the v3.7 H1 probe); the P0–P8 curve and the global closing-BOS readout (the whole-layer readout on the prefix measures the input at P0, D101). These never select a new primary probe.
- Status of the D102 pilot diagnostics: kept on TEST (descriptive): the P4 and P8 signed shifts and flip rates and their Q − control contrasts (random mean, high-variance, shuffled-digit); pilot only, not run on TEST: the Q bases of the individual probe seeds (D102(1) sensitivity); dropped: the normalized shift (see below).
- Causal diagnostics: per-condition directed effects and their spread over the 20 random bases; undirected TV(P_cond, P_clean); argmax changes over the 18 queries; the full donor-input reference; the P4 and P8 representational shifts towards the donor on discordant bits, using the seed-averaged pre-sigmoid logit z: signed shift (2 y_d − 1)(z_cond − z_clean) and flip rate towards y_d (pairs without a discordant bit are excluded from these diagnostics and counted; the normalized shift of D102(5) is dropped: its denominator is unstable at saturated logits); step norms and alignments; the distribution of TV(clean, full) and the share below 0.01; the heterogeneity of the directed effect across recipients.
- Exploratory, not preregistered with a fixed readout: the level-7 query positions and a breakdown by inference-wave depth (D101(7)).
- Not part of TEST: the full-generation causal variant and the rescue/harm analysis (D105(5)).

## 8. Pre-specified interpretation rules

All readings are conditional on the checkpoint, the frozen probes and bases, and this intervention. Claim A and claim B are read separately; the joint rows combine them.

| Result | Justified claim | Does not follow |
|---|---|---|
| Claim A holds | On average over the eligible pairs (equal weight per pair), the frozen own-position linear probe reads the one-step candidate mask within pairs from the prefix at layer 2 far better than from Z<=6 (difference > 0.25), and its within-pair readout of Z<=6 is practically equivalent to non-discrimination (within 6 net correct orderings per 100 discordant comparisons, forced ties included) | Exact or calibrated decoding of the full candidate mask (the test ranks discordant bits within pairs); Z<=6 carries no candidate information; no other readout could read it; equal capacity of the two readouts (256- vs. 512-dimensional inputs); the generator uses the encoded candidates |
| Claim A not shown (any of A1, A2 fails) | No confirmatory claim about the state reading; the component outcomes are reported descriptively | Z<=6 carries candidate information; the prefix lacks it; the two readouts are equal |
| Claim B holds | Under this interchange intervention with levels 1–6 fixed, the T = 1 level-7 code distribution moves towards the both-empty full-swap reference by more than 1 percentage point of TV on average, and more than under norm-matched random subspaces, the high-variance control and the shuffled-digit control | A digit-specific mechanism (the controls are matched in norm, not in alignment with the full difference); changes of argmax codes, later levels or solving; the generator performs candidate reasoning |
| Claim B not shown (any of B1–B4 fails) | No confirmatory claim about the causal reading; component outcomes descriptive | The code choice is unchanged by the patch (see the diagnostics); the candidate information is unused in general; B1 alone, or control contrasts without B1, establish movement towards the reference |
| Claims A and B hold | The average of the three frozen P2 heads ranks the discordant candidate bits of the eligible pairs far better than the Z<=6 readout, which is practically equivalent to non-discrimination, and the level-7 code distribution is sensitive to the candidate subspace beyond the named controls: the weak level-6 readout is consistent with a property of the cumulative state rather than with an absence of the information in the generator | Exact or calibrated decoding of the full candidate mask; the generator reasons about candidates; the result transfers to other checkpoints, levels, readouts or interventions |
| Claim A holds, claim B not shown | The state reading as above; no confirmatory evidence that the level-7 code distribution depends on the candidate subspace | The generator does not use the information |
| Claim B holds, claim A not shown | The causal reading as above; no confirmatory state reading | Z<=6 carries the candidate information |
| Claim B invalid (§6), claim A valid | Claim A is read as above; no reading of claim B | Anything about the causal question |
| Claim A invalid or not estimable, claim B valid | Claim B is read as above; no reading of claim A | Anything about the state question |
| Internal collision, shared failure or non-finite stop | No confirmatory claim | Anything about the effects |

## 9. Pre-lock tasks (all done and recorded before the tag)

1. Refit and save the Z<=6 shared head (`e5causal.refit_head`): in the pilot layout (all PROBE-VAL empty-cell rows in one call), check that the prediction array has the saved shape (500, 81, 9) and the same NaN pattern (given cells), that every evaluable element is finite on both sides, and that the evaluable elements are exactly equal to the saved pilot predictions; record its SHA-256. Claim-A scoring uses the per-seed sigmoid path of §5.1; `head_logits` stays a P4/P8 tool (generalized to the head's state dimension only if ever used elsewhere).
2. Save and hash Q, H, the 20 random bases, Π and W; save and hash the secondary components (§4.3), or list the file SHA-256 of the script that refits them on PROBE data.
3. Implement the frozen TEST runner: pair generation for namespace 10 with external screening, the screening log and the internal-collision rule; extraction and probe inference with the §4.4 layout and threads; W-AUC scoring with eligibility from labels and the tie rules; the causal evaluation with every §6 check as a hard failure for claim B (including the fixed isolation mask of `e5causal.Level7Hooks`, which must cover every non-targeted row, and the zero rule of §5.2); finiteness checks at every point listed in §6; decisions through `ncm_sudoku.e5stats` with `n_plan = 400`; restart and single-writer rules; a report. Acceptance: synthetic injected non-finite values stop every path.
4. Dry run on PROBE-VAL in a separate, hash-checked mode that never reaches the TEST generator, threads 4. Pass rule, all parts exact (no tolerance, none chosen afterwards):
   (a) the ordered PROBE-VAL id list reproduces the `sha256_ids` value in `experiments/e5/pairs.json`;
   (b) claim A, in the TEST layout of §4.4: per pair id, the number of discordant bits, W-AUC(P2), W-AUC(Z<=6) and Delta equal the values recomputed from the saved pilot predictions (`runs/e5/pilot/{P2,z6}__shared__none.npy`), and the ordered decision inputs of A1 and A2 are equal;
   (c) claim B: per (pair id, order, condition) the directed values equal those of `runs/e5/causal/primary.npz` (its `meta` gives pair index and order), then the pair means (ab and ba averaged) and the ordered decision inputs of B1–B4 are equal;
   (d) every §6 check passes;
   (e) reordering: the run is repeated with a fixed, recorded permutation of the pair order that changes every batch's neighbours and the position of each pair within its batch; per pair id the values of (b) and (c) are unchanged.
   Separately reported: whether the §5.1 identical-input tie rule changes any pilot per-pair W-AUC. The dry-run record states the SHA-256 of the three reference files, the ordered id list, the heads and bases, the runner, `ncm_sudoku.e5stats` and the record itself; the manifest lists them, and TEST checks the same set before starting. Only a passing dry run allows the lock. If the final procedure changes a pilot primary value, the D106 simulation is re-run with the hashed, id-aligned per-pair rows written by the final scorer as its input (not the pilot JSON files); the lock then requires power >= 0.9 for both claims at N = 400 in the grid point and in its re-check. Otherwise there is no tag, no OSF lock and no TEST; a different N requires a new protocol version.
5. Synthetic end-to-end tests of the runner: external rejection with index stepping and logging, generation errors, internal collision, n_A < 400, 1-ULP-perturbed identical inputs scored as ties, a hand-computable case with pairs of unequal discordant-bit counts and both signs of Delta that checks the equal pair weighting, the rescaling and the final decision, non-finite stops at every checked point, each injected claim-B check failure, n_elig = 0.
6. Hash manifest (§10), clean commit, tag, OSF registration with the protocol, the manifest and the observed-data summary (§2).

## 10. Hash manifest

Before the tag, a manifest file lists the SHA-256 of: this protocol; the checkpoint files; the generator guard files; the screening corpus (ids and solution arrays of every earlier dataset); the PROBE pair arrays; the primary heads (Z<=6, P2), the P4/P8 heads, Q, H, R_0..R_19, Π, W; the secondary components or the file hash of the script that refits them; the TEST runner and `ncm_sudoku` source files; `uv.lock`. It also lists the approved dry-run record and the hashes it states (§9.4). Hash formats are stated per entry: id lists by `subsets.sha256_ids` (SHA-256 of the ordered JSON list, UTF-8); puzzle, solution and clue-mask grids by `subsets.sha256_array` (uint8 C-order bytes); everything else by the SHA-256 of the file bytes. Because `runs/`, `checkpoints/` and `data/` are not in the repository, the manifest gives for every such artifact a retrieval location or a reconstruction recipe (script and seed), and restoration is checked once from a clean environment before the lock. The manifest is committed before the tag (so it cannot contain the tag commit's hash); the tag name and commit are given in the OSF registration, together with the manifest.

## 11. Compute

Measured basis: pair extraction 0.84–1.47 s per puzzle (`experiments/e5/extract.json`; 1.71–1.77 s in `experiments/e5/cost.json` at batch 20); causal one-pass evaluation 1,844 s per 250 pairs with 20 random draws (`experiments/e5/causal/primary.json`). For 400 pairs: extraction about 11–24 min, causal evaluation about 50 min (scaled from the pilot), plus the new checks, screening and logging (to be measured in the dry run).
