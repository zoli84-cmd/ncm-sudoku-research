Verdict

The numerical core is largely faithful, but the draft needs correction before advancing. Most
importantly, the synthesis must preserve the registered finding of small but nonzero readability,
rather than turning it into absence of readability.

Findings

SOL-1 | blocker | paper\sections\setup.tex:28
Claim: “Registered before TEST existed” misreports the preregistration chronology and contradicts
the following data-splits description.
Evidence: experiments\lock\test_set.json:2 explicitly says TEST was generated before the lock
without model evaluation; research_plan_v3.7.md:6 likewise distinguishes existing TEST puzzles from
unseen outcomes.
Recommendation: State that registration preceded every model run and outcome inspection on TEST,
whose identities and hashes were fixed before registration.
Confidence: high

SOL-2 | blocker | paper\sections\discussion.tex:9
Claim: “The candidate structure … is not visible in linearly readable form” contradicts the positive
H1 result. The adjacent claim that cell content becomes decodable “only” late also exceeds what
decoding partial states with the final decoder establishes.
Evidence: experiments\wp2\test\results.json:245–294 gives H1 = 0.002892, with its family interval
entirely positive and TOST inside ±0.01; research_plan_v3.7.md §13 explicitly requires the
positive-but-small interpretation.
Recommendation: Say candidates are linearly readable above the permuted control but below the
practical threshold; restrict the cell-content statement to the examined final decoder.
Confidence: high

SOL-3 | major | paper\sections\e3.tex:30
Claim: The unit-level raw-input target is described as perfectly readable, although only its ranking
is perfect. Conversely, chance-level observed AUC does not establish general unreadability of the
generated representation.
Evidence: experiments\wp2\test\results.json:18313–18335 reports generated AUC 0.50194; raw AUC 1.0,
but raw exact match 0.46951 and Brier 0.13610. DECISIONS.md:102 explicitly distinguishes ranking
from calibration.
Recommendation: Report all three registered metrics, describe perfect raw-input ranking rather than
perfect prediction, and qualify the generated result by the examined readout.
Confidence: high

SOL-4 | major | paper\sections\e3.tex:9; paper\sections\discussion.tex:29
Claim: The H1 redesign is attributed to interpolation without disclosing that both the primary-probe
switch and equivalence formulation followed observed near-null preparation results. H2’s analogous
pilot-driven change is disclosed clearly.
Evidence: research_plan_v3.7.md:231 explicitly records per-cell PROBE-VAL θ₁ ≈ 0.0018 and
whole-layer ≈ 0.0031 before these changes; DECISIONS.md:103–106 documents their sequence.
Recommendation: Add a concise pre-registration development history covering both H1 changes, their
pilot basis, and untouched TEST outcomes. Retain the accurate D43 disclosure.
Confidence: high

SOL-5 | major | paper\main.tex:12; paper\sections\introduction.tex:16
Claim: A positive additional-degradation magnitude, 11.1 percentage points, is paired with the
signed contrast’s negative interval [−13.6, −8.8]. These are different parameterizations.
Evidence: src\ncm_sudoku\wp4numbers.py:152 deliberately takes the estimate’s absolute magnitude;
experiments\wp2\test\results.json:298–329 stores the signed estimate and interval.
Recommendation: Either explicitly report θ₂ = −11.1 with the existing interval, or report the
degradation magnitude with the transformed interval [8.8, 13.6]. E2’s signed presentation is already
correct.
Confidence: high

SOL-6 | major | paper\sections\appendix.tex:22–50
Claim: The “Full result tables” omit registered E3 secondary outcomes, including candidate-mask
match, count MAE, F1, PR-AUC and single readouts. Depth sample sizes and raw-input depth comparisons
are also absent; merely naming D79 does not disclose its metric definition.
Evidence: research_plan_v3.7.md:136,273–277 specifies these reports. Results exist at
experiments\wp2\test\results.json:18434 onward and 19044 onward; for example, primary-probe macro-F1
is 0.0636 and naked-single F1 is 0.0165.
Recommendation: Add compact supplementary tables, including prevalence, threshold conventions, depth
denominators and D79’s cell-and-digit matching definition. Keep these analyses
secondary/descriptive.
Confidence: high

SOL-7 | major | paper\sections\e2.tex:39–43; paper\sections\appendix.tex
Claim: E2 reports edit-count curves and code/state summaries but omits important registered
intervention diagnostics: initial-damage distributions/curves, replacement geometry/probability and
spatial decoded changes. Missing AUC support does not remove these reporting obligations.
Evidence: research_plan_v3.7.md §7.2–§7.4 requires them; DECISIONS.md:116 fixes their scope.
Available outputs include experiments\wp2\test\results.json:3071–3119,3544 onward and 11665 onward.
Recommendation: Supply supplementary diagnostic summaries and define exactly which configurations
have intermediate decodings/state distances. Preserve the accurate disclosure that full state
tensors were not saved.
Confidence: high

