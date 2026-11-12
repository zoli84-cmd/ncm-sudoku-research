Verdict

Nearly ready, but correct the H1 interpretation table before locking: above-null readability must
require a positive 98.33% lower confidence limit, not merely a positive estimate. The disclosed
pre-TEST redesign and the combined difference/equivalence framework are otherwise defensible; no
redesign is indicated by this review.

Findings

ASTRA-1 | major | research_plan_v3.7.md:464–465
Claim: The first H1 interpretation row permits “readable above the permuted null control” from θ₁ >
0 plus equivalence, without requiring the family interval to exclude zero. Operationally, a positive
estimate with an interval crossing zero can satisfy both adjacent rows, conflating demonstrated
positive readability with equivalence alone.
Evidence: Section 8.3 correctly requires the 98.33% interval to exclude zero. The simulation also
correctly requires its lower limit to exceed zero for the combined positive-and-equivalent outcome
(src\ncm_sudoku\power.py:250–280); the interpretation table omits that condition.
Recommendation: Require “98.33% lower limit > 0 AND 96.67% interval wholly inside (−0.01, 0.01)” for
the positive-but-small claim. Keep zero-crossing results as equivalence-only, and distinguish
significantly negative improvements from successful readability.
Confidence: high

ASTRA-2 | minor | research_plan_v3.7.md:286 | Claim: Transformation aggregation remains ambiguous
after CARBON-5: the quoted 0.079 is not an average over all eight transformations. Evidence:
src\ncm_sudoku\e3equiv.py:62–83 averages each category separately;
experiments\lock\equivariance_l12.json:306–315 reports 0.078914 for the four full-group draws.
Recommendation: Explicitly identify that headline and report digit-only and geometric-only results
separately. Confidence: high

ASTRA-3 | minor | research_plan_v3.7.md:269 | Claim: Teacher/generated equivalence does not
establish that generated readout is literally “no better.” Evidence: The specified ±0.01 equivalence
region permits positive improvements smaller than 0.01. Recommendation: Say “no practically
meaningful difference within the pre-specified ±0.01 margin,” retaining the probe-family and budget
qualification. Confidence: high

ASTRA-4 | minor | experiments\lock\cal_freqs.json:16 | Claim: Frozen-frequency provenance
incorrectly describes the execution setting as deterministic=false. Evidence:
scripts\lock_cal_freqs.py:45–48 records the environment before src\ncm_sudoku\model.py:53 enables
deterministic algorithms. Recommendation: Capture the environment after initialization and reconcile
the provenance before finalizing its pinned digest; this is stale metadata, not evidence that
inference actually ran nondeterministically. Confidence: high

Claims checked

 - Holds: The 98.33% difference interval and 96.67% TOST interval are coherent. Their null sets—θ₁ =
0 versus |θ₁| ≥ 0.01—are disjoint, so sharing H1’s α = 0.05/3 allocation does not itself require
another multiplicity penalty, subject to interval calibration.
 - Holds: Sections 8.1/8.3 and D65–D70 disclose the outcome-informed preparation changes. Such
selection is defensible before an independent, unopened TEST; retaining the original per-cell
analysis and limiting absence claims to the examined readout are appropriate.
 - Holds: Whole-layer/PCA construction, frozen peer-order wiring, whitening, position features,
permutation seeds, selection and per-seed Brier averaging match the code. Results support θ₁ =
0.00311054, budget change +0.00004150, raw projected/unprojected Briers 0.00144032/0.01050786, and
teacher−generated ≈0.00031230. The reported flat training-size curve is specifically the per-cell
curve.
 - Holds: Frozen CAL counts for levels 1/2/6/11 match the table; level-1 frequencies match the
pilot. The runner accepts frozen frequencies. E2 requirements 200/400/300/600, the full-precision
6–11 AUC range, and absence of a positive-width 2–11 range match the stored results.
 - Holds: inject gives E[X′] = mean(X) + zero_share × p × sign(target) = target, preserving nonzero
values and bounded support. Stored E2 boundary errors are 0.0245/0.0365; the latter is acceptable
against this secondary test’s 0.05 nominal level for this scenario, not a universal calibration
guarantee. H1 power 1.000 and boundary errors 0.016/0.014 match the file.
 - Holds: Level-12 tolerance derives from 0.01164455 and is explicitly locked to 0.0116. The stored
deviation and zero within-tolerance share support non-equivariance at that tolerance; Briers
0.182834 versus 0.182784 support descriptively almost unchanged average performance, not proven
population equality.
 - Holds: Recorded checkpoint/released-data revisions and hashes, generator/label hashes, TEST
identity hashes/formats, namespaces, 600 puzzles and 6,400-grid collision-free screen agree with
§12.2. G0 records 86.3% and 17 successful identity checks. The TEST-generation script performs no
model inference.
 - Could not verify: Actual byte-level digests—including the CAL-frequency file and peer-index
array—were not recomputed, and repository records cannot independently prove that nobody has run
another model command on TEST. Inspection remained read-only; no execution commands were attempted.

