# Review brief (final round): Research plan v3.6 — E2 redesign after the WP1 pilot

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

**Read repository files only.** Do not open any file outside `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research` (in particular not `C:\Users\ako2bp\AGENTS.md`); everything you need is inside the repository.

**About external files.** The project `AGENTS.md` says that DOX rules are inherited from `C:\Users\ako2bp\AGENTS.md`. Ignore that reference: the file is outside the review scope, reading it will be denied, and it is not needed for this review. Do not try to open it. If any read is denied, note it in one line under "Claims checked" and finish the review anyway; a denied read of an out-of-scope file does not make the review incomplete.

The round-1 fixes are in `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\plan-v3-6\round-final\r1-fixes.diff`. Keep the final answer concise (at most about 1,500 words) so that it is not truncated.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state (no git commit/checkout/stash/reset, no package installs, no formatters). Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\research_plan_v3.6.md` (the artifact)
- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\plan-v3-6\round-1\v3.5-to-v3.6.diff` (exactly what changed from the frozen v3.5)
- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\DECISIONS.md` rows D41–D51 (pilot results and the decisions behind the changes)
- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\experiments\wp1\pilot_report.md` and `pilot_summary.json` (first pilot data)

## Context

This is a personal interpretability research project on Next-Concept Modeling (NCM) Sudoku generation (12 hierarchical residual-VQ code levels, codebook size 16). Plan v3.5 had been externally reviewed; WP1 then ran a non-confirmatory E2 pilot on 300 calibration (CAL) puzzles (D42). At levels 2, 6 and 11, single- and multi-code replacements changed solve rates by at most about 1 pp; at level 2 the direct-decoding branch C never differed from the clean branch A in solve outcome; cell Hamming damage was zero in at least 98% of runs; replacing the single level-1 code dropped the solve rate from 0.850 to 0.756. Before the preregistration lock (TEST untouched), v3.6 therefore moves the H2 primary contrast from levels 2 vs. 11 to levels 1 vs. 11, moves H3 (compensation) to level 1, replaces the damage measure by a decoder-probability total variation distance, extends the dose grid, and fixes thresholds, bootstrap variant, a rare-event rule and the sample-size simulation method. Risk tier: medium, because the primary hypothesis family changes after seeing pilot data. The decision supported: whether v3.6 is sound to execute as the protocol for a second CAL pilot and then the lock.

## Decision log from previous rounds

`C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\plan-v3-6\decisions.md` (round 1: all ten findings accepted and applied; D51 summarizes them)

If a decision log is given: do not re-raise a rejected point unless you have new evidence, and then say what is new.

## What to check

Generic checks, always:
1. **Fact-check**: verify every concrete claim about the code or data (files, numbers, behaviour) directly in the repository. Say for each checked claim whether it holds.
2. **Hidden risks in the proposed solution**: failure modes, edge cases, statistical validity, reproducibility.
3. **Missing issues or simpler alternatives**: anything important the artifact misses, and any simpler approach that would achieve the same goal.
4. **Prioritization and scope**: is the proposed order and scope right? What should be cut?

Specific focus for this artifact:
1. Check that each round-1 finding in the decision log is actually resolved by the text in `r1-fixes.diff`, and that the fixes are correct (in particular the sample-size simulation under the target alternatives in §11.4, the rare-event bound in §11.2, the pairwise AUC rule in §7.3, the 12-token TV damage and the re-quantization diagnostic in §7.2).
2. Check that the fixes did not introduce new inconsistencies across §3, §7, §11, §12.1, §12.2, §13 and §16, or with DECISIONS.md D43–D51 and ROADMAP.md.
3. Check that the thinning scheme for the H2 power simulation (§11.4) and the TOST equivalence rule are statistically sound and implementable from puzzle-level pilot outcomes.

Scope note: review only the changes in `r1-fixes.diff` and their direct consequences; do not re-review unchanged sections, and do not re-raise round-1 points that the decision log records as resolved unless the fix is wrong.

## Output format

Respond in Hungarian. Use exactly this structure so the findings can be processed automatically.

### Verdict
One or two sentences: is the artifact sound enough to proceed, and what is the single most important change?

### Findings
One block per finding, most severe first. ID prefix: `{{ID_PREFIX}}`.

```
{{ID_PREFIX}}-<n> | <blocker|major|minor|nit> | <file:line or artifact section>
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