SOL-8 | major | paper\sections\e3.tex:9; paper\sections\setup.tex:28
Claim: The below-threshold conclusion is conditional on a training budget and uncertainty scheme
that the manuscript never specifies adequately. Three training seeds are mentioned, but their
aggregation and the conditioning of confidence intervals are not.
Evidence: research_plan_v3.7.md:227–237 specifies BCE/AdamW, the grid, stopping budget and PCA
dimensions; :348 distinguishes seed stability from TEST sampling uncertainty.
experiments\wp2\test\results.json:21492 onward contains budget records.
Recommendation: Include these methods, specify averaging per-seed puzzle Briers rather than
averaging predictions, and state that intervals condition on fixed training data/fits. Report seed
stability and selected-fit budget/cap diagnostics separately.
Confidence: high

SOL-9 | major | paper\generated\tables\deviations.tex:9
Claim: The D84 row says the E4 entry condition “is not met,” suggesting an evaluated gate. The
main-text disclosure correctly describes an anticipatory decision after TEST, without SELECT
evaluation.
Evidence: DECISIONS.md:122 says the conditions were considered very unlikely to hold and explicitly
distinguishes this decision from the formal SELECT gate; research_plan_v3.7.md:289–293 locates that
gate on SELECT.
Recommendation: Change the generated summary’s source wording to “dropped after TEST because SELECT
success was judged unlikely; formal gate not evaluated.”
Confidence: high

SOL-10 | minor | paper\sections\e3.tex:38–50 | Keep the section order, but move the cross-experiment
primary/readings tables before E1; put a compact primary-probe/control table in E3 rather than
leaving its context in the appendix.

SOL-11 | minor | paper\sections\e3.tex:9,24; discussion.tex:25 | “All probes are linear” excludes
the reported MLPs; “did not improve” overlooks 0.230916 versus 0.231001. Say primary probes are
linear and the MLP’s observed gain was tiny.

SOL-12 | minor | paper\sections\e3.tex:22 | The raw MLP incorrectly uses \R{brier.rule}. Use
\R{brier.raw.mlp}; its rounded loss is zero, but its source value is not the exact rule’s zero.

SOL-13 | minor | paper\sections\e3.tex:22 | Level-6 teacher/generated losses are descriptively
similar, not supported by the registered level-12 equivalence test; replace “practically equal” with
“similar observed Brier losses.”

SOL-14 | minor | paper\sections\e3.tex:35; main.tex:12 | Say “similar observed Brier,” not unchanged
accuracy; qualify non-equivariance by sampled transformations/tolerance. Define all as the four
full-group draws, and the zero within-tolerance share as puzzle-level averaged deviations
(src\ncm_sudoku\e3equiv.py:45–108).

SOL-15 | minor | paper\sections\appendix.tex:25; generated\tables\e3_matrix.tex | The claimed
level-2/12 reference matrix omits referenced generated rows such as wl_L12.generated; add those rows
so comparisons are self-contained.

SOL-16 | minor | paper\sections\setup.tex:28 | Replace guaranteed FWER “at most” 5% with
nominal/targeted control; percentile-bootstrap coverage is approximate, as acknowledged in
research_plan_v3.7.md:356.

SOL-17 | minor | paper\sections\appendix.tex:20 | Add the actual repository URL and immutable
analysis commit; tag names alone do not identify an accessible reproducibility package.

Claims checked

 - holds — G0 reproduction and distribution-gate values match their JSON sources and stated interval
scales.
 - holds — E1 teacher reconstruction, generated performance, agreement and partial-decoding values
match TEST results.
 - holds — H1’s 98.33% family and 96.67% equivalence intervals are mapped correctly.
 - holds — E2’s signed H2/H3 estimates, secondary policies and baseline-subset values match results;
H3 practical relevance remains unresolved.
 - holds — θ₂′ uses the rare-event bound; θ_T uses the separate 90% TOST interval.
 - holds — Dose, propagation, training-size and depth numbers match their mapped descriptive
quantities.
 - does not hold — Perfect unit-target prediction is not established by AUC 1.0.
 - holds — Main-text D43 and post-TEST E4 timing disclosures agree with the log; D81–D82’s final
diagnosis is represented correctly.
 - holds — Prior-work descriptions and narrow novelty framing agree with the repository’s literature
summaries.

