# Review brief: Research plan v3.7 — preregistration lock version

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

**Read repository files only.** Do not open any file outside `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research`; everything you need is inside the repository.

**About external files.** The project `AGENTS.md` says that DOX rules are inherited from `C:\Users\ako2bp\AGENTS.md`. Ignore that reference: the file is outside the review scope, reading it will be denied, and it is not needed for this review. Do not try to open it. If any read is denied, note it in one line under "Claims checked" and finish the review anyway; a denied read of an out-of-scope file does not make the review incomplete. Keep the final answer concise (at most about 2,000 words) so that it is not truncated.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state (no git commit/checkout/stash/reset, no package installs, no formatters). Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\research_plan_v3.7.md` (the artifact)
- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\plan-v3-7\round-1b\v3.6-to-v3.7.diff` (exactly what changed from the externally reviewed v3.6)
- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\DECISIONS.md` rows D53–D71 (the data and decisions behind the changes)
- Result files cited by the artifact: `experiments/e2p2/summary.json`, `experiments/e3prep/probes.json`, `experiments/e3prep/wholelayer.json`, `experiments/e3prep/budget_sensitivity/wholelayer.json`, `experiments/lock/power.json`, `experiments/lock/test_set.json`, `experiments/lock/equivariance_l12.json`, `experiments/lock/cal_freqs.json`, `experiments/provenance/checkpoints.json`, `experiments/provenance/released_data.json`, `src/ncm_sudoku/grid.py` (`PEER_ORDER`), `src/ncm_sudoku/e2p2.py`, `scripts/lock_cal_freqs.py`
- Code: `src/ncm_sudoku/wholelayer.py`, `src/ncm_sudoku/power.py`, `src/ncm_sudoku/probes.py`, `src/ncm_sudoku/e3controls.py`, `src/ncm_sudoku/e3equiv.py`, `scripts/e3_wholelayer.py`, `scripts/lock_power.py`, `scripts/lock_test_set.py`, `scripts/lock_equiv_l12.py`

## Context

This is a personal interpretability research project on Next-Concept Modeling (NCM) Sudoku generation (12 hierarchical residual-VQ code levels, codebook size 16). v3.6 was externally reviewed; since then two non-confirmatory preparation runs happened on CAL and PROBE data: a second E2 pilot (D53) and the E3 preparation (D64), followed by a whole-layer probe diagnostic (D65–D67), a budget sensitivity check (D69) and lock computations (D70, D71). Because the level-6 candidate-mask readability came out near null (θ₁ preview 0.0018 per-cell, 0.0031 whole-layer vs. a 0.01 threshold), v3.7 changes the H1 primary probe to a cell-relative whole-layer probe and makes H1 two-sided with a family-level ±0.01 equivalence reading; it also fills every §12.2 lock field (TEST size 600, TEST identity hashes, frozen level-1 frequencies, E2 common range, simulated error rates, level-12 equivariance tolerance). v3.7 is meant to be frozen by a git tag and an embargoed OSF registration; TEST puzzles were generated but no model has been run on them. Risk tier: high, because the lock is a published contract that is hard to roll back, and H1 changed after seeing preparation data (TEST untouched). The decision supported: whether v3.7 is sound to lock as written.

## Decision log from previous rounds

`C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\plan-v3-7\decisions.md`: round 1 ran with one reviewer (carbon); its six findings were accepted and are already applied to the artifact (frozen CAL frequencies for levels 2/6/11, frozen peer order and PCA rules, Brier averaging, H1 switch justification, full-precision AUC range, fixed equivariance tolerance, hash formats). Do not re-raise those points unless the fix is wrong; focus on what they did not cover. The v3.6 review log is `.reviews/plan-v3-6/decisions.md`.

**Tool note.** Do not run Python, `uv run` or PowerShell commands; they are blocked in this review environment. Verify everything by reading files. Name any blocked attempt in one line under "Claims checked" and finish the review.

If a decision log is given: do not re-raise a rejected point unless you have new evidence, and then say what is new.

## What to check

Generic checks, always:
1. **Fact-check**: verify every concrete number, hash and code claim in the v3.7 changes against the result files and code listed above. Say for each checked claim whether it holds.
2. **Hidden risks**: statistical validity, garden-of-forking-paths risk from changing H1 after preparation data, reproducibility, anything that would make the lock unenforceable.
3. **Missing issues or simpler alternatives**: anything a preregistration of this design should fix but v3.7 leaves open (except E4, which is deliberately deferred to a separate registration).
4. **Prioritization and scope**: is anything locked that should not be, or left open that must be locked?

Specific focus for this artifact:
1. H1 form (§3, §8.3, §11.1, §13): is the combination of a two-sided 98.33% "θ₁ ≠ 0" reading and a 96.67% family-level TOST inside ±0.01 coherent, correctly multiplicity-controlled within the three-contrast primary family, and correctly interpreted in §13? Is switching the primary probe to the whole-layer probe after seeing PROBE-VAL data defensible, and is it disclosed well enough?
2. Whole-layer probe specification (§8.1): is it complete and reproducible from the text (peer order, PCA fit rows, whitening, own state, position one-hot, permuted control, selection)? Check it against `src/ncm_sudoku/wholelayer.py` and `scripts/e3_wholelayer.py`. Is the raw-input control description (projected 0.0014 vs. unprojected 0.0105) correct and fairly interpreted?
3. §11.4 lock values: verify the simulated numbers in `experiments/lock/power.json` and the injection scenario for the levels 2 vs. 11 equivalence rule (`power.inject`, `equivalence_boundary_error`). Is the injection scenario a valid boundary check, and is a false-equivalence rate of 0.036 at −0.03 acceptable?
4. §12.2 table: verify every hash and value against `experiments/provenance/checkpoints.json`, `experiments/lock/test_set.json`, `src/ncm_sudoku/subsets.py`, `experiments/e3prep/extract.json` and `experiments/e2p2/summary.json`. Is the TEST identity locked strongly enough (hash formats)?
5. §8.4 equivariance at level 12: is the exploratory procedure and the fixed acceptable deviation (0.0116) well specified, and is the §13 reading of the PROBE-VAL result (accurate but not equivariant) justified?
6. Consistency: do §1–§16 still agree with each other after the edits (for example any text that still describes the per-cell probe as primary, or references to "v3.6" status that should now say lock)?

## Output format

Respond in Hungarian. Use exactly this structure so the findings can be processed automatically.

### Verdict
One or two sentences: is the artifact sound enough to proceed, and what is the single most important change?

### Findings
One block per finding, most severe first. ID prefix: `SOL`.

```
SOL-<n> | <blocker|major|minor|nit> | <file:line or artifact section>
Claim: <what is wrong or missing, one or two sentences>
Evidence: <what you checked in the code, with file:line>
Recommendation: <concrete change>
Confidence: <high|medium|low>
```

Severity definitions:
- **blocker**: proceeding as written causes incorrect behaviour, data loss, a security issue, or a design that must be redone.
- **major**: a significant risk, a wrong claim that drives a decision, or a clearly better alternative that changes the plan.
- **minor**: a real but contained issue; fix if cheap.
- **nit**: wording, style or preference. Report at most three nits.

Rules: only report what you checked or can argue concretely. If you could not verify a claim, say so with Confidence: low. Do not pad: zero findings in a category is a valid result.

### Claims checked
A short list of the artifact's code claims you verified, each marked holds / does not hold / could not verify.
