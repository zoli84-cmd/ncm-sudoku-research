# E5 protocol v1 (draft): is the weak level-6 candidate-mask readout a property of the cumulative state or of the generator?

Status: draft for review, not locked. Written 2026-11-27 from decisions D91–D106 (`DECISIONS.md`). Locking follows the project rule: a git tag plus an OSF registration citing the tag name and the tagged commit; the TEST pairs are generated only after the lock.

This is a separate study. It does not change the submitted manuscript (TMLR submission 14707, D90) or the locked plan v3.7 (tag `prereg-v3.7`). Every number below that comes from a pilot is non-confirmatory and is used only for design.

## 1. Question and claims

The v3.7 study found the nine-bit candidate mask of a Sudoku puzzle only weakly linearly readable from the generated full-length cumulative latent state after level 6 (Z<=6) of the released NCM Sudoku-hard checkpoint. Its discussion states that candidate reasoning could take place inside the generator's activations without leaving a readable trace in Z<=6, and that its design does not test this. E5 tests it with counterfactual pairs: two puzzles with the same solution and different clue masks, so that a solution-carried signal cancels within a pair.

Two confirmatory claims, each at alpha = 0.025 (family-wise 0.05; D105):

- Claim A (state reading): with the frozen own-position linear probe, the within-pair candidate-mask readout from the generator's prefix layer k* is large, and the probe's within-pair readout of the generated Z<=6 is practically equivalent to non-discrimination.
- Claim B (causal reading): under an interchange intervention on the candidate subspace of the prefix at layer 2, with the recipient's levels 1–6 fixed, the level-7 code distribution moves towards the full-swap reference by more than a minimum and by more than under three named controls.

## 2. Model, code and environment

- Checkpoint: released NCM Sudoku-hard (`hazyresearch/ncm-checkpoints` revision d342ce8a; generator.pt SHA-256 9e0bfe44…df8b8, tokenizer.pt 3bc6aeca…80c0b, config.yaml 8d58c49e…8df2f; `experiments/provenance/checkpoints.json`), upstream code HazyResearch/ncm at c7027427 (unmodified submodule), loaded only through `ncm_sudoku.model.load_model` (weights_only).
- Numerics: FP32, eager, deterministic algorithms, CPU on native Windows (plan v3.7 §2.2, D30); greedy decoding (temperature 0).
- Code: this repository at the locking tag; the TEST runner and all frozen artifacts are identified by SHA-256 in the registration (§9).

## 3. Data

- Pairs (D97, D99, D105(2)): one solution from `generate.random_solution` and two clue masks from the frozen removal procedure (30 clues, unique solution), streams `[seed, index, 0/1/2]`, member B redrawn until its clue mask differs (`ncm_sudoku.e5pairs`). Seed namespace 10 (TEST); namespaces 8 and 9 were used for the PROBE pairs.
- Screening: each candidate pair is screened by exact canonical form of its solution against the fixed earlier datasets (gate, CAL, PROBE-TRAIN, PROBE-VAL, WP2 TEST, released hard set, the E5 PROBE-TRAIN and PROBE-VAL pairs); a candidate that collides is rejected. The raw index runs from 0 until the N-th accepted pair; the TEST set is these N pairs in raw index order.
- N = 400 pairs (800 puzzles) (D106: smallest grid point with power >= 0.9 for both claims under the planning model, re-checked).
- Internal collision rule: if two accepted TEST pairs share a solution orbit, neither claim is made; no candidate is replaced or redrawn (overrides the D99 internal replacement for TEST).
- Eligibility, decided from labels before any scoring: claim A uses pairs with at least one discordant bit (a cell empty in both members and a digit that is a candidate in exactly one); claim B uses pairs with at least one both-empty cell. Excluded pairs are counted and reported.

## 4. Representations and frozen components

