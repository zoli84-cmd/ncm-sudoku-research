# E5 D101 draft: primary readout and W-AUC inference after the pilot

Status: final after review rounds R1 and Final (`.reviews/e5-d101-readout/decisions.md`); recorded as D101 in `DECISIONS.md`. Non-confirmatory planning decision, written after the D100 pilot results and before the E5 protocol and any TEST data exist.

## Context

E5 is a planned, separately preregistered follow-up to the submitted manuscript (TMLR 14707, unchanged). Question: is the weak linear readout of the level-6 candidate mask a property of the cumulative state Z<=6 or of the NCM generator? The manuscript found the candidate mask only weakly readable from the generated full-length cumulative state after level 6 (`paper/sections/e3.tex`, `paper/sections/discussion.tex`), and states that candidate reasoning could happen inside the generator's activations without leaving a trace in Z<=6, which its design does not test.

Decisions so far (all in `DECISIONS.md`):

- D94–D96, D98: positive-control gate. Our label, probe-training and metric code recovers the Kniazev & Fijalkow (NeurIPS 2026; arXiv:2605.18847) mid-layer per-cell candidate readout on their released model: exact match 0.9994 / 1.0000 / 0.9978 after blocks 4–6 (gate >= 0.99), in bfloat16 and float32. Caveat: on blocks 1–7 the fixed E3 probe budget binds (all 30 fits end at their last epoch, grid edge (0, 0.003) selected); block 8 selected (0.1, 0.001) without hitting the cap.
- D95: global-position readout uses an untied 729-output linear head; the E3 shared head (state plus cell one-hot, one 9-output head shared across cells) cannot read cell-specific candidates from one global vector.
- D97, D99: counterfactual pairs from the project's frozen generator: one solution, two 30-clue masks with unique solutions; PROBE-TRAIN 1,000 pairs, PROBE-VAL 250 pairs; no canonical-form overlap with any earlier set. Within a pair, about 32 cells are empty in both members, about 31.6 of them have a different candidate mask, about 103 differing bits.
- Extraction (`experiments/e5/extract.json`): from the level-7 generation pass, prefix positions layers 0–8 and closing prefix BOS layers 0–8 (the prefix attends only to the puzzle prefix, so these do not depend on Z<=6; the 18 query positions of that pass read both Z<=6 and the prefix), plus generated and teacher Z<=6 cell states. Pair members solved 86–88%; the generated codes of levels 1–6 are identical in only 32–35% of pairs, so the generated Z<=6 is not a function of the solution alone.
- D100: pilot specification. Primary pilot quantity: within-pair AUC (W-AUC) over bits where the cell is empty in both members and the digit is a candidate in exactly one; the share of bits where the candidate member gets the higher probability, ties 0.5. Fit on PROBE-TRAIN pairs, select and score on PROBE-VAL pairs.

## Pilot results (PROBE-VAL pairs; `experiments/e5/pilot/`)

Readouts: shared = E3 shared head on the cell's own state (D55); whole = D66 cell-relative whole-layer features (own state plus PCA-256 of the 21 states of the cell and its 20 peers); global = D95 untied head on the closing BOS. Controls: permuted = representation permuted across puzzles (E3); labels = 9-bit labels permuted across empty cells (E3 label control).

W-AUC columns are pooled over bits (each pair weighted by its number of discordant bits), not means of per-pair W-AUCs.

