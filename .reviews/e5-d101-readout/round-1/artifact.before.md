# E5 D101 draft: primary readout and W-AUC inference after the pilot

Status: draft for review, not yet in `DECISIONS.md`. Non-confirmatory planning decision, written after the D100 pilot results and before the E5 protocol and any TEST data exist.

## Context

E5 is a planned, separately preregistered follow-up to the submitted manuscript (TMLR 14707, unchanged). Question: is the weak linear readout of the level-6 candidate mask a property of the cumulative state Z<=6 or of the NCM generator? The manuscript found the candidate mask only weakly readable from the generated full-length cumulative state after level 6 (`paper/sections/e3.tex`, `paper/sections/discussion.tex`), and states that candidate reasoning could happen inside the generator's activations without leaving a trace in Z<=6, which its design does not test.

Decisions so far (all in `DECISIONS.md`):

- D94–D96, D98: positive-control gate. Our label, probe-training and metric code recovers the Kniazev & Fijalkow (NeurIPS 2026; arXiv:2605.18847) mid-layer per-cell candidate readout on their released model: exact match 0.9994 / 1.0000 / 0.9978 after blocks 4–6 (gate >= 0.99), in bfloat16 and float32. Caveat: the fixed E3 probe budget binds (all fits end at their last epoch; grid edge selected).
- D95: global-position readout uses an untied 729-output linear head; the E3 shared head (state plus cell one-hot, one 9-output head shared across cells) cannot read cell-specific candidates from one global vector.
- D97, D99: counterfactual pairs from the project's frozen generator: one solution, two 30-clue masks with unique solutions; PROBE-TRAIN 1,000 pairs, PROBE-VAL 250 pairs; no canonical-form overlap with any earlier set. Within a pair, about 32 cells are empty in both members, about 31.6 of them have a different candidate mask, about 103 differing bits.
- Extraction (`experiments/e5/extract.json`): level-7 generation pass (it reads Z<=6), prefix positions layers 0–8, closing prefix BOS layers 0–8, generated and teacher Z<=6 cell states. Pair members solved 86–88%; the generated codes of levels 1–6 are identical in only 32–35% of pairs, so the generated Z<=6 is not a function of the solution alone.
- D100: pilot specification. Primary pilot quantity: within-pair AUC (W-AUC) over bits where the cell is empty in both members and the digit is a candidate in exactly one; the share of bits where the candidate member gets the higher probability, ties 0.5. Fit on PROBE-TRAIN pairs, select and score on PROBE-VAL pairs.

## Pilot results (PROBE-VAL pairs; `experiments/e5/pilot/`)

Readouts: shared = E3 shared head on the cell's own state (D55); whole = D66 cell-relative whole-layer features (own state plus PCA-256 of the 21 states of the cell and its 20 peers); global = D95 untied head on the closing BOS. Controls: permuted = representation permuted across puzzles (E3); labels = 9-bit labels permuted across empty cells (E3 label control).

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

Observations:

1. At layer 0 the prefix position of an empty cell holds the same token in both pair members, so the shared readout gives identical predictions and W-AUC exactly 0.5. The teacher Z<=6 is identical across members by construction, also exactly 0.5.
2. The whole-layer readout at P0 is perfect: at layer 0 the 20 peer positions hold the peers' raw clue tokens, and the candidate mask is a thresholded linear function of the peer clues. On the prefix this readout measures the input, not the model's computation.
3. Controls with no readable signal (Brier 0.230–0.235, exact match 0) still give W-AUC between 0.43 and 0.58 whenever the representation differs between members. Bits within one pair are strongly correlated, so a pooled bit-level W-AUC has a much wider null spread than 0.5 plus binomial noise.
4. Every pilot fit selected the grid edge (weight decay 0, learning rate 0.003) except some global fits, as in D96.

## Draft decision D101

1. Primary readout: the shared head on the cell's own position (D55), for every representation (generated Z<=6 and the prefix layers). Reason: observation 2 makes the whole-layer readout uninterpretable on the prefix, and the state-versus-model comparison needs one readout for both. Secondary: the whole-layer readout on Z<=6, which keeps the comparison with the manuscript's H1 primary probe (D66–D68). Descriptive only: the whole-layer readout on the prefix and the global BOS readout.
2. Inference unit and null: the pair. The primary quantity is the mean over pairs of the per-pair W-AUC, compared with 0.5 by a pair-level sign-flip permutation test (swapping the two members maps a pair's W-AUC w to 1 − w) and a pair-level bootstrap interval. Secondary: per-pair difference between the representation's W-AUC and its own permuted-control W-AUC. Reason: observation 3.
3. Prefix layer: one layer fixed by a rule before TEST: the layer with the highest mean per-pair W-AUC on the PROBE-VAL pairs (P2 in this pilot); TEST scores only that layer; the P0–P8 curve is descriptive.
4. Z<=6 primary stratum: pairs whose generated level 1–6 codes differ; the code-identical pairs (W-AUC 0.5 by construction) are reported as a negative control and not pooled into the primary estimate.
5. Remaining pilot items, restricted to where a weak readout could be a probe-fit artefact: a 4x-budget refit of the selected configuration and a converged full-batch L-BFGS L2 logistic reference for Z<=6 generated (shared and whole), B3 and P8; online MDL code length (Voita & Titov 2020) for Z<=6 generated, P0, P2 and B3 with the shared head (global head for B3).
6. Not decided here: the activation-exchange causal test and its random-subspace control (D102).

## Open questions for the review

- Is the shared own-position readout a fair common readout for Z<=6 and the prefix, given that Z<=6 cell states and prefix cell states live in different spaces (256 vs. 512 dimensions; Z<=6 is a sum of codebook vectors, the prefix is a transformer residual stream)?
- Is the sign-flip test valid for the per-pair W-AUC (exchangeability of the two members under the null), given that member a and member b come from different random streams of the same generator?
- Does choosing the prefix layer on PROBE-VAL and scoring it on TEST leave any selection bias in the confirmatory estimate?
- Does excluding code-identical pairs from the Z<=6 primary stratum bias the comparison with the prefix, which is scored on all pairs?
