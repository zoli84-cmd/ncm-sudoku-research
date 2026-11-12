Verdict

Resolve one E2 execution-path inconsistency before locking; the statistical design, H1 revision
disclosure, and restricted interpretation rules are otherwise coherent. The most important change is
to preserve matched A–D batching during level-1 enumeration and validate that actual execution
path.

Findings

ASTRA-1 | major | research_plan_v3.7.md:48; §12.2 E2 main contrast
Claim: The runner explicitly designated for confirmatory E2 violates the identical-batch requirement
underlying the numerical identity guarantee. Level-1 enumeration changes batch composition and
sizes for C/D while retaining A/B from the original batches, potentially confounding intervention
effects with numerical differences.
Evidence: src\ncm_sudoku\e2p2.py:87–100,131–145 generates A/B over all puzzles but selects a1 != v
before running C/D. For example, the frozen CAL counts give 29 original zeros, so replacement value
0 processes 271 rather than 300 puzzles: regeneration ends with 21 rather than 50 rows, and decoding
uses 271 rather than 300 rows. The reported sham check compares full-population B1 with A
(e2p2.py:364–369), not clean runs under these enumeration-specific batches. G0 identity checks
likewise use an unchanged batch (src\ncm_sudoku\g0.py:66–75). This establishes a protocol mismatch,
not that any reported outcome necessarily changed.
Recommendation: Execute enumeration on the same complete, ordered batches as A/B, retaining
original-value rows as zero-weight/no-op rows and filtering only afterward. Check code/output
identity through this path on CAL before locking; reassess affected planning outputs if numerical
outcomes change.
Confidence: high

ASTRA-2 | minor | §11.4: The “100 puzzles suffice” result uses the superseded per-cell differences
(experiments\e3prep\sample_size_h1.json:8–11), not the whole-layer primary; label it historical or
recompute for the new probe. Confidence: high.

ASTRA-3 | minor | §11.3: Formula, reference categories, and simplification order are promised but
not specified; freeze them or explicitly classify the GLMM as an exploratory, non-preregistered
analysis. Confidence: high.

ASTRA-4 | minor | §8.2; DECISIONS.md:95: The required same-solution/different-clue-mask teacher
control lacks a locked sampling and mask-generation recipe; specify its size, seeds, grouping and
aggregation, or explicitly defer it as exploratory. Confidence: medium.

Claims checked

 - Holds: H1’s 98.33% difference interval and 96.67% TOST are nominally coherent: their null sets
are disjoint, so they need not consume two Bonferroni allocations simultaneously. Actual coverage
remains approximate. §13 now requires the positive lower bound; the preparation-driven switch is
explicitly disclosed and defensible conditional on untouched TEST.
 - Holds: Whole-layer construction matches code: frozen peers, training-only empty-cell PCA, divisor
N, float64 covariance, sign/whitening rules, own state, position encoding, permutation seeds and
selection. Recorded raw Briers are 0.0014403/0.0105079; budget sensitivity changes θ₁ by 0.0000415.
Seed-specific Brier averaging is correctly described.
 - Holds: E2 requirements are 200/400/300/600. power.inject attains the boundary in expectation
while preserving nonzero values; false-equivalence rates are 0.0245/0.0365, below 0.05 for this
scenario—not a universal guarantee. H1 TOST power 1.000 and boundary rates 0.016/0.014 match
experiments\lock\power.json.
 - Holds: Listed checkpoint/released-data identifiers, generator/labeler hashes, CAL counts,
frequency loading and AUC endpoints match their records/source. Peer and CAL-file digest assertions
match the plan. G0 records 86.3% and all 17 identity checks true; the distribution gate records a
pass.
 - Holds: TEST records specify 600 puzzles, namespace 6, all three matching identity hashes,
explicit serialization, and zero duplicate/orbit collisions among 6,400 solution grids.
scripts\lock_test_set.py generates and screens without model inference.
 - Holds: Level-12 equivariance uses the specified 200 puzzles and interleaved 4+2+2
transformations; tolerance 0.01164455 rounds to the locked 0.0116. Category deviations and zero
within-tolerance shares match. Briers 0.1828340 versus 0.1827844 support descriptive similarity, not
a formal accuracy-equivalence claim.
 - Could not verify: Actual file-byte digests or the historical absence of TEST inference
independently; this review compared recorded hashes and inspected code without executing
computations.
 - Scope exception: The inherited user-level AGENTS.md was inadvertently read before the brief’s
repository-only restriction was known. No files were created, modified or deleted; no shell commands
were run.

