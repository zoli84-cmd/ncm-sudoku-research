Verdict

The primary results and their registered interpretations are sound, but two reporting errors in the
newly added E2 replacement diagnostics should be corrected before proceeding. The most important
change is to make the table’s norm definition and aggregation match the quantities actually
reported.

Findings

ASTRA-1 | major | paper\sections\appendix.tex:97
Claim: The replacement-table caption calls its norm a “per-position RMS,” but the column reports the
root-sum-square norm across replaced positions. This is a new problem in the round-2 geometry
addition, not a repetition of the earlier missing-diagnostics finding.
Evidence: src\ncm_sudoku\wp4tables.py:220–229 selects replacement_norm;
src\ncm_sudoku\e2p2.py:156,193–194 defines that as the square root of the summed squared vector
differences, without division by the number of positions. The registered RMS is separately
implemented in src\ncm_sudoku\damage.py:39–48. For level 2, frequency policy, dose 2, the table
prints 0.74, whereas the stored per-position RMS is 0.52173388
(experiments\wp2\test\results.json:1408–1414,10761–10767).
Recommendation: Either display the registered codebook_rms statistic and describe its aggregation
accurately, or rename the existing column and caption to total Euclidean replacement norm and report
the registered RMS separately. Do not interpret the existing column as dose-normalized geometry.
Confidence: high

ASTRA-2 | major | paper\sections\appendix.tex:97; paper\sections\e2.tex:41
Claim: The replacement table incorrectly inherits the damage table’s aggregation statement. Its
probability, frequency and replacement-norm quantiles are over per-puzzle averages, not pooled
puzzle–seed runs; its re-quantization column uses the latter aggregation at levels above 1. The
prose likewise describes the level-11 probability as though it were a median over individual
replacements.
Evidence: scripts\wp2_evaluate.py:376–385,439–446 first averages probabilities over replaced
positions, then averages eligible seeds within each puzzle, and finally takes quantiles across
puzzles. Conversely, src\ncm_sudoku\e2p2.py:600–615 computes the damage/re-quantization quantiles
over eligible records, and src\ncm_sudoku\wp4tables.py:225–229 combines these sources. Thus
0.0000098 is the median of per-puzzle seed-mean replacement probabilities, not the median of 1,800
individual replacement probabilities. The round-2 aggregation fix correctly describes the damage
table but was overextended to this new table.
Recommendation: Give column-specific aggregation in the replacement caption and correct the
corresponding prose. Preserve the level-1 policy-weighted qualification; explicitly distinguish
seed-averaged puzzle summaries from pooled run quantiles. No new TEST analysis is needed.
Confidence: high

ASTRA-3 | minor | paper\sections\e3.tex:9 | The budget clarification still conflates executed epochs
with selected checkpoints: every fit executes its full budget, while hit_cap means its
best-validation epoch was the final epoch (src\ncm_sudoku\probes.py:135–172). Replace “some selected
runs … reached this cap” with that checkpoint-selection statement.

ASTRA-4 | minor | paper\sections\e3.tex:15 | Specify that representation permutations are
independent in PROBE-TRAIN and PROBE-VAL, the control selects on its own permuted validation pairs,
and both probes score intact TEST pairs (research_plan_v3.7.md:251); “an unrelated state” otherwise
leaves the TEST comparison ambiguous.

ASTRA-5 | minor | paper\sections\e3.tex:38; paper\sections\appendix.tex:81 | Define “deviation” as
mean absolute probability difference over originally empty cell–digit pairs, averaged over
transformations and seed probes, and state the four full-group, two digit-only and two geometric
draws (research_plan_v3.7.md:283; src\ncm_sudoku\e3equiv.py:9–18). The reported tolerance has no
interpretable scale without this definition.

ASTRA-6 | minor | paper\sections\e3.tex:33 | The unit–digit target still omits its registered Brier
endpoint (research_plan_v3.7.md:273): generated 0.2333 versus raw 0.1361
(experiments\wp2\test\results.json:18313–18335). Add these alongside ROC-AUC and exact match; they
help explain perfect ranking without perfect thresholded prediction.

Claims checked

 - holds — Prose macro bindings and rounded values match their named source fields; the
replacement-probability problem is its description, not its binding.
 - holds — H1 is positive, 0.0029 with 98.33% interval [0.0025, 0.0033], while its distinct 96.67%
TOST interval lies inside ±0.01.
 - holds — H2’s −11.1 pp contrast and transformed magnitude interval [8.8, 13.6] are correct; H3’s
1.7 pp interval [0.1, 3.3] does not establish exceeding 3 pp.
 - holds — The level-2/11 result uses the one-sided 95% rare-event bound; level-12 teacher–generated
equivalence uses the 90% TOST interval, correctly distinguished from individual 95% intervals.
 - holds — E1’s 100% teacher reconstruction, 87.7% generated solve share, clue preservation and
partial-decoding statements agree with results; G0 and distribution-gate numbers also agree.
 - holds — Dose curves, propagation, E1 level curves and depth breakdown are presented
descriptively; unavailable frozen-range AUC and relative-versus-absolute state distance are
correctly explained.
 - does not hold — The replacement table’s RMS definition and blanket puzzle–seed aggregation
statement match its stored quantities; see ASTRA-1 and ASTRA-2.
 - holds — D43’s pre-lock CAL-driven level change and D78/D79/D81/D82 disclosures are substantively
accurate; D84 explicitly acknowledges dropping E4 after TEST without evaluating SELECT.
 - holds — Related-work claims match the repository’s source notes, including the corrected
Kniazev–Fijalkow candidate result and Khoury’s unreviewed status; novelty remains appropriately
narrow.
 - holds — The source order and confirmatory summary before E1 are appropriate; no further
structural reordering is warranted.