- Extraction (`ncm_sudoku.e5extract`): in the generation pass that produces level 7 (reads Z<=6), the prefix residual stream at the 81 cell positions, layers 0–8 (layer 0 = input of blocks[0], layer k = output of blocks[k−1]); the generated Z<=6 cell states (`states.cumulative_states`, level 6); generated codes; the solved flag.
- Labels: `labels.candidate_mask` on the initial puzzle.
- Frozen probes (fitted on the PROBE-TRAIN pairs, selected on the PROBE-VAL pairs, never refitted on TEST): the shared own-position linear heads (D55: state plus cell one-hot, nine sigmoid outputs, three seeds, seed-averaged) for the prefix layer k* and for Z<=6. k* = P2 by the D101(3) rule (highest mean per-pair W-AUC on PROBE-VAL, ties by lower Brier, then lower layer; P2 and P3 tied at 1.0, P2 has the lower Brier). The P2, P4 and P8 heads are saved (`runs/e5/causal/heads/`, `experiments/e5/causal/heads.json`, bit-identical to the pilot predictions); the Z<=6 head is refitted and saved the same way before the lock (§9).
- Frozen causal components (D102, D105(2)): Q = orthonormal basis of the seed-averaged state rows of the P2 head; the high-variance basis (first nine principal directions of PROBE-TRAIN both-empty layer-2 donor−recipient differences projected off Q); the digit derangement d → d + 1 (mod 9); the 20 random orthonormal bases with seeds 1000–1019 (float64 QR of Gaussian matrices, positive R diagonal). All are saved and hashed before the lock.

## 5. Primary analyses

Within-pair AUC (W-AUC, D100, D101): for a pair, over the discordant bits, the share of bits where the probe gives the candidate member the higher probability, verified-identical inputs counted as ties (0.5); W = mean of per-pair W-AUCs over eligible pairs.

Causal outcome (D102, D105): with the recipient's clean level 1–6 codes fixed, `intervene.level_logits(..., level=7)`; patch at the output of blocks[1] at both-empty prefix cells, x_r + ((x_d − x_r) S) Sᵀ for subspace S, controls norm-matched per cell to the Q step; T = 1 softmax over the 16 codes of the 18 level-7 queries; directed effect = TV(P_clean, P_full) − TV(P_cond, P_full), averaged over queries, with P_full the both-empty full swap; both orders per pair averaged.

Decision statistic (D105(2), `ncm_sudoku.e5stats`): one-sided betting test for a bounded mean, unhedged positive-branch capital process, fixed-n predictable plug-in bets lambda_{i+1} = min(sqrt(2 log 40 / (N v_i)), 0.75 / m0) with mu_i = (0.5 + sum_{j<=i} X_j)/(i + 1), v_i = (0.25 + sum_{j<=i} (X_j − mu_j)^2)/(i + 1); terminal decision log K_N > log 40; pairs in raw index order; quantities on [−1, 1] rescaled by (x + 1)/2.

| Condition | Quantity | H0 rejected when the test rejects E[X] <= m0 on [0, 1] |
|---|---|---|
| A1 lower | W(Z<=6) | m0 = 0.47 |
| A1 upper | 1 − W(Z<=6) | m0 = 0.47 |
| A2 | Delta = W(P2) − W(Z<=6) | m0 = 0.625 (Delta > 0.25) |
| B1 | Q directed effect | m0 = 0.505 (> 0.01) |
| B2 | Q − mean of the 20 random subspaces | m0 = 0.5 |
| B3 | Q − high-variance control | m0 = 0.5 |
| B4 | Q − shuffled-digit control | m0 = 0.5 |

Claim A holds if A1 lower, A1 upper and A2 all reject; claim B holds if B1–B4 all reject (intersection-union; no further alpha split). Conditions are not reported as separate confirmatory results. Pair-level bootstrap intervals (10,000 resamples) are reported for every quantity as estimates only.

## 6. Invalid runs and stopping

- A non-finite model output stops the run; nothing is decided.
- A hash mismatch of any frozen artifact, a wrong hook-application count, a failed query-isolation, self-donor identity or norm check (D102(4f)) makes claim B not confirmable; the failing pair is not dropped to rescue the claim. Claim A is affected only by failures in its own pipeline (extraction, probe hashes).
- An internal orbit collision (§3) blocks both claims.
- Every departure from this protocol is logged in `DECISIONS.md` as a deviation before any outcome is read where possible, and reported.

## 7. Secondary and descriptive analyses (no confirmatory claims)

