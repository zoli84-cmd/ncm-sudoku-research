Verdict

Do not execute the plan as written. The most important change is to make freeze and run-validity
checks fail closed, including at completion and evaluation, before any TEST inference.

Findings

SOL-1 | blocker | Tasks 1 and 12
Claim: A run that finishes outside the code freeze can still contribute confirmatory results after
the worktree is restored.
Evidence: 2026-11-13-wp2.md:185–200 explicitly marks a code-changed run complete; evaluation at line
936 checks only starting commits and the current freeze. The upstream check at lines 196–198
verifies HEAD, not upstream worktree cleanliness; src\ncm_sudoku\g0.py:53 excludes the submodule
from CODE_PATHS.
Recommendation: Reject invalid end/stage freeze states and code-change flags during evaluation;
distinguish finished from valid. Check upstream worktree cleanliness as well as its commit, and test
restored-worktree rejection.
Confidence: high

SOL-2 | major | Task 3, steps 7–8
Claim: The specified E2 cache lifecycle cannot reliably support crash recovery or fresh dry reruns.
Evidence: 2026-11-13-wp2.md:295,335–341 supplies A_sha256 as a completion extra, but resume requires
it before completion. Step 8 also loads existing parts unconditionally, including after a dry
--force, potentially reusing outputs from superseded code.
Recommendation: Persist the A hash atomically before running stages; define recovery for crashes
around that checkpoint. Load parts only on validated resume, and isolate fresh forced runs from
previous artifacts. Test both cases.
Confidence: high

SOL-3 | major | Task 9, input and resume contracts
Claim: Resume can combine stages computed from different E3 inputs without detecting the change.
Evidence: 2026-11-13-wp2.md:729 hashes selected metadata but omits the consumed L/T representations,
empty masks and score labels. Line 768 accepts cached artifacts merely because their listed files
exist. Task 1’s input-equality check cannot protect omitted inputs.
Recommendation: Record and validate a content manifest for every consumed array and cached artifact,
including dependencies passed between runners. Add mutation tests that leave puzzle IDs unchanged.
Confidence: high

SOL-4 | major | Spec ambiguities 11–13; Task 13
Claim: Choosing the first 50 CAL puzzles does not establish the asserted matching batch shapes
throughout E2; exact dry/reference equality remains unproven.
Evidence: 2026-11-13-wp2.md:31–33,1033 assumes chunk 50 preserves reference computation. However,
src\ncm_sudoku\e2.py:22–24 decodes the entire supplied tensor; e2p2.py:83,104–105,143,211 invokes
that path. Reference outcome decoding therefore uses 300 rows, versus 50 in dry mode, although
generation is chunked.
Recommendation: Before freezing, establish CAL decoder parity across these shapes, or preserve the
reference decoding context. Pin that comparison and update D77 if the dry design must change; do not
assume numerical equality.
Confidence: high

SOL-5 | major | Tasks 3, 12 and 13
Claim: Instrumentation failures are recorded but are not required to invalidate the analysis.
Evidence: 2026-11-13-wp2.md:295,340–341,955,1041 records sham/no-op mismatches and then completes or
tabulates the run without an explicit zero-mismatch gate. research_plan_v3.7.md:48,167 requires
identity; src\ncm_sudoku\e2p2.py:428–429 notes that sham failure can put compensation outside the
range assumed by the rare-event bound.
Recommendation: Require zero identity failures for dry acceptance and confirmatory inference.
Preserve failed TEST artifacts, stop with an explicit invalid-run/deviation status, and test
rejection rather than merely reporting counts.
Confidence: high

SOL-6 | major | Tasks 2–3 and 12; protocol §7.2–§7.4
Claim: The plan omits required E2 diagnostics, rather than implementing every specified analysis.
Evidence: research_plan_v3.7.md:187,219 requires conditional-probability reporting and saved
downstream code changes, cumulative states, intermediate decodings and level-by-cell propagation
maps. 2026-11-13-wp2.md:230–235,291–295,953–955 retains the existing scalar records and summaries;
src\ncm_sudoku\e2p2.py:120–133 saves only an aggregate downstream-change count, not the required
maps or states.
Recommendation: Add explicit extraction, persistence and evaluation tasks for these outputs. Any
intentional narrowing needs the protocol’s deviation/version process, not an ambiguity
interpretation.
Confidence: high

SOL-7 | major | Tasks 8–9 and 12; protocol §8.1
Claim: Required training-budget details for every configuration and seed are discarded before
evaluation.
Evidence: research_plan_v3.7.md:227 requires these records per configuration and seed.
2026-11-13-wp2.md:642,658–664,729 persists summarize_fit output plus selected models/predictions.
src\ncm_sudoku\e3controls.py:106–125 reduces the budget to selected-config records and an aggregate
cap flag.
Recommendation: Persist all grid-by-seed budget records in an additive WP2 artifact, and test that
evaluation reports every configuration without altering existing pre-lock summaries.
Confidence: high

SOL-8 | minor | Task 6, line 518 | Moving depth summaries verbatim omits the required per-stratum
label proportions (research_plan_v3.7.md:136); add them alongside sample sizes.

SOL-9 | minor | Task 13, line 1039 | The E1 comparison still specifies 30 IDs despite D77’s
50-puzzle dry run; compare all 50 and assert the matched count.

SOL-10 | minor | Tasks 5 and 13 | Real dry controls use score=val and do not exercise random
features for new score IDs; add a distinct-score controls integration test covering row assignment,
selection independence and saved predictions.

Claims checked

 - holds — Planned family coverage, TOST levels/margins and strict equivalence inequalities match
the locked rules.
 - holds — H1’s simultaneous nonzero/equivalence readings and negative-direction precedence match
§8.3 and §13.
 - holds — Frozen AUC endpoints, absent 2–11 range and no-extrapolation rule match the saved pilot
summary.
 - holds — Probe grid, seeds, PCA construction and budget defaults match the reused implementation.
 - holds — Equivariance uses fixed 0.0116, the prescribed sample/order, and D77’s descriptive-only
interpretation.
 - holds — Planned pre-freeze real-TEST access is hash verification, not model inference; TEST
--force is prohibited.
 - does not hold — Complete protocol coverage and fail-closed freeze/resume guarantees, for the
reasons above.
 - could not verify — Numerical dry/reference reproduction or refactor parity; this review used file
reads only, as required.