| Representation / readout / control | W-AUC | W-AUC, pairs with different level 1–6 codes | Val Brier | Exact match |
|---|---|---|---|---|
| Z<=6 generated / shared / none | 0.5035 | 0.5054 | 0.2307 | 0.001 |
| Z<=6 generated / whole / none | 0.5052 | 0.5081 | 0.2306 | 0.002 |
| Z<=6 generated / shared / permuted | 0.4974 | 0.4960 | 0.2325 | 0.000 |
| Z<=6 generated / shared / labels | 0.5075 | 0.5116 | 0.2324 | 0.000 |
| Z<=6 teacher / any | 0.5000 | 0.5000 | 0.2308–0.2325 | <= 0.003 |
| P0 / shared / none | 0.5000 | 0.5000 | 0.2323 | 0.000 |
| P0 / whole / none | 1.0000 | 1.0000 | 0.0006 | 1.000 |
| P1 / shared / none | 0.9678 | 0.9673 | 0.0785 | 0.348 |
| P2 / shared / none | 1.0000 | 1.0000 | 0.000002 | 1.000 |
| P3 / shared / none | 1.0000 | 1.0000 | 0.0001 | 1.000 |
| P4 / shared / none | 0.9999 | 0.9999 | 0.0014 | 0.988 |
| P5 / shared / none | 0.9994 | 0.9994 | 0.0079 | 0.916 |
| P6 / shared / none | 0.9932 | 0.9938 | 0.0250 | 0.754 |
| P7 / shared / none | 0.9744 | 0.9755 | 0.0488 | 0.565 |
| P8 / shared / none | 0.9575 | 0.9598 | 0.0643 | 0.469 |
| P1–P8 / shared / permuted | 0.4317–0.4908 | 0.4351–0.4910 | 0.2333–0.2349 | 0.000 |
| P1–P8 / shared / labels | 0.5050–0.5812 | 0.5068–0.5820 | 0.2305–0.2324 | <= 0.001 |
| B0 / global | 0.5000 | 0.5000 | 0.2325 | 0.000 |
| B1–B8 / global (peak B3) | 0.5592–0.7638 | 0.5607–0.7628 | 0.2026–0.2395 | <= 0.031 |

Observations (revised after R1):

1. At layer 0 the prefix position of an empty cell holds the same token in both pair members, and the teacher Z<=6 is identical across members by construction, so the shared readout gets identical inputs. P0/shared/none is exactly 0.5 (every one of the 25,418 evaluable bits is a tie). Teacher/shared/none is 0.50001967 and P0/shared/permuted 0.50003934: the two members are predicted in one float32 batch, and a 1-ULP difference turns an exact tie into a win or loss; casting float32 outputs to float64 does not undo this, so identical inputs must be ties by rule.
2. The whole-layer readout at P0 is perfect: at layer 0 the 20 peer positions hold the peers' raw clue tokens, and the candidate mask is a thresholded linear function of the peer clues. At P0 this readout measures the input; at higher prefix layers it is diagnostic only (the states are contextualized, but the input stays reachable through the residual stream).
3. The controls are systematically shifted, not noisy around 0.5: P1 permuted has a per-pair mean of 0.432 (pair-level SE 0.0035, 219 of 250 pairs below 0.5), P2 labels 0.581 (SE 0.0034). Bit clustering within pairs does not explain this. Plausible causes: a fixed probe direction learned on one permutation (seed 11) shifts every pair the same way, and the label control selects its configuration and epoch on the true PROBE-VAL labels (`e3controls.fit_cells` permutes only the training labels). The E3 controls are therefore diagnostics, not a calibrated null.
4. Selected configurations differ by representation: 23 of 53 fits chose (0.1, 0.001), including every Z<=6 fit; the uncontrolled generated Z<=6 fits had their best epochs at 2–8 of 80 (shared 5/8/6, whole 2/2/2), while some control fits on Z did not (teacher whole: 2/74/77, budget cap reached on its grid); 21 chose (0, 0.003) (prefix shared P1–P8, prefix whole, B1–B4); 9 chose (0.1, 0.003).
5. On PROBE-VAL, 6,313 of the 16,482 discordant bits in pairs with different level 1–6 codes (and 15,249 of 25,418 over all pairs) sit in cells whose generated Z<=6 cell state is identical in both members. With ties scored 0.5, the mean per-pair W-AUC of any own-position Z<=6 readout is bounded by 0.7004 over all pairs and 0.8093 over code-different pairs.

## Decision D101

