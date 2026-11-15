Verdict

Not quite ready for the final round: the original confirmatory blockers are resolved, but two E2
reporting majors remain. The most important change is to distinguish quantiles of per-puzzle policy
averages from quantiles of individual interventions.

Findings

SOL-1 | major | paper\sections\appendix.tex:72; paper\sections\e2.tex:41
Claim: The new diagnostic caption incorrectly describes all quantiles as “over runs,” and the prose
describes 0.0089 as the median replacement probability. At level 1, these are quantiles across
puzzles after policy-weighted averaging over replacement values—not quantiles across individual
replacements. The table also mixes these with damage quantiles over puzzle–seed records at other
levels.
Evidence: src\ncm_sudoku\e2p2.py:572–582,620–640 averages level-1 damage within puzzle before taking
quantiles, whereas :600–615 pools eligible records for other levels.
scripts\wp2_evaluate.py:376–386,444–446 likewise averages replacement probabilities within puzzle
before taking quantiles. The macro selects the stored median correctly; its verbal interpretation is
incomplete.
Recommendation: Retain the numbers but explicitly label the aggregation units. Describe 0.0089 as
the median across puzzles of the policy-expected conditional replacement probability. Explain the
different aggregation of the level-1 and other-level damage rows; identify the latent distance as C
versus A.
Confidence: high

SOL-2 | major | src\ncm_sudoku\wp4tables.py:192–209
Claim: The accepted R1 E2-diagnostics fix remains incomplete. The new table reports damage, latent
distance and format errors, but not replacement probability or code frequency per configuration;
replacement-vector/codebook geometry also remains unreported. The level-1 probability sentence does
not cover the other configurations. This is separate from the explicitly accepted deferral of change
maps.
Evidence: .reviews\paper-wp4\decisions.md:15 explicitly accepts a table containing damage,
replacement probability, code frequency and format errors per configuration. The generator at
wp4tables.py:201–208 includes only the damage/latent/format fields. Available committed diagnostics
include p_new, p_orig, freq_new and replacement_norm (experiments\wp2\test\results.json:10627
onward); the damage summaries also contain codebook_rms and requant_ratio
(src\ncm_sudoku\e2p2.py:38–39,615,639–640).
Recommendation: Extend the generated supplementary reporting with the promised probability/frequency
summaries and replacement-geometry diagnostics, explaining their averaging and scale. No new model
run is needed; retain the agreed map deferral.
Confidence: high

SOL-3 | minor | paper\sections\e3.tex:9; paper\sections\appendix.tex:46 | Seed aggregation is
explained for Brier but not the newly reported secondary metrics. State that thresholded/ranking
metrics use seed-averaged predictions, unlike the average of seed-specific Briers
(research_plan_v3.7.md §8.1; src\ncm_sudoku\e3metrics.py:1–8).

SOL-4 | minor | paper\sections\appendix.tex:29 | The revised caption calls the marginal predictor
“label-free,” but it estimates candidate-label frequencies from PROBE-TRAIN
(src\ncm_sudoku\e3controls.py:56–64). Call it a representation-free, position-wise training-label
marginal baseline; align E3 and discussion wording.

SOL-5 | minor | src\ncm_sudoku\wp4tables.py:144–152 | The secondary-metric addition still omits
registered per-digit F1 (§8.3), exporting only macro F1 despite available f1.per_digit values
(results.json:19046–19059). Add a compact supplementary report or an explicit source pointer and
disclosure of the omitted breakdown.

SOL-6 | minor | paper\sections\appendix.tex:46 | Hidden-single F1 is described as counting (unit,
digit) items, omitting the required matching cell. Specify (puzzle, unit, digit, cell) matching and
that the displayed field is hidden_single_f1.all.f1, including naked-single overlaps
(src\ncm_sudoku\e3metrics.py:219–240).

SOL-7 | minor | paper\sections\e3.tex:33 | The rewritten unit-target paragraph says “secondary” but
drops its registered exploratory status (§8.3). Label it “secondary exploratory”; the corrected
pooling distinction and ROC-AUC versus exact-match wording otherwise hold.

SOL-8 | minor | paper\sections\introduction.tex:21 | The accepted bootstrap-coverage correction is
incomplete: the contribution still promises intervals “that control” family-wise error, while setup
correctly says approximate coverage targeting nominal control. Use the same qualification here.

SOL-9 | nit | paper\sections\discussion.tex:25 | “The E3 probes are linear” survives despite the
corrected methods and reported MLPs; change to “The primary E3 probes are linear.”

Claims checked

 - holds — Registration chronology now agrees with the pre-lock TEST-generation record; H2, H3 and
H1 pilot-driven changes are disclosed.
 - holds — New macro bindings select the intended fields and quantile indices; H2’s magnitude
interval is correctly transformed to [8.8, 13.6] pp, subject to SOL-1’s aggregation-description
issue.
 - holds — Summary tables use the correct family, equivalence and secondary intervals, including the
one-sided 95% rare-event bound for levels 2 versus 11.
 - holds — The readings table reproduces every non-null mechanical §13 row in the committed results
without promoting exploratory equivariance.
 - holds — E2’s relative-distance explanation follows the additive state construction: C’s absolute
difference stays fixed; D ends relatively farther from A than C.
 - holds — Surface-control ordering, prior-work correction, unit exact-match numbers, depth counts
and raw-depth control agree with their sources.
 - holds — Probe budget, fixed-fit interval conditioning, seed stability and unchanged pre-lock
selections agree with the implementation/results.
 - holds — D77–D84 disclosures and E4 wording correctly distinguish dropping the study from
evaluating its SELECT gate.

