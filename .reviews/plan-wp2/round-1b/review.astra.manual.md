Note: astra's automated run in this folder failed (completion verifier inconclusive). The review below was copied by the user from the Copilot session output on 2026-11-13.

Verdict
Not ready to execute as written. The most important change is to make freeze and run-validity checks fail closed, rather than treating completed execution as sufficient evidence of a valid confirmatory run.

Findings
ASTRA-1 | major | Tasks 1, 12 — freeze enforcement
Claim: The guard can accept modified upstream code, and evaluation can accept a run whose code changed during execution. A completed dry record also does not establish that comparisons passed.
Evidence: Plan:197 checks upstream HEAD, not cleanliness; line 200 marks changed-code runs complete; line 936 checks starting commits and the current freeze only.
Recommendation: Require clean upstream files, unchanged start/end code and freeze states, and a successful same-commit dry check. Reject invalid records during evaluation.
Confidence: high

ASTRA-2 | major | Task 9 — resume integrity
Claim: E3 resume can silently combine outputs from different input arrays or accept altered artifacts.
Evidence: Plan:729 excludes activations and several labels from input hashes; line 768 checks artifact existence only. Task 7 also reuses non-atomic extraction writes despite the global atomic-write requirement.
Recommendation: Hash every consumed array and saved artifact, validate schemas/shapes, compare numerical environments on resume, and publish extraction through temporary paths. Test altered-existing-file rejection.
Confidence: high

ASTRA-3 | major | Task 3 — E2 crash recovery
Claim: Resume requires a persisted A_sha256, but the specified sequence contains no pre-stage write persisting it.
Evidence: Plan:295 places the hash among finish extras; lines 335–341 save A, execute stages, then finish.
Recommendation: Persist the hash immediately after publishing A, before any stage. Define and test recovery before A exists and between publishing A and its manifest.
Confidence: high

ASTRA-4 | major | Tasks 3, 12 — sham validity
Claim: Sham/no-op failures are reported but do not prevent confirmatory inference. With B≠A, compensation can leave [−1,1], invalidating the rare-event bound.
Evidence: Plan:956 merely tabulates failures; the estimator subtracts B−A. Protocol §11.2 requires bounded differences.
Recommendation: Make nonzero sham/no-op failures invalidate E2 inference, preserving raw evidence and requiring explicit deviation handling. Test rejection before intervals or readings.
Confidence: high

ASTRA-5 | major | Ambiguity 11; Task 13 — dry-run batches
Claim: Fifty puzzles reproduce the generation chunk, but not every pilot numerical batch. Exact reproduction is therefore not established by the stated rationale.
Evidence: Plan:31 asserts matching shapes. However, E2 evaluation decodes the entire supplied tensor: 300 pilot puzzles versus 50 dry puzzles.
Recommendation: Match reference decoding batches or establish a real-model prefix-parity check before relying on the reduced dry run. Do not silently relax exact comparison.
Confidence: high

ASTRA-6 | major | Task 11 — TEST-defined AUC
Claim: test_own introduces an outcome AUC over a TEST-derived range, potentially even when the frozen comparison is prohibited.
Evidence: Plan:847 calls the existing AUC helper; protocol §7.3 permits only the CAL-fixed range.
Recommendation: Return TEST support bounds and coverage diagnostics, not another AUC. An additional analysis requires explicit exploratory/deviation treatment.
Confidence: high

ASTRA-7 | major | Tasks 2, 12 — missing E2 diagnostics
Claim: The unchanged record schema does not implement all required E2 reporting: conditional probabilities and level-by-cell propagation trajectories are absent.
Evidence: Existing records retain scalar diagnostics and total downstream changes, not trajectories. Protocol §7.2–§7.4 requests more.
Recommendation: Add acquisition/reporting tasks before the single look, or explicitly invoke §7.4's final-sensitivity limitation and log remaining omissions. Aggregate change counts cannot support propagation claims.
Confidence: high

ASTRA-8 | major | Tasks 8, 12 — discarded training budgets
Claim: Persisted outputs cannot produce the required per-configuration, per-seed budget report.
Evidence: Plan:642 uses summarize_fit; its budget summary retains selected-configuration records only. Protocol §8.1 requires every configuration and seed.
Recommendation: Persist the complete grid budget; test all 30 configuration–seed entries per trained fit.
Confidence: high

ASTRA-9 | minor | Task 6:561 | Hidden singles return (unit, digit, cell) triples, not pairs; explicitly project triples and retain cells for hidden-only classification.
ASTRA-10 | minor | Task 13:1039 | Replace the stale 30-ID E1 comparison with all 50 dry IDs; assert complete key coverage.
ASTRA-11 | minor | Task 6:518 | Moving depth summaries verbatim omits §5.2's per-stratum label proportions; add them alongside sample sizes.
ASTRA-12 | minor | Task 8:664 | Rule/marginal fits save no predictions, but evaluation requests secondary metrics per fit; persist predictions or sufficient reconstruction inputs.
ASTRA-13 | minor | Task 4 | Add originally-empty-cell Hamming; the specified E1 fields retain only the all-cell measure, unlike §10.
ASTRA-14 | minor | Ambiguity 3 | Restrict training-size conclusions to the per-cell probe; its curve cannot establish primary whole-layer data saturation. Fixed PCA does not prevent a reduced-label-training curve.

Claims checked
holds — Primary contrast signs and puzzle-first weighting match the protocol.
holds — Interval levels, strict TOST inequalities and rare-event limits match planning rules for valid inputs.
holds — H1 mechanical readings and descriptive-only equivariance agree with §13 and D77.
holds — Declared TEST hashes, frozen AUC range and tolerance match committed specifications.
holds — Grid, seeds, PCA construction and selection/scoring separation are correctly specified.
could not verify — Exact numerical dry-run reproduction; execution was prohibited.
could not verify — An initial out-of-scope home-contract read was denied; not retried.
holds — No execution commands were run and no files were created, modified or deleted.