1. Primary readout: the shared head on the cell's own position (D55), for the generated Z<=6 and the prefix layers; the scored prediction is the mean of the selected configuration's three seed models, so the primary quantity is the readability of these seed-averaged linear heads (single-head support: per-seed W-AUC and the L-BFGS reference of item 6). Reason: the whole-layer readout measures the input at P0 (observation 2), and the state-versus-model comparison needs one readout family for both. The claim is limited to own-position linear readability with this probe family; the two inputs differ in space and dimension (Z<=6: 256-d sum of codebook contributions; prefix: 512-d residual stream), so equal readability is not equal capacity. Readability in the prefix shows that the one-step candidate mask is present in the puzzle encoding, not that the generator uses it (causal use: D102). Secondary: the whole-layer readout on Z<=6 (comparison with the manuscript's H1 probe, D66–D68). Descriptive only: whole-layer readouts on the prefix and the global BOS readout.
2. Primary statistic and inference: the paired contrast Delta = W(P_k*) − W(Z<=6), with W the mean of per-pair W-AUCs and both terms computed on the same pairs with the same weighting, and a pair-level bootstrap interval that resamples whole pairs (blocks = solution symmetry orbits if a TEST orbit repeats). Two pre-registered parts, with thresholds fixed in the protocol: (a) Delta exceeds a minimum meaningful difference; (b) W(Z<=6) lies within an equivalence band 0.5 ± epsilon (TOST at the pair level). Success of the state reading requires both: the one-sided lower bound of Delta above the minimum difference, and the two-sided 1 − 2 alpha interval of W(Z<=6) strictly inside 0.5 ± epsilon. The sample size is planned for the joint power of both parts, simulated with the chosen thresholds, the boundary cases and the interval switch of item 3. Part of the all-pair Delta is forced by locally identical Z<=6 states (observation 5); the W-AUC of Z<=6 on the bits whose local state differs is reported with an interval (pilot: per-pair mean 0.5086 over 162 pairs, as computed by the Final reviewer), which separates forced ties from weak ranking. No sign-flip test (swapping members leaves a pair's W-AUC unchanged). The E3 permuted and label controls are reported as diagnostics (observation 3); they are not a calibrated null for W = 0.5, and more refits would only estimate their own permutation distribution more precisely. A formal permutation test, if wanted later, needs its own stated null and an argument for which units are exchangeable under it; a label control, if kept, permutes the tuning labels as well.
3. Prefix layer: fixed before TEST by the rule: highest mean per-pair W-AUC on the PROBE-VAL pairs; ties broken by lower PROBE-VAL Brier, then by the lower layer index (in the pilot: P2). The layer, preprocessing and fitted probes are frozen before TEST; only that layer is scored on TEST; the P0–P8 curve is descriptive. Interval rules at the bound, stated separately: (i) prefix ceiling: when fewer than 20 pairs have a per-pair W-AUC below 1, with U_P the one-sided Clopper–Pearson upper bound of the probability of that event, W(P) >= 1 − U_P; (ii) Z<=6 band: when fewer than 20 pairs differ from 0.5, |W(Z) − 0.5| <= U_Z / 2 with U_Z the corresponding bound; (iii) Delta: on the ceiling branch, the lower bound L_P − U(W(Z)) with joint coverage, otherwise the paired pair-level bootstrap. These bounds treat pairs as independent units, so the TEST pairs keep the D99 exclusion of repeated solution orbits.
4. Population: the primary analysis uses all pairs for both representations. Secondary, for both: the stratum of pairs whose generated level 1–6 codes differ; the code-identical stratum is a negative control for Z<=6. Also reported: the share of discordant bits whose local Z<=6 cell state is identical in both members and the W-AUC restricted to the other bits (observation 5).
5. Scoring rules: predictions are compared in float64, and verified bit-identical inputs count as ties; a non-finite prediction on an evaluable bit stops the run; pairs without a discordant bit are excluded and counted, an empty stratum is reported as not estimable (null); outputs give both the per-pair means and the bit-pooled values.
6. Remaining pilot items, restricted to where a weak readout could be a fit artefact: a converged full-batch L-BFGS L2 logistic reference on inputs standardized with PROBE-TRAIN statistics, over a grid of regularization strengths, for Z<=6 (shared and whole), P2 and P8; online MDL code length (Voita & Titov 2020) for Z<=6, P0 and P2 with the shared head. The 4x AdamW refit is dropped: the uncontrolled Z<=6 fits did not select their last epoch, and the converged L-BFGS reference covers the remaining fit question (whether a longer AdamW run would select a different model is not asserted). B3 is dropped (descriptive readout).
7. Deferred to the protocol design: a readout for the level-7 query positions (they read both Z<=6 and the prefix; they do not map to cells), and a breakdown by inference-wave depth.
8. Not decided here: the activation-exchange causal test and its random-subspace control (D102).

## Review

Round R1 (sol, carbon) findings and their triage: `.reviews/e5-d101-readout/decisions.md`. Changed after R1: status line, the D96 caveat and extraction lines in Context, the weighting note above the table, Observations 1–5, and decision items 1–8. Changed after Final: Observations 1 and 4, decision items 1, 2, 3 and 6.
