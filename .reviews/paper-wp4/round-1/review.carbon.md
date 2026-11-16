I will read the review brief at `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\paper-wp4\round-1\brief.carbon.md` to understand the exact scope, criteria, and required format for this read-only review.

I have read the review brief and am now reading all manuscript `.tex` files (`main.tex` and all sections in `paper\sections\`) in parallel.

Verdict

The statistical pipeline and macro-generated numbers faithfully reflect the committed confirmatory
outputs, so the draft has a sound empirical foundation, but it is not ready for arXiv as written
because of two blockers and four major issues in metric description, §13 claim boundaries,
prior-work accuracy, and disclosures. The single most important change is fixing the misdescription
of relative cumulative-state ratios as decaying state distances in E2 (CARBON-1) alongside
tightening the Abstract, Introduction, and Discussion so every cross-experiment claim respects the
registered §13 boundaries and separates confirmatory from exploratory results (CARBON-2).

Findings

CARBON-1 | blocker | paper/sections/e2.tex:79-81, 102-104; src/ncm_sudoku/wp4figures.py:117
Claim: The manuscript and Figure 4 describe state_dist as the cumulative-state distance from the
clean run and assert that it "decreased towards the last level in both C and D." In fact, in branch
C the unnormalized Euclidean distance to A is algebraically constant across all 12 levels; only the
relative ratio falls because the denominator $\lVert Z_{\le\ell}^A\rVert_2$ grows, and branch D ends
farther from A than C.
Evidence: src/ncm_sudoku/e2p2.py:97-98 defines state_dist as $\lVert Z_{\le\ell}^X -
Z_{\le\ell}^A\rVert_2 / \lVert Z_{\le\ell}^A\rVert_2$. In src/ncm_sudoku/states.py:21-25,
$Z_{\le\ell}$ sums per-level contributions that depend only on each level's own codes, so replaying
A's levels 2–12 in C keeps $Z_{\le\ell}^C - Z_{\le\ell}^A \equiv Z_{\le 1}^C - Z_{\le 1}^A$. Even
the relative ratio rises at level 5 (0.841 to 0.863), and D exceeds C at levels 7–12 (0.186 vs.
0.155 at level 12; experiments/wp2/test/results.json:11667, report.md:122).
Recommendation: Rename the y-axis and caption of Figure 4 to relative cumulative-state distance
$\lVert Z_{\le\ell}^X - Z_{\le\ell}^A\rVert_2 / \lVert Z_{\le\ell}^A\rVert_2$, note that C's
unnormalized perturbation norm is constant across levels, and report that D's final state deviates
slightly more from A than C's despite higher solve rate.
Confidence: high

CARBON-2 | blocker | paper/main.tex:12; paper/sections/introduction.tex:22;
paper/sections/discussion.tex:9-16
Claim: Three high-visibility summary statements cross registered §13 claim boundaries or present
exploratory observations as confirmatory verdicts: discussion.tex:14 says level-6 candidate
structure is "not visible in linearly readable form," main.tex:12, introduction.tex:22, and
discussion.tex:9-10 state flatly within confirmatory summaries that the level-12 readout "was not
equivariant under Sudoku symmetries," and main.tex:12 reports H3 (1.7 pp) without its 3.0 pp
practical threshold.
Evidence: experiments/wp2/test/results.json:263, 845 rejects zero H1 readability (98.33% CI [0.0025,
0.0033] > 0) and research_plan_v3.7.md:458 forbids concluding that no candidate readability exists
(only readability below 0.01 Brier). Level-12 equivariance is exploratory with no registered
criterion (research_plan_v3.7.md:308, 369, 463; src/ncm_sudoku/wp2eval.py:25), and H3's
pre-specified minimal practical effect is 3.0 pp (research_plan_v3.7.md:382, e2.tex:54).
Recommendation: Revise discussion.tex:14 to "only weakly visible (below the 0.01 Brier practical
threshold) in linearly readable form"; qualify equivariance in Abstract, Introduction, and
Discussion as exploratory, accurate on transformed grids, and non-equivariant at the 0.0116
seed-noise tolerance (with its §13 boundary); and state in main.tex:12 that H3's 1.7 pp estimate
lies below the 3.0 pp practical threshold.
Confidence: high

CARBON-3 | major | paper/sections/discussion.tex:20-25; paper/sections/e3.tex:48-50
Claim: discussion.tex:20-21 misstates Kniazev & Fijalkow (2026) by claiming their per-cell candidate
probes did not reach perfect exact match, while e3.tex:48-50 overstates our raw-input unit-digit
control as reading the target "perfectly" by citing only ROC-AUC (1.0) and omitting exact match
(47.0%).
Evidence: The project's primary-source verification
(literature/kniazev_fijalkow_2026_unit_probe.md:43-50) shows their 729 per-cell candidate probes
reached 1.0 exact match across layers 4–6 (only deteriorating at layer 8), whereas their 81
filled-digit probes plateaued at 0.8 (fixing an earlier conflation in research_plan_v3.7.md:29,
296). On TEST (results.json:18313-18335), our pooled unit-digit probe achieved ROC-AUC 1.0 on raw
input (0.50 generated) but exact match 47.0% (0.9% generated; Brier 0.1361 vs. 0.2333), and
DECISIONS.md D62 notes that pooling 9 cell states does not replicate kniazev2026linear's global
[clues_end] token readout.
Recommendation: Correct the description of kniazev2026linear in discussion.tex:20-21, report
pre-specified exact match (\R{unit.gen.exact}, \R{unit.raw.exact}) and Brier alongside ROC-AUC in
e3.tex:48-50, and note the pooled-cells versus single-anchor readout difference.
Confidence: high

CARBON-4 | major | paper/sections/e3.tex:27-35; paper/sections/discussion.tex:38-40
Claim: The main text omits the pre-specified surface-correlation control (\R{brier.surface} =
0.2253), which outperforms the primary level-6 generated probe (0.2307) using only puzzle-wide clue
digit counts and cell position, and omits several pre-specified secondary results altogether.
Evidence: src/ncm_sudoku/e3data.py:134-140 builds surface_features from global clue count and 9 clue
digit frequencies; in results.json:18100 (paper/generated/tables/e3_matrix.tex:18),
controls.surface_linear reaches 0.2253 vs. 0.2307 for wl_L06.generated, yet introduction.tex:28,
e3.tex:27-35, and discussion.tex:38-40 omit it. Also omitted are all §8.3 secondary candidate-mask
metrics (results.json:19044: macro F1 0.064, PR-AUC 0.416 at 0.367 positive rate, mask exact match
0.2%, count MAE 3.08, naked/hidden-single F1), §11.1 per-seed H1 stability (results.json:35412),
§8.1 config-selection parity (results.json:34934), and the §4.1 secondary E1 stratum on the 2,000
released boards (experiments/wp1/e1_released.json).
Recommendation: Report \R{brier.surface} in e3.tex:27-35 and discussion.tex:38-40 so readers see
that level-6 linear readout falls short of global digit-frequency correlations, and add concise
prose/appendix coverage of the §8.3 secondary metrics, seed/selection stability, and released-set E1
check.
Confidence: high

CARBON-5 | major | paper/sections/e3.tex:12-15; paper/sections/discussion.tex:42-46;
paper/sections/appendix.tex:4-18; src/ncm_sudoku/wp4tables.py:18-24
Claim: Pre-lock and post-lock disclosures are incomplete and internally inconsistent: pre-lock
pilot-driven changes to H3 (D45) and H1 (D65–D68) are omitted or attributed only to architecture,
while Table 4 (tab:deviations) lists unreported D79 (naked-single F1) as bearing on reported
analyses yet omits D77 and D78(Q1).
Evidence: discussion.tex:42 places pre-lock D43 under \paragraph{Post-registration decisions.} and
omits that H3 also moved from level 2 to level 1 on CAL (DECISIONS.md D45;
research_plan_v3.7.md:534). e3.tex:12-14 omits that switching H1 to the whole-layer probe and adding
the $\pm 0.01$ TOST equivalence range followed near-null PROBE-VAL estimates (0.0018 per-cell,
0.0031 whole-layer; research_plan_v3.7.md:229-235, osf/registration.md:45). In appendix.tex:5-14 and
wp4tables.py:18-24, D79 is listed though naked-single F1 is never reported, whereas D77 (21
pre-freeze readings, including level-12 CI criterion and level-2 whole-layer $\theta_1$) and D78(Q1)
(whole-layer level-6 controls and training-size curve) are omitted; meanwhile pre-TEST Windows
rename bug D81–D82 is repeated in four places (setup.tex:60, discussion.tex:43, appendix.tex:9-12,
tab:deviations). (D84's post-TEST drop of E4 is accurately disclosed in discussion.tex:48-54.)
Recommendation: Split pre-lock pilot adaptations (D43, D45, D65–D68, including PROBE-VAL motivation)
from post-lock readings/fixes, update DEVIATIONS in wp4tables.py to cover D77 and D78(Q1) (and
either report naked-single F1 or drop D79's "reported" claim), and trim D81–D82 to Appendix A.1
only.
Confidence: high

CARBON-6 | major | paper/sections/e3.tex:62-75; src/ncm_sudoku/wp4tables.py:66-90;
paper/sections/e2.tex:72-75
Claim: The section order (Intro, Background, Setup, E1, E2, E3, Discussion) works well, but burying
the study-wide primary tables (tab:primary, tab:readings) at the end of e3.tex leaves E2 unlinked,
wp4tables.py:67 silently drops half of H1's and H3's triggered §13 rows, and e2.tex:72-75 invokes an
undefined "common damage range" and "TEST nodes."
Evidence: tab:primary and tab:readings are cited only in e3.tex:24. In
src/ncm_sudoku/wp4tables.py:67, next(...) takes only the first matching readings entry per
hypothesis, dropping probe_beats_null for H1 ("Does not follow: ... the generator uses the read-out
feature") and positive_compensation for H3 (results.json:859-915). tab:primary cites "the 96.67%
interval" in its text column without showing that interval or H2/H3 practical thresholds (5.0, 3.0
pp). In e2.tex:72-75, E2's initial-damage metric (mean cell-wise 12-token decoder TV distance
between C and A, research_plan_v3.7.md:195-203) is never defined.
Recommendation: Move a unified or paired confirmatory summary table to Section 7.1 (with forward
pointers from Setup/E2/E3), include all triggered §13 rows (H1, H2, H3, plus secondary theta2_prime
and level12), add practical thresholds and H1's 96.67% TOST interval to tab:primary, and define
decoder TV initial damage and per-dose nodes in e2.tex.
Confidence: high

CARBON-7 | minor | paper/sections/e3.tex:32-33 | Prose binds both the raw-input MLP and the exact
rule to \R{brier.rule}; use \R{brier.raw.mlp} (2.1e-8, rounded to 0.0000) for the MLP and
\R{brier.rule} (0) for the rule to preserve key provenance.
CARBON-8 | minor | paper/sections/appendix.tex:31-35; paper/generated/tables/e3_matrix.tex |
tab:e3-matrix's caption says relative differences use "the reference row of the same construction"
and lists label-free as a Constr. value, whereas input rows reference whole_layer/per_cell probes
and no row has Constr. = label-free; rewrite caption to state (Brier - ref)/ref against the matched
probe family.
CARBON-9 | minor | paper/sections/appendix.tex:46-52; paper/sections/e3.tex:56-58 | tab:equivariance
labels the 4 full-group draws all, making 0.0791 > max(0.0686, 0.0782) look impossible next to digit
and geometric, and e3.tex:56 omits TEST seed-noise P95 (\R{equiv.seednoise} = 0.0117, required by
plan §8.4); rename all to full group and report \R{equiv.seednoise}.
CARBON-10 | minor | paper/sections/e2.tex:63-66; paper/sections/setup.tex:53-55 | e2.tex:65 reports
the $\theta_2'$ rare-event bound [-1.5, 1.5] pp without its level, and setup.tex:55 states only H1's
96.67% TOST level; state that $\theta_2'$ uses a 90% TOST replaced under the rare-event rule by the
one-sided 95% Clopper–Pearson bound (wp2eval.py:64-65).
CARBON-11 | minor | paper/main.tex:12; paper/sections/introduction.tex:22 | Both sentences pair
positive magnitude \R{h2.est.abs} ("lowered by 11.1 points") with negative signed bounds [-13.6,
-8.8], and main.tex:12 omits H1's interval; align sign conventions and add [\R{h1.fam.lo},
\R{h1.fam.hi}] in the abstract.
CARBON-12 | minor | paper/sections/e3.tex:38-41; src/ncm_sudoku/wp4figures.py:165-178 | The depth
breakdown omits stuck (0.2394, 89 puzzles / 2,842 cells) in prose, per-stratum sample sizes, and the
flat raw-input depth control (0.0014–0.0015) required by plan §5.2/§8.3 (report.md:166); add counts,
stuck, and raw-control context.
CARBON-13 | minor | paper/sections/e2.tex:81-82; src/ncm_sudoku/wp4figures.py:89 | Prose says state
distances exist "only for the primary configurations," but Figure 4 (right) plots secondary
level1-uniform; state accurately that they exist for all enumerated level-1 values (both policies)
and L11-frequency-d1 (report.md:142).
CARBON-14 | minor | paper/refs.bib:1-60; paper/sections/discussion.tex:25 | refs.bib omits first
names/initials (Kumbong and others truncates co-authors in plainnat), omits venues on
hewitt2019control/belinkov2022probing, leaves shah2024logic uncited, and discussion.tex:25 does not
note in text that khoury2026roundtrip is an unreviewed preprint (plan §2.1, §15); complete refs.bib
and add the caveat in prose.

CARBON-15 | nit | paper/sections/introduction.tex:6, 9-15 | Note parenthetically that H2, H3, H1
retain their preregistered labels in E2-before-E3 order, and mention at introduction.tex:6 that the
conditional causal step (E4) was not executed.
CARBON-16 | nit | paper/sections/e1.tex:13; src/ncm_sudoku/wp4numbers.py:182 | "kept every clue
(\R{e1.clues}\%)" reads cell-level clue_preservation rather than puzzle-level all_clues_preserved
(both 100.0% on TEST, distinct on G0); bind e1.clues to all_clues_preserved.
CARBON-17 | nit | paper/sections/setup.tex:12; paper/sections/e3.tex:43 | Clarify at setup.tex:12
that upstream evaluation already uses FP32 eager and differs only in CUDA vs. CPU (plan §2.2), and
add the 95% interval [\R{theta1.wl.L02.ci.lo}, \R{theta1.wl.L02.ci.hi}] at e3.tex:43.

Claims checked

 - G0 reproduction (86.3% vs. 86.1%, 17/17 identity checks) and fresh-batch gate (TVD = 0.017, 86.6%
vs. 86.3%, 90% CI [-1.6, 2.0] pp) in setup.tex:13-27 against reproduction.json and gate.json: holds.
 - Exact duplicate and canonical symmetry-orbit screening across all 6,400 grids (setup.tex:31-32)
against test_set.json:631 and symmetry.py:102: holds.
 - E1 TEST metrics (teacher 100.0%, solve/official 87.7%, cell accuracy 98.1%/97.0%, 0.44
violations, 0.0% partial-level solves) in e1.tex and tab:e1 against results.json:1162-1285: holds.
 - Primary contrasts H1 (0.0029, 98.33% [0.0025, 0.0033], 96.67% TOST [0.0025, 0.0033]), H2 (-11.1
pp [-13.6, -8.8]), and H3 (1.7 pp [0.1, 3.3]) against results.json:245-366: holds.
 - Secondary E2 contrasts ($\theta_2' = 0.0$ pp, bound [-1.5, 1.5] pp), level-6/11 dose shares, and
TEST TV-damage non-coverage of the frozen CAL range (e2.tex:63-75) against results.json:585-1155,
1286-3540: holds.
 - Cumulative-state distance from the clean run decreased towards the last level in both C and D
(e2.tex:79-81) against e2p2.py:97, states.py:24, and results.json:11667: does not hold.
 - Level-6 candidate structure is "not visible in linearly readable form" and level-12
non-equivariance as unqualified confirmatory summary (discussion.tex:14, main.tex:12,
introduction.tex:22) against research_plan_v3.7.md §8.4, §13: does not hold.
 - Kniazev & Fijalkow (2026) per-cell candidate probes missed perfect exact match and raw unit-level
probe read "perfectly" (discussion.tex:20-21, e3.tex:48-50) against
kniazev_fijalkow_2026_unit_probe.md:43-50 and results.json:18329: does not hold.
 - Completeness and accuracy of pre-lock/post-lock disclosures (discussion.tex:42-54,
appendix.tex:4-18) against DECISIONS.md D43, D45, D65–D68, D77–D84 (D84 holds; D45, D65–D68
motivation, D77, D78(Q1), D79 do not): does not hold.
 - External embargoed OSF record (]8;id=md-ysxt3g;https://osf.io/m28fxhttps://osf.io/m28fx]8;;]8;;) and rendered PDFs in ]8;;
paper/generated/figures/*.pdf (not opened under repository-only / text-only rules;
osf/registration.md and wp4figures.py match): could not verify.