- W(Z<=6) and W(P2) on the stratum of pairs whose generated level 1–6 codes differ; the code-identical stratum as a negative control for Z<=6 (D101(4)).
- The share of discordant bits whose local Z<=6 cell state is identical in both members, and W(Z<=6) restricted to the other bits (D101(4)).
- Secondary readout of Z<=6 with the D66 whole-layer features (comparison with the v3.7 H1 probe).
- The P0–P8 curve and the global closing-BOS readout (descriptive; the whole-layer readout on the prefix measures the input at P0, D101).
- Causal diagnostics: per-condition directed effects, undirected TV, argmax changes, the P4 and P8 representational shifts towards the donor (float64 logits), flip rates, step norms and the alignment of each condition's step with the full difference (D104), the random-draw spread, the full donor-input reference, heterogeneity of the directed effect across recipients (including those with TV(clean, full) < 0.01).
- Exploratory, not preregistered as analyses with a fixed readout: the level-7 query positions and a breakdown by inference-wave depth (D101(7)).
- Not part of TEST: the full-generation causal variant and the rescue/harm analysis (D105(5)).

## 8. Pre-specified interpretation rules

Results are conditional on the checkpoint, the frozen probes and bases, and this intervention.

| Result | Justified claim | Does not follow |
|---|---|---|
| Claim A holds | With the frozen own-position linear probe, the one-step candidate mask is readable within pairs from the generator's puzzle encoding at layer 2, and this probe's within-pair readout of Z<=6 is practically equivalent to non-discrimination (within 6 net correct orderings per 100 discordant comparisons) | Z<=6 carries no candidate information; no other readout could read it; the generator uses the encoded candidates |
| A2 holds, A1 does not (W(Z<=6) not shown inside the band) | The prefix readout exceeds the Z<=6 readout by more than 0.25 | Practical equivalence of Z<=6 to non-discrimination |
| A1 holds, A2 does not | The Z<=6 readout is practically equivalent to non-discrimination | The prefix readout is large |
| Claim B holds | Under this interchange intervention, the level-7 code distribution moves towards the full-swap reference by more than 1 percentage point of TV on average and more than under norm-matched random subspaces, a high-variance control and a shuffled-digit control | A digit-specific mechanism (the controls are matched in norm, not in alignment with the full difference); the generator performs candidate reasoning; effects on later levels or on solving |
| B1 holds, a control contrast does not | The patch moves the code distribution towards the reference | Specificity to the candidate subspace |
| Claims A and B hold | The candidate mask is encoded in the generator's puzzle encoding, is practically absent from the frozen probe's within-pair readout of Z<=6, and the level-7 code choice is sensitive to the candidate subspace: the weak level-6 readout is consistent with a property of the cumulative state rather than an absence of the information in the generator | The generator reasons about candidates; the result transfers to other checkpoints, levels or readouts |
| Neither claim holds | The design provides insufficient evidence for the designated effects | The effects are absent |
| Internal collision or invalid run | No confirmatory claim | Anything about the effects |

## 9. Pre-lock tasks (all done and recorded before the tag)

1. Refit and save the Z<=6 shared head as for the P heads (`e5causal.refit_head`), check bit-identity with the pilot predictions, record its SHA-256.
2. Save and hash the high-variance basis, the 20 random bases and the derangement used by `scripts/e5_causal.py`.
3. Implement the frozen TEST runner: pair generation for namespace 10 with screening and the collision rule; extraction; W-AUC scoring with eligibility from labels, verified-identical inputs as ties and a stop on non-finite output; the causal evaluation with all identity checks as hard failures for claim B; the decisions through `ncm_sudoku.e5stats`; a report.
4. Dry run of the TEST runner on the PROBE-VAL pairs, reproducing the pilot W-AUCs and causal per-pair values exactly; record the dry run.
5. Fix the commit (clean tree), create the tag, and register on OSF with the tag name, the commit, this protocol's SHA-256 and the frozen-artifact hashes.

## 10. Compute

Measured basis (`experiments/e5/cost.json`, `experiments/e5/extract.json`, `experiments/e5/causal/primary.json`): pair extraction about 0.5 s to 1.7 s per puzzle; causal one-pass evaluation about 31 min per 250 pairs with 20 random draws. Expected for 400 pairs: extraction under 1 h, causal evaluation about 50 min, scoring minutes (not yet measured on the TEST runner).
