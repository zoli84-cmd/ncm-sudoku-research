# E5 D105 draft: confirmatory thresholds, error rates and TEST size

Status: draft for review, not yet in `DECISIONS.md`. Fixes the numbers the E5 protocol will preregister; written after the pilots (D100–D104) and before any TEST pair exists. Non-confirmatory planning decision.

## Context

E5 asks whether the weak linear readout of the level-6 candidate mask in the NCM Sudoku generator's cumulative state Z<=6 is a property of that state or of the generator. Design so far (all in `DECISIONS.md`):

- Counterfactual pairs (one solution, two 30-clue masks) from the project's frozen generator (D97, D99); TEST pairs will come from a fresh seed namespace (10) with the canonical-form orbit exclusion of D99.
- D101 (after review): primary readout = seed-averaged shared own-position linear head (D55) for both Z<=6 and the prefix layer k* (P2 in the pilot, fixed on PROBE-VAL); W = mean over pairs of the per-pair within-pair AUC (W-AUC); primary contrast Delta = W(P_k*) − W(Z<=6) on the same pairs; success of the state reading needs both a one-sided lower bound of Delta above a minimum difference and the two-sided 1 − 2 alpha interval of W(Z<=6) inside 0.5 ± epsilon; joint power to be simulated; separate exact bounds at the ceiling; pair-level bootstrap.
- D102–D104 (after review): activation-exchange causal test at layer 2 of the prefix, level-7 pass with the recipient's levels 1–6 fixed; primary outcome = directed TV movement of the level-7 code distributions towards the both-empty full-swap reference; controls: norm-matched random subspaces, a high-variance control (cosine with the full difference 0.471 vs. Q 0.541), a shuffled-digit control.

Pilot per-pair statistics (PROBE-VAL, 250 pairs): W(Z<=6) 0.5036, SD 0.0445; Delta 0.496, SD 0.0445, minimum per pair 0.304; causal Q directed 0.052, SD 0.061; Q minus high-variance 0.030, SD 0.041; Q minus random mean 0.049; Q minus shuffled 0.131. Z<=6 control W-AUCs (permuted, labels): 0.497, 0.508. Rough normal-approximation sizes for the Z<=6 equivalence alone (one-sided 5%, power 90%, pilot SD and mean): epsilon 0.02 → about 63 pairs, 0.03 → about 25, 0.05 → about 8.

## Draft decision D105

1. Equivalence band for Z<=6: epsilon = 0.03, i.e. W(Z<=6) must lie in (0.47, 0.53). Reason: the pilot value and the Z<=6 control values lie within 0.497–0.508, so 0.03 leaves a margin for probe-induced shifts of that size, while a W-AUC of 0.53 is substantively negligible next to the prefix's value near 1.0.
2. Minimum difference: Delta must exceed 0.25 (one-sided lower bound), half the distance between chance (0.5) and perfect within-pair ranking (1.0).
3. Causal decision rule: the generator's level-7 code choice counts as sensitive to the candidate directions only if all three hold: the one-sided lower bound of the Q directed effect exceeds 0.01 (TV); the lower bound of Q minus the high-variance control exceeds 0; the lower bound of Q minus the shuffled-digit control exceeds 0.
4. Error rates: three primary tests (Z<=6 equivalence, Delta, causal), family-wise alpha = 0.05 with Bonferroni, alpha = 0.05/3 per test, as in plan v3.7; intervals accordingly (two-sided 1 − 2 alpha for the equivalence, one-sided 1 − alpha bounds otherwise).
5. TEST size: 500 pairs (1,000 puzzles) from seed namespace 10. Reason: the primary tests need far fewer pairs (to be confirmed by the final simulation), but the secondary strata need more: code-different pairs are about 65%, pairs with exactly one solved member about 20% (about 100 at 500 pairs) for the rescue analysis. Estimated cost: extraction about 1 h, causal evaluation about 1 h, probe scoring minutes.
6. The final simulation (after these numbers are fixed) resamples the pilot per-pair values (PROBE-VAL pairs) with the real decision rules, the interval switch at the bounds and the Bonferroni levels, under the pilot effects and under boundary scenarios (W(Z<=6) shifted to 0.5 ± epsilon, Delta shifted to 0.25, causal effects shifted to the thresholds), and reports the joint power and the false-positive rates. If the joint power at 500 pairs is below 0.9, the protocol revisits the size before TEST generation.

## Open questions for the review

- Are epsilon = 0.03 and the Delta minimum 0.25 defensible as substantively meaningful, given that the PROBE-VAL controls of the prefix representations showed systematic W-AUC shifts up to ±0.07 (D101 observation 3) while the Z<=6 controls shifted by at most 0.008?
- Is a Bonferroni split over three tests appropriate when the state reading requires two of them jointly (equivalence and Delta) and the causal test answers a different question?
- Is the causal minimum effect 0.01 TV sensible relative to the pilot (Q 0.052; full-swap reference 0.061; 14.2% of recipients with TV(clean, full) below 0.01)?
- Is 500 pairs justified, or is a smaller TEST preferable, given that larger TEST sets make small probe-induced biases in W(Z<=6) more likely to exceed a narrow band?
