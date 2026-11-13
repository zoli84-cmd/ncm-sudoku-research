Verdict

Not yet ready to execute as written. The most important remaining change is to make E3 progress
checkpoints fully validated and crash-atomic, including the numerical summaries used for inference
and the complete training budgets.

Findings

ASTRA-1 | major | Task 9 — checkpoint integrity and publication
Claim: Resume validates saved models and predictions, but not the stored numerical summaries
themselves. Additionally, separately replacing e3_fits.json and e3_budget.json leaves a crash window
in which a stage is considered finished without its full budget.
Evidence: 2026-11-13-wp2.md:945–953,1012 specifies artifact validation and a final-only fits_sha256,
with completion determined from e3_fits.json. A changed stages.*.per_puzzle value can survive resume
and acquire a fresh final hash. The existing src\ncm_sudoku\e3controls.py:106–125 retains only
selected-configuration budget details in summaries, so missing full budgets cannot be reconstructed
from them.
Recommendation: Publish a per-stage checkpoint containing its summary, full budget and artifact
manifest, with one atomic completion marker and a recorded digest checked on resume. Add mutation
tests for summary values and budgets, and crash tests between every publication step. This closes
gaps left by the new model/input mutation tests.
Confidence: high

ASTRA-2 | major | Tasks 1, 9, 13 — dry approval is not bound to the validated inputs and outputs
Claim: The TEST guard accepts a same-commit passing Boolean without establishing that it describes
the current dry records. A completed dry --force rerun can leave an older passing check usable;
likewise, fresh TEST fitting can accept changed PROBE arrays with unchanged ids.
Evidence: 2026-11-13-wp2.md:254 checks the dry record’s validity and the check’s Boolean/commit, not
their correspondence. Lines 953 and 1363–1379 specify resume-input comparisons and dry comparisons,
but no binding of the approval to their exact snapshots. Fresh E3 preconditions at lines 949–952
check PROBE ids/counts, whereas line 70 requires unchanged training/validation data.
Recommendation: Record and verify the dry records’ and compared artifacts’ hashes in check.json;
invalidate approval when any dry runner restarts. Before TEST, also require shared PROBE input
hashes to equal those in the approved dry run. Test stale approval after --force and same-id PROBE
mutation before a fresh TEST start.
Confidence: high

ASTRA-3 | major | Tasks 11–12 — summarize2 bypasses the new inference restrictions
Claim: The revised evaluation still consumes summarize2 for descriptive E2 tables, but that function
unconditionally computes intervals, TOST-related results and TEST-derived-range AUCs. Selecting only
its descriptive return fields does not prevent these computations, including on the identity-failure
path.
Evidence: 2026-11-13-wp2.md:1209,1243 retains this dependency, contradicting lines 1099 and 1218.
src\ncm_sudoku\e2p2.py:375–391 computes contrasts before constructing tables, and line 447 calls
auc_pair unconditionally. The new isolated auc_frozen test does not cover this indirect call.
Recommendation: Extract a statistics-free descriptive-summary helper and use it in WP2; preserve
summarize2 for pre-lock callers. Add evaluation-level tests that forbid every auc_pair call and
every E2 interval call when identity fails.
Confidence: high

ASTRA-4 | major | Tasks 2–3 — identity gate checks outcomes, not branch identity
Claim: The new invalidation gate can accept a sham with different codes whenever its binary solve
outcome matches A. This is narrower than the promised “any sham mismatch” gate and can miss a faulty
restart that also affects intervention results.
Evidence: 2026-11-13-wp2.md:396–397 adopts the existing mismatch counts.
src\ncm_sudoku\e2p2.py:429–433 compares only solve_B/solve_B1 against solve_A; its no-op check at
lines 174–180 likewise does not verify regenerated-code identity. By contrast, the established G0
identity checks use exact code equality (src\ncm_sudoku\g0.py:72–75).
Recommendation: Count exact per-puzzle code mismatches for B1/A, each B/A, and no-op D/A before
discarding branch tensors. Gate validity on these technical counts while retaining the existing 20
outcome fields unchanged. Test a changed sham suffix with an unchanged solve outcome.
Confidence: high

ASTRA-5 | minor | Task 9, line 988 | Clarify the score-label mutation test:
fit_selected.val_brier_mean is the scored endpoint, so it must not be required to remain unchanged;
assert unchanged selection/model parameters and tuning loss, but recomputed score loss.

ASTRA-6 | minor | Tasks 3 and 15, lines 393–395,1485 | The runtime re-estimate requires E2 per-stage
seconds, but the specified part schema/callback does not persist them; explicitly record stage and
diagnostic timings before relying on that forecast.

Claims checked

 - holds — Core start/end freeze checks, upstream cleanliness and restored-worktree rejection are
specified; all five same-runner dry prerequisites have producers.
 - holds — Technical-only stdout/run-record contracts remove the identified outcome disclosures.
 - does not hold — Dry approval freshness and complete E3 checkpoint integrity remain incomplete, as
above.
 - holds — The default decode path retains one whole-tensor call; exact dry comparison is an
appropriate empirical gate for the 300-to-50-row change.
 - could not verify — Bitwise/RNG invariance awaits implementation; level_logits has the correct
conditional target, but level-1 logits must be exposed before _level0_from_queries applies argmax.
 - holds — Whole-layer controls specify 512 features/593 probe inputs, teacher T06.npy, and the
full-training PCA for the size curve; D64/D67 comparisons remain mapped.
 - holds — NaN-safe TOST, corrected hidden-single matching, None/bool dry comparisons, 50-id E1
coverage, fallback readings and D78 disclosure address their accepted findings.
 - could not verify — Approximately 8.1 h dry and 17.5 h TEST are plausible planning totals from
recorded stage times, but the additional E2 diagnostic cost remains unmeasured.

