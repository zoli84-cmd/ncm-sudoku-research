# Review brief: WP2 implementation plan — final round on the round-1 changes

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

**Read repository files only.** Do not open any file outside `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research`. Do not run Python, `uv run`, PowerShell or other execution commands; verify by reading files only. If any read is denied, note it in one line under "Claims checked" and finish the review.

**Keep the final answer short: at most about 1,200 words in total.** Report blocker and major findings in full; list minor findings as one line each (at most six) and no nits. Keep "Claims checked" to at most eight one-line items. A longer answer is truncated and the whole review is lost.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state. Return your review as your final answer; do not write it to disk.

## Artifact

- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\docs\superpowers\plans\2026-11-13-wp2.md` (the artifact: implementation plan, revised)
- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\plan-wp2\round-final\plan-r1.diff` (exactly what changed in round 1)
- Spec: `research_plan_v3.7.md` (locked protocol; §5.2, §7.1–7.4, §8.1–8.4, §10, §11.2, §12.2, §13) and `DECISIONS.md` rows D76–D78
- Code the plan modifies or reuses: `src/ncm_sudoku/e2.py`, `e2p2.py`, `intervene.py`, `g0.py`, `labels.py`, `e3controls.py`, `probes.py`, `wholelayer.py`; scripts `e2_pilot2.py`, `e3_extract.py`, `e3_probes.py`, `e3_wholelayer.py`, `lock_level1_check.py`

## Context

Personal interpretability research project on Next-Concept Modeling (NCM) Sudoku generation. The protocol is preregistered and locked. WP2 runs every confirmatory analysis once on 600 TEST puzzles; the code is frozen by a git tag `wp2-code`, verified by a dry run on non-TEST data (E2 must reproduce pilot-2 records exactly; E3 with PROBE-VAL in the TEST role must reproduce D64/D67), then run on TEST and evaluated by a pre-written script. Round 1 (three reviewers) found 3 blockers and 8 majors, all accepted (D78): fail-closed freeze and validity, no TEST outcome leakage, two statistics bugs, content-hashed resume, no TEST-own AUC, sham/no-op mismatches invalidate E2, 50-row outcome decoding with dry equality as the batch-invariance test, full budget records, dry-check fixes, §8.2 controls also on the whole-layer probe, and scoped §7.2–7.4 E2 diagnostics. Risk tier: medium (the plan is revertable, but the runs it produces are single-look). The decision supported: whether the revised plan can now be executed.

## Decision log from previous rounds

`C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\plan-wp2\decisions.md`. Do not re-raise resolved points unless the fix is wrong or incomplete; say what is new.

## Scope

Review only the sections changed in round 1 (see the diff) and their direct consequences. Check each accepted fix: is it correct against the real code it modifies, complete, and does it introduce a new defect?

## What to check

1. **Validity gates**: `valid_record`, `finish_run`, `guard_start` (Task 1), the E2 identity gate (Task 3), and the evaluation's refusal paths (Task 12). Can any invalid run still reach a confirmatory number? Can a valid run be wrongly blocked (for example the TEST guard requiring a dry record per runner)?
2. **Decode batching and diagnostics (Task 2)**: does `decode_chunk=None` with `diagnostics=False` provably leave pre-lock output unchanged? Do the new diagnostics (`level_logits`, change vectors, per-level code changes, state distances) avoid changing any of the 20 compared record fields or RNG streams? Is `level_logits` correctly specified against `intervene.continue_generation`?
3. **Resume and manifests (Tasks 1, 3, 7, 9)**: crash points around A, `parts/`, `diag/`, temp paths; are the mutation tests sufficient?
4. **Whole-layer controls (Task 8)**: are the new stages consistent with §8.2 and the existing whole-layer code (512-d random features, label permutation, teacher L06 from `T06.npy`, training-size curve), and do they keep the D64/D67 dry reproduction intact?
5. **Evaluation (Tasks 11–12)**: `tost` NaN handling, `auc_frozen` without TEST-own AUC, fallback readings, the D78 §7.4 disclosure.
6. **Runtime**: are the new dry (about 8.1 h) and TEST (about 17.5 h) estimates plausible from the cited measurements?

## Output format

Respond in English. Use exactly this structure.

### Verdict
One or two sentences: can the revised plan be executed, and what is the single most important remaining change?

### Findings
One block per blocker or major finding, most severe first. ID prefix: `ASTRA`.

```
ASTRA-<n> | <blocker|major> | <plan line or section>
Claim: <one or two sentences>
Evidence: <what you checked, with file:line>
Recommendation: <concrete change>
Confidence: <high|medium|low>
```

Then minor findings as one line each: `ASTRA-<n> | minor | <location> | <claim and recommendation>`.

Severity: blocker = executing as written produces wrong confirmatory results or breaks the single-look guarantee; major = significant risk or a clear mismatch with the locked protocol; minor = real but contained.

### Claims checked
At most eight one-line items, each marked holds / does not hold / could not verify.
